#!/usr/bin/env python3

import json
import operator
import time

import oursql
import requests

import db

def insert_kill(c, kill):
	try:
		db.execute(c, 'INSERT INTO kills (kill_id, solar_system_id, kill_time, moon_id) VALUES(?, ?, ?, ?)',
				kill['killID'], kill['solarSystemID'], kill['killTime'], kill['moonID'])
	except oursql.IntegrityError as e:
		if e.args[0] == oursql.errnos['ER_DUP_ENTRY']:
			print('duplicate:', kill['killID'])
			return
		raise

	victim = kill['victim']
	parambatch = [(
		kill['killID'], 1, victim['characterID'], victim['characterName'], victim['shipTypeID'],
		victim['allianceID'], victim['allianceName'], victim['corporationID'], victim['corporationName'], victim['factionID'], victim['factionName'],
		victim['damageTaken'], None, None, None,
	)]
	for attacker in kill['attackers']:
		parambatch.append((
			kill['killID'], 0, attacker['characterID'], attacker['characterName'], attacker['shipTypeID'],
			attacker['allianceID'], attacker['allianceName'], attacker['corporationID'], attacker['corporationName'], attacker['factionID'], attacker['factionName'],
			attacker['damageDone'], attacker['finalBlow'], attacker['securityStatus'], attacker['weaponTypeID'],
		))
	c.executemany('''
		INSERT INTO characters (
			kill_id, victim, character_id, character_name, ship_type_id,
			alliance_id, alliance_name, corporation_id, corporation_name, faction_id, faction_name,
			damage, final_blow, security_status, weapon_type_id
		) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		''', parambatch
	)

	parambatch = []
	for item in kill['items']:
		parambatch.append((kill['killID'], item['typeID'], item['flag'],
			item['qtyDropped'], item['qtyDestroyed'], item['singleton']))
	c.executemany('''
		INSERT INTO items (
			kill_id, type_id, flag, dropped, destroyed, singleton
		) VALUES(?, ?, ?, ?, ?, ?)
		''', parambatch
	)

	try:
		result = db.get(c, 'SELECT cost FROM item_costs WHERE type_id = ?', (victim['shipTypeID']))
		cost = result['cost']
	except db.NoRowsException:
		cost = 0
	result = db.get(c, '''
		SELECT SUM(cost * (dropped + destroyed)) AS item_cost
		FROM items
		JOIN item_costs ON items.type_id = item_costs.type_id
		WHERE kill_id = ?
		''', kill['killID'])
	if result['item_cost'] is not None:
		cost += result['item_cost']
	db.execute(c, 'INSERT INTO kill_costs (kill_id, cost) VALUES(?, ?)', kill['killID'], cost)

def main():
	rs = requests.session()
	with db.cursor() as c:
		groups = db.query(c, 'SELECT groupID FROM eve.invGroups WHERE categoryID = ?', 6)
		groups = list(map(operator.itemgetter('groupID'), groups))
		for i in range(0, len(groups), 10):
			query_groups = list(map(str, groups[i:i+10]))
			last_kill_id = None
			last_request_time = 0
			while True:
				path = '/api/losses/api-only/groupID/{}'.format(','.join(query_groups))
				if last_kill_id is not None:
					path += '/beforeKillID/' + str(last_kill_id)
				now = time.time()
				if now - last_request_time < 10:
					print('sleeping', 10 - (now - last_request_time))
					time.sleep(10 - (now - last_request_time))
				try:
					r = rs.get('https://zkillboard.com' + path)
					kills = r.json()
				except Exception as e:
					print(repr(e))
					break
				print('inserting', len(kills), 'kills')
				for kill in kills:
					insert_kill(c, kill)
				db.conn.commit()
				last_kill_id = kills[-1]['killID']
				last_request_time = now

if __name__ == '__main__':
	main()
