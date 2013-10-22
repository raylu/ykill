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
			kill['kill_time'] = _format_kill_time(kill['kill_time'])
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
		kill['kill_time'] = _format_kill_time(kill['kill_time'])

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
		attackers = []
		for char in characters:
			if char['victim']:
				victim = char
			elif char['final_blow']:
				final_blow = char
			else:
				attackers.append(char)

		item_rows = db.query(c, '''
			SELECT type_id, flag, dropped, destroyed, singleton,
				typeName AS item_name, capacity
			FROM items
			JOIN eve.invTypes ON type_id = typeID
			WHERE kill_id = ? ORDER BY flag ASC
			''', kill_id)
		items = defaultdict(list)
		for item in item_rows:
			flag = item['flag']
			if 125 <= flag <= 132:
				slot = 'subsystem'
			elif 27 <= flag <= 34:
				slot = 'high'
			elif 19 <= flag <= 26:
				slot = 'medium'
			elif 11 <= flag <= 18:
				slot = 'low'
			elif 92 <= flag <= 99:
				slot = 'rig'
			elif flag == 87:
				slot = 'drone bay'
			elif flag == 5:
				slot = 'cargo'
			elif 133 <= flag <= 143:
				slot = 'special hold'
			elif flag == 89:
				slot = 'implant'
			else:
				slot = '???'
			items[slot].append(item)

		slot_rows = db.query(c, '''
			SELECT attributeID, valueInt, valueFloat FROM eve.dgmTypeAttributes
			WHERE typeID = ? AND attributeID IN (12, 13, 14, 1137, 1367)
				AND (valueInt != 0 OR valueFloat != 0.0)
			''', victim['ship_type_id'])
		slot_mapping = {12: 'low', 13: 'medium', 14: 'high', 1137: 'rig', 1367: 'subsystem'}
		slots = dict.fromkeys(slot_mapping.values(), 0)
		for attr in slot_rows:
			slot = slot_mapping[attr['attributeID']]
			slots[slot] = attr['valueInt'] or int(attr['valueFloat']) # wtf CCP
		if slots['subsystem']:
			sub_ids = map(lambda s: str(s['type_id']), items['subsystem'])
			modifier_rows = db.query(c, '''
				SELECT attributeID, valueFloat FROM eve.dgmTypeAttributes
				WHERE typeID IN ({}) AND attributeID in (1374, 1375, 1376) and valueFloat != 0.0
				'''.format(','.join(sub_ids)))
			slot_mapping = {1374: 'high', 1375: 'medium', 1376: 'low'} # that's right, it's backwards for subs!
			for modifier in modifier_rows:
				slot = slot_mapping[modifier['attributeID']]
				slots[slot] += int(modifier['valueFloat']) # strangely, an improvement
	return {
		'kill': kill,
		'victim': victim,
		'final_blow': final_blow,
		'attackers': attackers,
		'items': items,
		'slots': slots,
	}

def _format_kill_time(kill_time):
	return kill_time.strftime('%Y-%m-%d %H:%m')
