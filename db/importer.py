#!/usr/bin/env python3

import json
from pprint import pprint

import __init__ as db

with db.cursor() as c:
	db.execute(c, 'INSERT INTO kills (kill_id, solar_system_id, kill_time, moon_id) VALUES(?, ?, ?, ?)',
			kill['killID'], kill['solarSystemID'], kill['killTime'], kill['moonID'])

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
