#!/usr/bin/env python3

from collections import defaultdict

import db

def fill_for_kill(c, kill):
	char_rows = db.query(c, '''
		SELECT kill_id, alliance_id, alliance_name, corporation_id, corporation_name, victim
		FROM kill_characters WHERE kill_id = %s
		''', kill['kill_id'])

	corp_params = []
	alliance_params = []
	corporations = set()
	alliances = set()
	for row in char_rows:
		if row['victim']:
			corp_params.append((row['kill_id'], row['corporation_id'], True))
			alliance_params.append((row['kill_id'], row['alliance_id'], True))
		else:
			if row['corporation_id'] != 0:
				corporations.add(row['corporation_id'])
			if row['alliance_id'] != 0:
				alliances.add(row['alliance_id'])

	for corp in corporations:
		corp_params.append((row['kill_id'], corp, False))
	for alliance in alliances:
		alliance_params.append((row['kill_id'], alliance, False))

	sql = 'INSERT INTO kill_corporations (kill_id, corporation_id, victim) VALUES(%s, %s, %s)'
	c.executemany(sql, corp_params)
	sql = 'INSERT INTO kill_alliances (kill_id, alliance_id, victim) VALUES(%s, %s, %s)'
	c.executemany(sql, alliance_params)

	db.conn.commit()

def handle_batch(c):
	for i in range(50):
		r = c.fetchone()
		if r is None:
			break
		with db.cursor() as ic:
			fill_for_kill(ic, r)
	return i == 49


def main():
	with db.cursor() as c:
		i = 0
		while True:
			db.execute(c, 'SELECT kill_id FROM kills ORDER BY kill_id ASC LIMIT 50 OFFSET %s', i)
			if not handle_batch(c):
				break
			i += 50
			if i % 1000 == 0:
				print('updated for', i, 'kills')

if __name__ == '__main__':
	main()
