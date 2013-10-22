#!/usr/bin/env python3

from http.client import HTTPSConnection
import json
import operator
import time

import oursql

import db

def insert_kill(c, kill):
	try:
		db.execute(c, 'INSERT INTO kills (kill_id, solar_system_id, kill_time, moon_id) VALUES(?, ?, ?, ?)',
				kill['killID'], kill['solarSystemID'], kill['killTime'], kill['moonID'])
	except oursql.IntegrityError as e:
		print('duplicate')
		if e.args[0] == oursql.errnos['ER_DUP_ENTRY']:
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

def main():
	with db.cursor() as c:
		groups = db.query(c, 'SELECT groupID FROM eve.invGroups WHERE categoryID = ?', 6)
		groups = list(map(operator.itemgetter('groupID'), groups))
		for i in range(0, len(groups), 10):
			query_groups = list(map(str, groups[i:i+10]))
			conn = HTTPSConnection('zkillboard.com', timeout=10)
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
					conn.request('GET', path)
					response = conn.getresponse()
					if response.status != 200:
						raise Exception('got {} {} from zkb'.format(response.status, response.reason))
					kills = json.loads(response.read().decode('utf-8'))
				except Exception as e:
					print(repr(e))
					break
				response.close()
				print('inserting', len(kills), 'kills')
				for kill in kills:
					insert_kill(c, kill)
				db.conn.commit()
				last_kill_id = kills[-1]['killID']
				last_request_time = now

if __name__ == '__main__':
	main()
