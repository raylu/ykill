#!/usr/bin/env python3

from decimal import Decimal
import sys

import requests

import db

rs = requests.session()
def get_prices():
	r = rs.get('https://crest-tq.eveonline.com/market/prices/')
	items = r.json()['items']
	for item in items:
		# averagePrice updates faster but some items (AT ships) don't have one
		price = item.get('averagePrice', item['adjustedPrice'])
		price = int(Decimal(price) * 100)
		yield item['type']['id'], price

au79_cost = None
def update_kill(kill_id):
	with db.conn.cursor() as c:
		r = db.get(c, '''
			SELECT ship_type_id, cost FROM kill_characters
			LEFT JOIN item_costs ON ship_type_id = item_costs.type_id
			WHERE kill_id = %s AND victim
			''', kill_id)
		if r[1] is not None:
			cost = r[1]
		else:
			cost = 0
		if r[0] == 33328: # Capsule - Genolution 'Auroral' 197-variant
			cost -= au79_cost
		# singleton is 0 normally and for BPOs and 2 for BPCs
		# we want to divide by 1 for BPOs and by 1000 for BPCs
		r = db.get(c, '''
			SELECT SUM(cost * (dropped + destroyed) / (singleton * 499.5 + 1))
			FROM items
			JOIN item_costs ON items.type_id = item_costs.type_id WHERE kill_id = %s
			''', kill_id)
		if r[0]:
			cost += int(r[0])
		if cost < 0:
			cost += au79_cost
			print('goddamnit CCP', kill_id) # sometimes, the implant just isn't there for a golden pod...
		c.execute('UPDATE kill_costs SET cost = %s WHERE kill_id = %s', (cost, kill_id))

def main():
	quiet = (len(sys.argv) == 2 and sys.argv[1] == '-q')
	with db.conn.cursor() as c:
		if not quiet:
			print('updating items')
		for type_id, price in get_prices():
			c.execute('UPDATE item_costs SET cost = %s WHERE type_id = %s', (price, type_id))
			if c.rowcount == 0:
				c.execute('INSERT INTO item_costs (type_id, cost) VALUES(%s, %s)', (type_id, price))
		db.conn.commit()

		r = db.get(c, 'SELECT cost FROM item_costs WHERE type_id = 33329') # Genolution 'Auroral' AU-79
		global au79_cost
		au79_cost = r[0]

		if len(sys.argv) == 2 and sys.argv[1] == '-a':
			print('getting kills')
			c.execute('SELECT kill_id FROM kills')

			print('updating kills')
			while True:
				r = c.fetchone()
				if r is None:
					break
				update_kill(r[0])
				if c.rownumber % 100 == 0:
					db.conn.commit()
					print('updated', c.rownumber, 'kills')
		db.conn.commit()

if __name__ == '__main__':
	main()
