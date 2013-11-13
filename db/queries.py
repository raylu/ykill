from collections import defaultdict
import datetime
import operator

import oursql

import db

def insert_kill(c, kill):
	try:
		db.execute(c, 'INSERT INTO kills (kill_id, solar_system_id, kill_time, moon_id) VALUES(?, ?, ?, ?)',
				kill['killID'], kill['solarSystemID'], kill['killTime'], kill['moonID'])
	except oursql.IntegrityError as e:
		if e.args[0] == oursql.errnos['ER_DUP_ENTRY']:
			return False
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
		INSERT INTO kill_characters (
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
		SELECT SUM(cost * (dropped + destroyed) / (singleton * 499.5 + 1)) AS item_cost
		FROM items
		JOIN item_costs ON items.type_id = item_costs.type_id
		WHERE kill_id = ?
		''', kill['killID'])
	if result['item_cost'] is not None:
		cost += result['item_cost']
	db.execute(c, 'INSERT INTO kill_costs (kill_id, cost) VALUES(?, ?)', kill['killID'], cost)

	for entity_type in ['alliance', 'corporation', 'character']:
		entity_dict = defaultdict(lambda: {'name': None, 'killed': 0, 'lost': 0})
		victim_id = victim[entity_type + 'ID']
		entity = entity_dict[victim_id]
		entity['name'] = victim[entity_type + 'Name']
		entity['lost'] = cost
		for attacker in kill['attackers']:
			entity_id = attacker[entity_type + 'ID']
			if entity_id != 0:
				entity = entity_dict[entity_id]
				entity['name'] = attacker[entity_type + 'Name']
				if attacker[entity_type + 'ID'] != victim_id:
					entity['killed'] = cost

		parambatch = []
		for entity_id, info in entity_dict.items():
			parambatch.append((entity_id, info['name'], info['killed'], info['lost'],
				info['name'], info['killed'], info['lost']))
		sql = '''
			INSERT INTO {}s ({}_id, {}_name, killed, lost)
			VALUES(?, ?, ?, ?)
			ON DUPLICATE KEY UPDATE {}_name = ?, killed = killed + ?, lost = lost + ?
			'''.format(entity_type, entity_type, entity_type, entity_type)
		c.executemany(sql, parambatch)

	return True

def search(q):
	like_str = '{}%'.format(q)
	with db.cursor() as c:
		alliances = db.query(c, '''
			SELECT alliance_id, alliance_name FROM alliances
			WHERE alliance_name LIKE ? LIMIT 25
			''', like_str)
		corps = db.query(c, '''
			SELECT corporation_id, corporation_name FROM corporations
			WHERE corporation_name LIKE ? LIMIT 25
			''', like_str)
		chars = db.query(c, '''
			SELECT character_id, character_name FROM characters
			WHERE character_name LIKE ? LIMIT 25
			''', like_str)
		systems = db.query(c, '''
			SELECT solarSystemID AS system_id, solarSystemName AS system_name
			FROM eve.mapSolarSystems
			WHERE solarSystemName LIKE ? LIMIT 5
			''', like_str)
	return {
		'alliances': alliances,
		'corporations': corps,
		'characters': chars,
		'systems': systems,
	}

def kill_list(entity_type, entity_id, list_type, page):
	with db.cursor() as c:
		if entity_type == 'system':
			sql = 'SELECT solarSystemName AS system_name FROM eve.mapSolarSystems WHERE solarSystemID = ?'
		else:
			sql = 'SELECT {}_name, killed, lost FROM {}s WHERE {}_id = ?'.format(entity_type, entity_type, entity_type)
		try:
			stats = db.get(c, sql, entity_id)
		except db.NoRowsException:
			return None
		# the combination of DISTINCT and and ORDER BY means we can't join kills or we get filesort
		# get kill_ids from chars, then get kill data on those ids
		if list_type == 'kills':
			extra_cond = 'AND victim = 0'
		elif list_type == 'losses':
			extra_cond = 'AND victim = 1'
		elif list_type is None:
			extra_cond = ''
		page_size = 50
		if entity_type == 'system':
			sql = 'SELECT kill_id FROM kills WHERE solar_system_id = ? ORDER BY kill_id DESC LIMIT ? OFFSET ?'
		else:
			sql = '''
				SELECT DISTINCT kill_id FROM kill_characters
				WHERE {}_id = ? {}
				ORDER BY kill_id DESC LIMIT ? OFFSET ?
				'''.format(entity_type, extra_cond)
		kills = db.query(c, sql, entity_id, page_size, (page - 1) * page_size)
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
			FROM kill_characters
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
		kills.sort(key=operator.itemgetter('kill_id'), reverse=True)
		for kill in kills:
			kill['kill_time'] = _format_kill_time(kill['kill_time'])
			kill['security_status'] = _security_status(kill['security'], kill['wh_class'])
			chars = characters[kill['kill_id']]
			kill['victim'] = chars['victim']
			kill['final_blow'] = chars['final_blow']
			kill['attackers'] = chars['attackers']
	return {'stats': stats, 'kills': kills}

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
		kill['security_status'] = _security_status(kill['security'], kill['wh_class'])

		characters = db.query(c, '''
			SELECT character_id, character_name, damage, victim, final_blow,
				corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, weapon_type_id,
				ship.typeName AS ship_name, weapon.typeName AS weapon_name
			FROM kill_characters
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
			if slot not in items:
				continue # otherwise, defaultdict creates lists for them
			fitting_items.update(map(operator.itemgetter('type_id'), items[slot]))
		if len(fitting_items):
			# 11: requires low, 12: requires high, 13: requires medium; :CCP:
			modules = db.query(c, '''
				SELECT DISTINCT typeID AS type_id FROM eve.dgmTypeEffects
				WHERE typeID IN ({}) and effectID IN (11, 12, 13)
				'''.format(','.join(map(str, fitting_items))))
			module_ids = set(map(operator.itemgetter('type_id'), modules))
			for slot in module_slots:
				if slot not in items:
					continue
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
			meta = db.get(c, '''
				SELECT kill_time, solar_system_id, solarSystemName AS system_name,
					security, class AS wh_class, static1, static2, effect AS wh_effect
				FROM kills
				LEFT JOIN wh_systems ON solar_system_id = id
				JOIN eve.mapSolarSystems ON solar_system_id = solarSystemID
				WHERE kill_id = ?
				''', kill_id)
		except db.NoRowsException:
			return None
		after = meta['kill_time'] - datetime.timedelta(minutes=15)
		before = meta['kill_time'] + datetime.timedelta(minutes=15)
		kill_rows = db.query(c, '''
			SELECT kills.kill_id, kill_time, cost
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			WHERE solar_system_id = ? AND kill_time BETWEEN ? AND ?
			''', meta['solar_system_id'], after, before)
		kill_ids = list(map(operator.itemgetter('kill_id'), kill_rows))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, typeName AS ship_name
			FROM kill_characters
			JOIN eve.invTypes ON ship_type_id = typeID
			WHERE kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))

	# organize characters and kills
	characters = {}
	for char in char_rows: # generate canonical chars
		character_id = char['character_id']
		canonical_char = characters.get(character_id)
		if canonical_char is None:
			characters[character_id] = char
		elif not canonical_char['victim']: # prefer canonicalizing victims
			characters[character_id] = char
		elif canonical_char['victim'] and canonical_char['ship_type_id'] in [670, 33328]: # pod
			characters[character_id] = char
			char['pod'] = canonical_char['kill_id']
		elif char['victim'] and char['ship_type_id'] in [670, 33328]:
			canonical_char['pod'] = char['kill_id']
		char['faction'] = None
	kills = {}
	for kill in kill_rows:
		kills[kill['kill_id']] = {'victim': None, 'attackers': [], 'cost': kill['cost']}
	for char in char_rows:
		canonical_char = characters[char['character_id']]
		kill = kills[char['kill_id']]
		if char['victim']:
			kill['victim'] = canonical_char
			canonical_char['death_id'] = canonical_char['kill_id']
			canonical_char['cost'] = canonical_char.get('cost', 0) + kill['cost']
		else:
			kill['attackers'].append(canonical_char)

	# let's sort this mess out
	kills[kill_id]['victim']['faction'] = 0
	for attacker in kills[kill_id]['attackers']:
		# ignore minor awoxing
		if attacker['corporation_id'] != kills[kill_id]['victim']['corporation_id'] or \
				len(kill['attackers']) < 3:
			attacker['faction'] = 1
	change = True
	while change:
		change = False
		for kill in kills.values():
			victim = kill['victim']
			if victim['faction'] is not None:
				attacker_faction = 1 - victim['faction']
			else:
				for attacker in kill['attackers']:
					# find an attacker that has already been assigned and isn't an NPC
					if attacker['faction'] is not None and attacker['character_id'] != 0:
						attacker_faction = attacker['faction']
						victim['faction'] = 1 - attacker_faction
						change = True
						break
				else:
					continue
			for attacker in kill['attackers']:
				if attacker['faction'] is None and \
						(attacker['corporation_id'] != victim['corporation_id'] or \
						len(kill['attackers']) < 3):
					attacker['faction'] = attacker_faction
					change = True

	# prepare output lists
	factions = [[], [], []]
	for char in characters.values():
		if char['faction'] is None:
			char['faction'] = 2
		del char['kill_id']
		del char['final_blow']
		del char['victim']
		factions[char['faction']].append(char)

	meta['kill_time'] = _format_kill_time(meta['kill_time'])
	meta['security_status'] = _security_status(meta['security'], meta['wh_class'])
	return {'meta': meta, 'factions': factions}

def top_cost():
	with db.cursor() as c:
		kills = db.query(c, '''
			SELECT kills.kill_id, cost, solar_system_id, kill_time,
				ship_type_id, typeName AS ship_name
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			JOIN kill_characters ON kill_characters.kill_id = kills.kill_id
			JOIN eve.invTypes ON typeID = ship_type_id
			WHERE victim = 1 AND kill_time >= ADDDATE(UTC_DATE(), INTERVAL -3 DAY)
			ORDER BY cost DESC
			LIMIT 25
			''')
		# joining eve.mapSolarSystems on the initial query causes filesort on large dbs for some reason
		# do a manual join
		system_ids = set(map(operator.itemgetter('solar_system_id'), kills))
		system_rows = db.query(c, '''
			SELECT solarSystemID as solar_system_id, solarSystemName AS system_name,
				security, class AS wh_class
			FROM eve.mapSolarSystems
			LEFT JOIN wh_systems ON solarSystemID = wh_systems.id
			WHERE solarSystemID IN ({})
			'''.format(','.join(map(str, system_ids))))
	systems = {}
	for system in system_rows:
		systems[system['solar_system_id']] = system
	for kill in kills:
		kill.update(systems[kill['solar_system_id']])
		del kill['solar_system_id']
		kill['security_status'] = _security_status(kill['security'], kill['wh_class'])
		kill['kill_time'] = _format_kill_time(kill['kill_time'])
	return kills

def last(kill_id):
	with db.cursor() as c:
		if kill_id is None:
			kills = db.get(c, 'SELECT kills.kill_id FROM kills ORDER BY kills.kill_id DESC LIMIT 1')
		else:
			kills = db.query(c, '''
				SELECT
					kills.kill_id, kill_costs.cost AS total_cost, item_costs.cost AS hull_cost, typeName AS ship_name
				FROM kills
				JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
				JOIN kill_characters ON kill_characters.kill_id = kills.kill_id
				JOIN item_costs ON item_costs.type_id = ship_type_id
				JOIN eve.invTypes ON typeID = ship_type_id
				WHERE victim = 1 AND kills.kill_id > ?
			''', kill_id)
	return kills

def _format_kill_time(kill_time):
	return kill_time.strftime('%Y-%m-%d %H:%M')

def _security_status(security, wh_class):
		if wh_class:
			security_status = 'wspace'
		elif security >= 0.5:
			security_status = 'high'
		elif security > 0.0:
			security_status = 'low'
		else:
			security_status = 'null'
		return security_status
