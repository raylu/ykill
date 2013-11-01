#!/usr/bin/env python3

from decimal import Decimal
import sys
from xml.etree import ElementTree

import requests

import db

rs = requests.session()
def get_prices():
	r = rs.get('http://eve.no-ip.de/prices/30d/prices-all.xml', stream=True)
	tree = ElementTree.parse(r.raw)
	rowset = tree.getroot().find('result').find('rowset').findall('row')
	parambatch = []
	for row in rowset:
		price = int(Decimal(row.attrib['median']) * 100)
		parambatch.append((row.attrib['typeID'], price, price))
	return parambatch

au79_cost = None
def update_kill(kill_id):
	with db.conn.cursor() as c:
		c.execute('''
			SELECT ship_type_id, cost FROM characters
			LEFT JOIN item_costs ON ship_type_id = item_costs.type_id
			WHERE kill_id = ? AND victim
			''', (kill_id,))
		r = c.fetchone()
		if r[1] is not None:
			cost = r[1]
		else:
			cost = 0
		c.nextset()
		if r[0] == 33328: # Capsule - Genolution 'Auroral' 197-variant
			cost -= au79_cost
		# singleton is 0 normally and for BPOs and 2 for BPCs
		# we want to divide by 1 for BPOs and by 1000 for BPCs
		c.execute('''
			SELECT SUM(cost * (dropped + destroyed) / (singleton * 499.5 + 1))
			FROM items
			JOIN item_costs ON items.type_id = item_costs.type_id WHERE kill_id = ?
			''', (kill_id,))
		r = c.fetchone()
		c.nextset()
		if r[0]:
			cost += int(r[0])
		if cost < 0:
			cost += au79_cost
			print('goddamnit CCP', kill_id) # sometimes, the implant just isn't there for a golden pod...
		c.execute('UPDATE kill_costs SET cost = ? WHERE kill_id = ?', (cost, kill_id))

def main():
	with db.conn.cursor() as c:
		if len(sys.argv) < 2:
			print('downloading prices')
			parambatch = get_prices()

			print('updating items')
			c.executemany('''
				INSERT INTO item_costs (type_id, cost) VALUES(?, ?)
				ON DUPLICATE KEY UPDATE cost = ?
				''', parambatch)

		c.execute('SELECT cost FROM item_costs WHERE type_id = 33329') # Genolution 'Auroral' AU-79
		global au79_cost
		au79_cost = c.fetchone()[0]
		c.nextset()

		if len(sys.argv) < 2:
			print('getting kills')
			c.execute('SELECT kill_id FROM kills')
		else:
			c.execute('''
				SELECT kill_id FROM characters
				JOIN eve.invTypes ON typeID = ship_type_id
				WHERE victim = 1 AND groupID = ?
				''', (sys.argv[1],))

		print('updating kills')
		while True:
			r = c.fetchone()
			if r is None:
				break
			update_kill(r[0])

if __name__ == '__main__':
	main()
