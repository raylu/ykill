#!/usr/bin/env python3

from decimal import Decimal
from io import StringIO
import operator
import sys
from xml.etree import ElementTree

import requests

import db

def fetch_type_ids(c):
	if len(sys.argv) > 1 and sys.argv[1] in ['-q', '--quick']:
		type_ids = c.execute('''
			SELECT i.type_id FROM items AS i
				JOIN eve.invTypes AS t ON i.type_id = t.typeID
				WHERE marketGroupID is NOT NULL
			UNION SELECT ship_type_id FROM characters
				JOIN eve.invTypes ON ship_type_id = typeID
				WHERE victim AND marketGroupID is NOT NULL
			''')
	else:
		type_ids = c.execute('SELECT typeID FROM eve.invTypes WHERE marketGroupID IS NOT NULL')
	return set(map(operator.itemgetter(0), c.fetchall()))

rs = requests.session()
jita_system = 30000142
def query(type_id):
	params = {'typeid': type_id, 'usesystem': jita_system}
	r = rs.get('http://api.eve-central.com/api/marketstat', params=params)
	try:
		tree = ElementTree.parse(StringIO(r.text))
	except ElementTree.ParseError:
		return 0
	value = tree.getroot().find('marketstat').find('type').find('sell').find('percentile').text
	return int(Decimal(value) * 100)

def update_kill(kill_id):
	with db.conn.cursor() as c:
		c.execute('''
			SELECT cost FROM characters
			JOIN item_costs ON ship_type_id = item_costs.type_id
			WHERE kill_id = ? AND victim
			''', (kill_id,))
		r = c.fetchone()
		if r:
			cost = r[0]
			c.nextset()
		else:
			cost = 0
		# singleton is 0 normally and for BPOs and 2 for BPCs
		# we want to divide by 1 for BPOs and by 1000 for BPCs
		c.execute('''
			SELECT SUM(cost * (dropped + destroyed) / (singleton * 499.5 + 1))
			FROM items AS i
			JOIN item_costs AS ic ON i.type_id = ic.type_id WHERE kill_id = ?
			''', (kill_id,))
		r = c.fetchone()
		c.nextset()
		if r[0]:
			cost += r[0]
		c.execute('UPDATE kill_costs SET cost = ? WHERE kill_id = ?', (cost, kill_id))

def main():
	with db.conn.cursor() as c:
		print('getting items')
		type_ids = fetch_type_ids(c)

		print('updating items')
		parambatch = []
		for type_id in type_ids:
			value = query(type_id)
			parambatch.append((type_id, value, value))
		c.executemany('''
			INSERT INTO item_costs (type_id, cost) VALUES(?, ?)
			ON DUPLICATE KEY UPDATE cost = ?
			''', parambatch)

		print('getting kills')
		c.execute('SELECT kill_id from kills')

		print('updating kills')
		while True:
			r = c.fetchone()
			if r is None:
				break
			update_kill(r[0])

if __name__ == '__main__':
	main()
