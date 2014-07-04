#!/usr/bin/env python3

import heapq
import json
import operator
import sys
import time

import oursql
import requests

import db
import db.queries

def main():
	rs = requests.session()
	with db.cursor() as c:
		if len(sys.argv) == 2:
			kill_id = sys.argv[1]
			response = rs.get('http://api.whelp.gg/kill/' + kill_id)
			character_id = response.json()['victim']['character_id']
			kill_id = int(kill_id)
			url = 'https://zkillboard.com/api/losses/characterID/{}/beforeKillID/{}/limit/200'
			response = rs.get(url.format(character_id, kill_id + 200))
			data = response.json()
			print('got {} kills'.format(len(data)))
			for kill in data:
				if int(kill['killID']) != kill_id:
					continue
				if db.queries.insert_kill(c, kill):
					print('inserted!')
				else:
					print('duplicate')
			return

		groups = db.query(c, 'SELECT groupID FROM eve.invGroups WHERE categoryID = ?', 6)
		groups = list(map(operator.itemgetter('groupID'), groups))
		last_kill_ids = []
		for i in range(0, len(groups), 10):
			query_groups = ','.join(map(str, groups[i:i+10]))
			heapq.heappush(last_kill_ids, (-float('inf'), query_groups))
		last_request_time = 0
		last_kill_id, query_group = heapq.heappop(last_kill_ids)
		while last_kill_id < -27500770: # first kill of 2013
			path = '/api/losses/api-only/groupID/' + query_group
			if last_kill_id != -float('inf'):
				path += '/beforeKillID/' + str(-last_kill_id)
			now = time.time()
			if now - last_request_time < 12:
				sleep_secs = 12 - (now - last_request_time)
				print('sleeping', sleep_secs)
				time.sleep(sleep_secs)
			last_request_time = time.time()
			try:
				r = rs.get('https://zkillboard.com' + path)
				kills = r.json()
			except Exception as e:
				print(repr(e))
				break
			print('inserting', len(kills), 'kills', end='... ')
			sys.stdout.flush()
			inserted = 0
			try:
				for kill in kills:
					if db.queries.insert_kill(c, kill):
						inserted += 1
			except TypeError as e:
				print(repr(e), kills)
				break
			db.conn.commit()
			print(len(kills) - inserted, 'dupes')

			last_kill_id = int(kills[-1]['killID'])
			last_kill_id, query_group = heapq.heappushpop(last_kill_ids, (-last_kill_id, query_group))

if __name__ == '__main__':
	main()
