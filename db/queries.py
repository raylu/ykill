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
			SELECT DISTINCT(kills.kill_id), kill_time FROM kills
			JOIN characters on characters.kill_id = kills.kill_id
			WHERE corporation_id = ?
			''', corp_id)
		kill_ids = list(map(operator.itemgetter('kill_id'), kills))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name
			FROM characters
			WHERE kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))
		characters = defaultdict(dict)
		for char in char_rows:
			kill_id = char['kill_id']
			if char['victim']:
				characters[kill_id]['victim'] = char
			elif char['final_blow']:
				characters[kill_id]['final_blow'] = char
		for kill in kills:
			chars = characters[kill['kill_id']]
			kill['victim'] = chars['victim']
			kill['final_blow'] = chars['final_blow']
	return kills

def kill(kill_id):
	with db.cursor() as c:
		kill = db.get(c, '''
			SELECT kill_time, solarSystemName, security FROM kills
			JOIN eve.mapSolarSystems on solar_system_id = solarSystemID
			WHERE kill_id = ?
			''', kill_id)
		characters = db.query(c, '''
			SELECT ship_type_id, character_id, character_name,
				corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name
				typeName
			FROM characters
			JOIN eve.invTypes on ship_type_id = typeID
			WHERE kill_id = ?
			''', kill_id)
	return {'kill': kill, 'characters': characters}
