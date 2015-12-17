#!/usr/bin/env python3

import heapq
import json
import operator
import sys
import time

import requests

import db
import db.queries

rs = requests.session()
def main():
	with db.cursor() as c:
		if len(sys.argv) == 2:
			kill_id = int(sys.argv[1])
			import_one_kill(c, kill_id)
			db.conn.commit()
			return

		last_kill_id = None
		while not last_kill_id or last_kill_id > 27500770: # don't go before 2013
			if last_kill_id is None:
				path = '/page/0'
			else:
				path += '/beforeKillID/%s' % last_kill_id
			r = rs.get('https://zkillboard.com/api' + path)
			kills = r.json()
			last_kill_id = kills[-1]['killID']

			print('inserting', len(kills), 'kills', end='... ')
			sys.stdout.flush()
			inserted = 0
			for kill in kills:
				if db.queries.insert_kill(c, kill):
					inserted += 1
			db.conn.commit()
			print(len(kills) - inserted, 'dupes')

			time.sleep(5)

def import_one_kill(cursor, kill_id):
	response = rs.get('https://zkillboard.com/api/killID/%d' % kill_id)
	kill = response.json()[0]
	if db.queries.insert_kill(cursor, kill):
		print('inserted!')
	else:
		print('duplicate')

if __name__ == '__main__':
	main()
