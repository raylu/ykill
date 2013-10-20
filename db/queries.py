from collections import defaultdict
import operator
import db

def search(q):
	with db.cursor() as c:
		corps = db.query(c, '''
			SELECT DISTINCT corporation_id, corporation_name FROM characters
			WHERE corporation_name LIKE ?
			''', '%{}%'.format(q))
	return {'corporations': corps}

def corporation(corp_id):
	with db.cursor() as c:
		kills = db.query(c, '''
			SELECT DISTINCT(kills.kill_id), kill_time,
				solarSystemName as system_name, security, regionName as region
			FROM kills
			JOIN characters ON characters.kill_id = kills.kill_id
			JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
			JOIN eve.mapRegions ON mapSolarSystems.regionID = mapRegions.regionID
			WHERE corporation_id = ?
			''', corp_id)
		kill_ids = list(map(operator.itemgetter('kill_id'), kills))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, typeName AS ship_name
			FROM characters
			JOIN eve.invTypes ON ship_type_id = typeID
			WHERE kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))
		characters = defaultdict(dict)
		for kill_id in kill_ids:
			characters[kill_id]['attackers'] = 1 # count final_blow now
		for char in char_rows:
			kill_id = char['kill_id']
			if char['victim']:
				characters[kill_id]['victim'] = char
			elif char['final_blow']:
				characters[kill_id]['final_blow'] = char
			else:
				characters[kill_id]['attackers'] += 1
		for kill in kills:
			chars = characters[kill['kill_id']]
			kill['victim'] = chars['victim']
			kill['final_blow'] = chars['final_blow']
			kill['attackers'] = chars['attackers']
	return kills

def kill(kill_id):
	with db.cursor() as c:
		kill = db.get(c, '''
			SELECT kill_time, solarSystemName, security FROM kills
			JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
			WHERE kill_id = ?
			''', kill_id)
		characters = db.query(c, '''
			SELECT character_id, character_name, damage, victim, final_blow,
				corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, weapon_type_id,
				ship.typeName AS ship_name, weapon.typeName AS weapon_name
			FROM characters
			JOIN eve.invTypes AS ship ON ship_type_id = ship.typeID
			LEFT JOIN eve.invTypes AS weapon ON weapon_type_id = weapon.typeID
			WHERE kill_id = ?
			''', kill_id)
		items = db.query(c, '''
			SELECT type_id, flag, dropped, destroyed, singleton,
				typeName AS item_name
			FROM items
			JOIN eve.invTypes ON type_id = typeID
			WHERE kill_id = ? ORDER BY flag ASC
			''', kill_id)
	return {'kill': kill, 'characters': characters, 'items': items}
