from collections import defaultdict
import datetime
import operator
import db

def search(q):
	like_str = '{}%'.format(q)
	with db.cursor() as c:
		alliances = db.query(c, '''
			SELECT DISTINCT alliance_id, alliance_name FROM characters
			WHERE alliance_name LIKE ? LIMIT 25
			''', like_str)
		corps = db.query(c, '''
			SELECT DISTINCT corporation_id, corporation_name FROM characters
			WHERE corporation_name LIKE ? LIMIT 25
			''', like_str)
		chars = db.query(c, '''
			SELECT DISTINCT character_id, character_name FROM characters
			WHERE character_name LIKE ? LIMIT 25
			''', like_str)
	return {'alliances': alliances, 'corporations': corps, 'characters': chars}

def kill_list(entity_type, entity_id):
	with db.cursor() as c:
		# the combination of DISTINCT and and ORDER BY means we can't join kills or we get filesort
		# get kill_ids from chars, then get kill data on those ids
		kills = db.query(c, '''
			SELECT DISTINCT kill_id FROM characters
			WHERE {}_id = ? ORDER BY kill_id DESC LIMIT 50
			'''.format(entity_type), entity_id)
		if len(kills) == 0:
			return None
		kill_ids = list(map(operator.itemgetter('kill_id'), kills))
		kills = db.query(c, '''
			SELECT kills.kill_id, kill_time, cost,
				solarSystemName AS system_name, security, regionName AS region,
				class AS wh_class, static1, static2
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			LEFT JOIN wh_systems ON solar_system_id = id
			JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
			JOIN eve.mapRegions ON mapSolarSystems.regionID = mapRegions.regionID
			WHERE kills.kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))
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
		entity_name = None
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
			if entity_name is None and char[entity_type + '_id'] == entity_id:
				entity_name = char[entity_type + '_name']
		kills.sort(key=operator.itemgetter('kill_id'), reverse=True)
		for kill in kills:
			kill['kill_time'] = _format_kill_time(kill['kill_time'])
			kill['security_status'] = _security_status(kill['system_name'], kill['security'], kill['wh_class'])
			chars = characters[kill['kill_id']]
			kill['victim'] = chars['victim']
			kill['final_blow'] = chars['final_blow']
			kill['attackers'] = chars['attackers']
	return {'entity_name': entity_name, 'kills': kills}

def kill(kill_id):
	with db.cursor() as c:
		try:
			kill = db.get(c, '''
				SELECT kill_time, cost, solarSystemName AS system_name, security,
					class AS wh_class, static1, static2, effect AS wh_effect
				FROM kills
				JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
				LEFT JOIN wh_systems ON solar_system_id = id
				JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
				WHERE kills.kill_id = ?
				''', kill_id)
		except db.NoRowsException:
			return None
		kill['kill_time'] = _format_kill_time(kill['kill_time'])
		kill['security_status'] = _security_status(kill['system_name'], kill['security'], kill['wh_class'])

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

		try:
			ship_cost = db.get(c, 'SELECT cost FROM item_costs WHERE type_id = ?',
					victim['ship_type_id'])
			victim['ship_cost'] = ship_cost['cost']
		except db.NoRowsException:
			victim['ship_cost'] = 0

		# see update_costs for an explanation of the ORDER BY
		item_rows = db.query(c, '''
			SELECT items.type_id, flag, dropped, destroyed, singleton,
				cost, typeName AS item_name
			FROM items
			JOIN item_costs ON item_costs.type_id = items.type_id
			JOIN eve.invTypes ON items.type_id = typeID
			WHERE kill_id = ?
			ORDER BY (cost * (dropped + destroyed) / (singleton * 499.5 + 1)) DESC
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
			elif flag == 90:
				slot = 'ship hangar'
			elif flag == 155:
				slot = 'fleet hangar'
			elif flag == 148:
				slot = 'command center hold'
			elif flag == 149:
				slot = 'planetary commodities hold'
			elif flag == 89:
				slot = 'implant'
			else:
				slot = '???'
			items[slot].append(item)

		module_slots = ['high', 'medium', 'low']
		fitting_items = set()
		for slot in module_slots:
			fitting_items.update(map(operator.itemgetter('type_id'), items[slot]))
		if len(fitting_items):
			# 11: requires low, 12: requires high, 13: requires medium; :CCP:
			modules = db.query(c, '''
				SELECT DISTINCT typeID AS type_id FROM eve.dgmTypeEffects
				WHERE typeID IN ({}) and effectID IN (11, 12, 13)
				'''.format(','.join(map(str, fitting_items))))
			module_ids = set(map(operator.itemgetter('type_id'), modules))
			for slot in module_slots:
				for item in items[slot]:
					if item['type_id'] not in module_ids:
						item['charge'] = True

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

def battle_report(kill_id):
	with db.cursor() as c:
		# collect some data
		try:
			kill = db.get(c, 'SELECT kill_time, solar_system_id FROM kills WHERE kill_id = ?', kill_id)
		except db.NoRowsException:
			return None
		after = kill['kill_time'] - datetime.timedelta(minutes=15)
		before = kill['kill_time'] + datetime.timedelta(minutes=15)
		kill_rows = db.query(c, '''
			SELECT kills.kill_id, kill_time, cost
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			WHERE solar_system_id = ? AND kill_time BETWEEN ? AND ?
			''', kill['solar_system_id'], after, before)
		kill_ids = list(map(operator.itemgetter('kill_id'), kill_rows))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, typeName AS ship_name
			FROM characters
			JOIN eve.invTypes ON ship_type_id = typeID
			WHERE kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))

		# organize characters and kills
		characters = {}
		for char in char_rows: # generate canonical chars
			canonical_char = characters.get(char['character_id'])
			if canonical_char is None or not canonical_char['victim']: # prefer canonicalizing victims
				characters[char['character_id']] = char
				char['faction'] = None
		kills = {}
		for kill in kill_rows:
			kills[kill['kill_id']] = {'victim': None, 'attackers': []}
		for char in char_rows:
			canonical_char = characters[char['character_id']]
			kill = kills[char['kill_id']]
			if char['victim']:
				kill['victim'] = canonical_char
				canonical_char['death_id'] = char['kill_id']
			else:
				kill['attackers'].append(canonical_char)

		# let's sort this mess out
		kills[kill_id]['victim']['faction'] = 0
		for attacker in kills[kill_id]['attackers']:
			attacker['faction'] = 1
		change = True
		while change:
			change = False
			for kill in kills.values():
				if kill['victim']['faction'] is not None:
					attacker_faction = 1 - kill['victim']['faction']
					for attacker in kill['attackers']:
						if attacker['faction'] is None:
							attacker['faction'] = attacker_faction
							change = True
				else:
					for attacker in kill['attackers']:
						if attacker['faction'] is not None:
							break
					else:
						continue
					attacker_faction = attacker['faction']
					kill['victim']['faction'] = 1 - attacker_faction
					change = True
					for attacker in kill['attackers']:
						if attacker['faction'] is None:
							attacker['faction'] = attacker_faction

		# prepare output lists
		factions = [[], []]
		for char in characters.values():
			del char['kill_id']
			del char['final_blow']
			del char['victim']
			factions[char['faction']].append(char)
		return factions

def top_cost():
	with db.cursor() as c:
		kills = db.query(c, '''
			SELECT kills.kill_id, cost,
				ship_type_id, typeName as ship_name,
				solarSystemName AS system_name, security, class AS wh_class
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			JOIN characters ON characters.kill_id = kills.kill_id
			LEFT JOIN wh_systems ON solar_system_id = wh_systems.id
			JOIN eve.invTypes ON typeID = ship_type_id
			JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
			WHERE victim = 1
			ORDER BY cost DESC
			LIMIT 25
			''')
	for kill in kills:
		kill['security_status'] = _security_status(kill['system_name'], kill['security'], kill['wh_class'])
	return kills

def _format_kill_time(kill_time):
	return kill_time.strftime('%Y-%m-%d %H:%M')

def _security_status(system_name, security, wh_class):
		if wh_class:
			security_status = 'wspace'
		elif security >= 0.5:
			security_status = 'high'
		elif security > 0.0:
			security_status = 'low'
		else:
			security_status = 'null'
		return security_status
