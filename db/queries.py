from collections import defaultdict
import datetime
import operator

import psycopg2
import psycopg2.errorcodes

import db
from dogma import Dogma

entity_types = ['alliance', 'corporation', 'character']

def insert_kill(c, kill):
	try:
		c.execute('INSERT INTO kills (kill_id, solar_system_id, kill_time) VALUES(%s, %s, %s)',
				(kill['killID'], kill['solarSystemID'], kill['killTime']))
	except psycopg2.IntegrityError as e:
		if e.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
			db.conn.rollback()
			return False
		raise

	victim = kill['victim']
	pc_attackers = 0
	parambatch = [(
		kill['killID'], True, victim['characterID'], victim['characterName'], victim['shipTypeID'],
		victim['allianceID'], victim['allianceName'], victim['corporationID'], victim['corporationName'], victim['factionID'], victim['factionName'],
		victim['damageTaken'], None, None, None,
	)]
	for attacker in kill['attackers']:
		final_blow = bool(int(attacker['finalBlow'])) # the stomp service sometimes hands us finalBlow: '0'
		parambatch.append((
			kill['killID'], False, attacker['characterID'], attacker['characterName'], attacker['shipTypeID'],
			attacker['allianceID'], attacker['allianceName'], attacker['corporationID'], attacker['corporationName'], attacker['factionID'], attacker['factionName'],
			attacker['damageDone'], final_blow, attacker['securityStatus'], attacker['weaponTypeID'],
		))
		if attacker['characterID'] != 0:
			pc_attackers += 1
	c.executemany('''
		INSERT INTO kill_characters (
			kill_id, victim, character_id, character_name, ship_type_id,
			alliance_id, alliance_name, corporation_id, corporation_name, faction_id, faction_name,
			damage, final_blow, security_status, weapon_type_id
		) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		''', parambatch
	)

	parambatch = []
	for item in kill.get('items', []): # stomp sometimes doesn't have items
		parambatch.append((kill['killID'], item['typeID'], item['flag'],
			item['qtyDropped'], item['qtyDestroyed'], item['singleton']))
	c.executemany('''
		INSERT INTO items (
			kill_id, type_id, flag, dropped, destroyed, singleton
		) VALUES(%s, %s, %s, %s, %s, %s)
		''', parambatch
	)

	try:
		result = db.get(c, 'SELECT cost FROM item_costs WHERE type_id = %s', (victim['shipTypeID']))
		cost = result['cost']
	except db.NoRowsException:
		cost = 0
	result = db.get(c, '''
		SELECT SUM(cost * (dropped + destroyed) / (singleton * 499.5 + 1)) AS item_cost
		FROM items
		JOIN item_costs ON items.type_id = item_costs.type_id
		WHERE kill_id = %s
		''', kill['killID'])
	if result['item_cost'] is not None:
		cost += result['item_cost']
	db.execute(c, 'INSERT INTO kill_costs (kill_id, cost) VALUES(%s, %s)', kill['killID'], cost)

	for entity_type in entity_types:
		entity_dict = defaultdict(lambda: {
			'name': None, 'killed': 0, 'lost': 0,
			'victim': False, 'attacker': False,
		})
		# set lost
		victim_id = victim[entity_type + 'ID']
		entity = entity_dict[victim_id]
		entity['name'] = victim[entity_type + 'Name']
		entity['lost'] = cost
		entity['victim'] = True
		# set killed
		for attacker in kill['attackers']:
			entity_id = attacker[entity_type + 'ID']
			if entity_id != 0:
				entity = entity_dict[entity_id]
				entity['name'] = attacker[entity_type + 'Name']
				entity['attacker'] = True
				if attacker[entity_type + 'ID'] != victim_id:
					try:
						entity['killed'] += cost / pc_attackers
					except ZeroDivisionError: # NPC-only kill
						assert attacker['characterID'] == 0
						entity['killed'] += cost

		parambatch = []
		for entity_id, info in entity_dict.items():
			sql = '''
				UPDATE {}s
				SET {}_name = %s, killed = killed + %s, lost = lost + %s
				WHERE {}_id = %s
				'''.format(entity_type, entity_type, entity_type)
			c.execute(sql, (info['name'], info['killed'], info['lost'], entity_id))
			if c.rowcount == 0:
				sql = 'INSERT INTO {}s ({}_id, {}_name, killed, lost) VALUES(%s, %s, %s, %s)'.format(
						entity_type, entity_type, entity_type)
				c.execute(sql, (entity_id, info['name'], info['killed'], info['lost']))

			if entity_id != 0 and entity_type != 'character':
				if entity['attacker']:
					parambatch.append((kill['killID'], entity_id, False))
				if entity['victim']:
					parambatch.append((kill['killID'], entity_id, True))

		if entity_type != 'character':
			sql = '''
				INSERT INTO kill_{}s (kill_id, {}_id, victim)
				VALUES(%s, %s, %s)
				'''.format(entity_type, entity_type)
			c.executemany(sql, parambatch)

	db.conn.commit()
	return True

def remove_kill(kill_id):
	with db.cursor() as c:
		entities = {}
		for entity_type in entity_types:
			entities[entity_type] = set()

		rows = db.query(c, '''
			SELECT victim, character_id, alliance_id, corporation_id
			FROM kill_characters
			WHERE kill_id = %s
			''', kill_id
		)
		for row in rows:
			if row['victim']:
				victim = row
			else:
				for entity_type in entity_types:
					entities[entity_type].add(row[entity_type + '_id'])

		cost = db.get(c, 'SELECT cost FROM kill_costs WHERE kill_id = %s', kill_id)['cost']
		parambatch = []
		for entity_type in entity_types:
			sql = 'UPDATE {}s SET killed = killed - %s WHERE {}_id IN ({})'.format(
					entity_type, entity_type, ','.join(map(str, entities[entity_type])))
			db.execute(c, sql, cost)

			sql = 'UPDATE {}s SET lost = lost - %s WHERE {}_id = %s'.format(entity_type, entity_type)
			db.execute(c, sql, cost, victim[entity_type + '_id'])

		for table in ['kill_characters', 'kill_costs', 'items', 'kills']:
			sql = 'DELETE FROM {} WHERE kill_id = %s'.format(table)
			db.execute(c, sql, kill_id)
		db.conn.commit()

def search(q):
	like_str = '{}%'.format(q.lower())
	with db.cursor() as c:
		alliances = db.query(c, '''
			SELECT alliance_id, alliance_name FROM alliances
			WHERE LOWER(alliance_name) LIKE %s LIMIT 25
			''', like_str)
		corps = db.query(c, '''
			SELECT corporation_id, corporation_name FROM corporations
			WHERE LOWER(corporation_name) LIKE %s LIMIT 25
			''', like_str)
		chars = db.query(c, '''
			SELECT character_id, character_name FROM characters
			WHERE LOWER(character_name) LIKE %s LIMIT 25
			''', like_str)
		systems = db.query(c, '''
			SELECT "solarSystemID" AS system_id, "solarSystemName" AS system_name
			FROM "mapSolarSystems"
			WHERE LOWER("solarSystemName") LIKE %s LIMIT 5
			''', like_str)
		ships = db.query(c, '''
			SELECT "typeID" AS ship_id, "typeName" AS ship_name FROM "invTypes"
			JOIN "invGroups" ON "invTypes"."groupID" = "invGroups"."groupID"
			WHERE LOWER("typeName") LIKE %s AND "invGroups"."categoryID" = 6 LIMIT 5
			''', like_str) # 6 == ship
	return {
		'alliances': alliances,
		'corporations': corps,
		'characters': chars,
		'systems': systems,
		'ships': ships,
	}

def kill_list(entity_type, entity_id, list_type, page):
	with db.cursor() as c:
		if entity_type == 'time':
			stats = None
		else:
			if entity_type == 'system':
				sql = 'SELECT "solarSystemName" AS system_name FROM "mapSolarSystems" WHERE "solarSystemID" = %s'
			elif entity_type == 'ship':
				sql = 'SELECT "typeName" AS ship_name FROM "invTypes" WHERE "typeID" = %s'
			else:
				sql = 'SELECT {}_name, killed, lost FROM {}s WHERE {}_id = %s'.format(entity_type, entity_type, entity_type)
			try:
				stats = db.get(c, sql, entity_id)
			except db.NoRowsException:
				return None
		# the combination of DISTINCT and and ORDER BY means we can't join kills or we get seq scans
		# get kill_ids from chars, then get kill data on those ids
		page_size = 50
		if entity_type == 'time':
			sql = 'SELECT kill_id FROM kills WHERE kill_time BETWEEN %s AND %s ORDER BY kill_id DESC LIMIT %s OFFSET %s'
			start, end = entity_id
			kills = db.query(c, sql, start, end, page_size, (page - 1) * page_size)
		else:
			if list_type == 'kills':
				extra_cond = 'AND victim = FALSE'
			elif list_type == 'losses':
				extra_cond = 'AND victim = TRUE'
			elif list_type is None:
				extra_cond = ''

			if entity_type == 'system':
				sql = 'SELECT kill_id FROM kills WHERE solar_system_id = %s'
			elif entity_type == 'ship':
				if list_type is None:
					# psql query planner won't use our index otherwise
					extra_cond = 'AND victim IN (TRUE, FALSE)'
				sql = 'SELECT kill_id FROM kill_characters WHERE ship_type_id = %s {}'.format(extra_cond)
			else:
				sql = '''
					SELECT kill_id FROM kill_{}s
					WHERE {}_id = %s {}
					'''.format(entity_type, entity_type, extra_cond)
			sql += '\nORDER BY kill_id DESC LIMIT %s OFFSET %s'
			kills = db.query(c, sql, entity_id, page_size, (page - 1) * page_size)
		if len(kills) == 0:
			return None
		kill_ids = list(map(operator.itemgetter('kill_id'), kills))
		kills = db.query(c, '''
			SELECT kills.kill_id, kill_time, cost,
				"solarSystemName" AS system_name, security, "regionName" AS region,
				class AS wh_class, static1, static2
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			LEFT JOIN wh_systems ON solar_system_id = wh_systems.id
			JOIN "mapSolarSystems" ON solar_system_id = "solarSystemID"
			JOIN "mapRegions" ON "mapSolarSystems"."regionID" = "mapRegions"."regionID"
			WHERE kills.kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, "typeName" AS ship_name
			FROM kill_characters
			JOIN "invTypes" ON ship_type_id = "typeID"
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

	if entity_type == 'ship_type':
		stats['killed'] = stats['lost'] = 0
	kills.sort(key=operator.itemgetter('kill_id'), reverse=True)
	for kill in kills:
		kill['kill_time'] = _format_kill_time(kill['kill_time'])
		kill['security_status'] = _security_status(kill['security'], kill['wh_class'])
		chars = characters[kill['kill_id']]
		kill['victim'] = chars['victim']
		kill['final_blow'] = chars['final_blow']
		kill['attackers'] = chars['attackers']
		if entity_type == 'ship_type':
			if chars['victim']['ship_type_id'] == entity_id:
				stats['lost'] += kill['cost']
			else:
				stats['killed'] += kill['cost']
	return {'stats': stats, 'kills': kills}

def kill(kill_id):
	with db.cursor() as c:
		try:
			kill = db.get(c, '''
				SELECT kill_time, cost, "solarSystemName" AS system_name, security,
					class AS wh_class, static1, static2, effect AS wh_effect
				FROM kills
				JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
				LEFT JOIN wh_systems ON solar_system_id = id
				JOIN "mapSolarSystems" ON solar_system_id = "solarSystemID"
				WHERE kills.kill_id = %s
				''', kill_id)
		except db.NoRowsException:
			return None
		kill['kill_time'] = _format_kill_time(kill['kill_time'])
		kill['security_status'] = _security_status(kill['security'], kill['wh_class'])

		characters = db.query(c, '''
			SELECT character_id, character_name, damage, victim, final_blow,
				corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, weapon_type_id,
				ship."typeName" AS ship_name, weapon."typeName" AS weapon_name
			FROM kill_characters
			JOIN "invTypes" AS ship ON ship_type_id = ship."typeID"
			LEFT JOIN "invTypes" AS weapon ON weapon_type_id = weapon."typeID"
			WHERE kill_id = %s
			ORDER BY damage DESC
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
			ship_cost = db.get(c, 'SELECT cost FROM item_costs WHERE type_id = %s',
					victim['ship_type_id'])
			victim['ship_cost'] = ship_cost['cost']
		except db.NoRowsException:
			victim['ship_cost'] = 0

		# see update_costs for an explanation of the ORDER BY
		item_rows = db.query(c, '''
			SELECT items.type_id, flag, dropped, destroyed, singleton,
				cost, "typeName" AS item_name
			FROM items
			LEFT JOIN item_costs ON item_costs.type_id = items.type_id
			JOIN "invTypes" ON items.type_id = "typeID"
			WHERE kill_id = %s
			ORDER BY (cost * (dropped + destroyed) / (singleton * 499.5 + 1)) DESC
			''', kill_id)
		items = defaultdict(list)
		dropped = 0
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

			cost = item['cost'] or 0
			dropped += cost * item['dropped'] / (item['singleton'] * 499.5 + 1)
		kill['dropped'] = dropped

		module_slots = ['high', 'medium', 'low']
		fitting_items = set()
		for slot in module_slots:
			if slot not in items:
				continue # otherwise, defaultdict creates lists for them
			fitting_items.update(map(operator.itemgetter('type_id'), items[slot]))
		if len(fitting_items):
			# 11: requires low, 12: requires high, 13: requires medium; :CCP:
			modules = db.query(c, '''
				SELECT DISTINCT "typeID" AS type_id FROM "dgmTypeEffects"
				WHERE "typeID" IN ({}) and "effectID" IN (11, 12, 13)
				'''.format(','.join(map(str, fitting_items))))
			module_ids = set(map(operator.itemgetter('type_id'), modules))
			for slot in module_slots:
				if slot not in items:
					continue
				for item in items[slot]:
					if item['type_id'] not in module_ids:
						item['charge'] = True

		slot_rows = db.query(c, '''
			SELECT "attributeID", "valueInt", "valueFloat" FROM "dgmTypeAttributes"
			WHERE "typeID" = %s AND "attributeID" IN (12, 13, 14, 1137, 1367)
				AND ("valueInt" != 0 OR "valueFloat" != 0.0)
			''', victim['ship_type_id'])
		slot_mapping = {12: 'low', 13: 'medium', 14: 'high', 1137: 'rig', 1367: 'subsystem'}
		slots = dict.fromkeys(slot_mapping.values(), 0)
		for attr in slot_rows:
			slot = slot_mapping[attr['attributeID']]
			slots[slot] = attr['valueInt'] or int(attr['valueFloat']) # wtf CCP
		if 'subsystem' in items:
			sub_ids = map(lambda s: str(s['type_id']), items['subsystem'])
			modifier_rows = db.query(c, '''
				SELECT "attributeID", "valueFloat" FROM "dgmTypeAttributes"
				WHERE "typeID" IN ({}) AND "attributeID" in (1374, 1375, 1376) and "valueFloat" != 0.0
				'''.format(','.join(sub_ids)))
			slot_mapping = {1374: 'high', 1375: 'medium', 1376: 'low'} # that's right, it's backwards for subs!
			for modifier in modifier_rows:
				slot = slot_mapping[modifier['attributeID']]
				slots[slot] += int(modifier['valueFloat']) # strangely, an improvement

		dgm = Dogma()
		dgm.set_ship(victim['ship_type_id'])
		dogma = {'hp': {}, 'resists': {}, 'ehp': 0.0, 'velocity': 0.0}
		for slot in ['subsystem', 'medium', 'low', 'rig']:
			if slot not in items:
				continue
			for item in items[slot]:
				dgm.add_module(item['type_id'])
		for hp_type, attr in dgm.hp_types.items():
			dogma['hp'][hp_type] = dgm.get_attribute(attr)
			resists = {}
			average_res = 0.0
			for resist_type, attr in dgm.resists[hp_type].items():
				res = dgm.get_attribute(attr)
				average_res += res
				resists[resist_type] = 1 - res
			average_res /= len(dgm.resists[hp_type])
			dogma['ehp'] += dogma['hp'][hp_type] / average_res
			dogma['resists'][hp_type] = resists
		dogma['velocity'] = dgm.get_attribute(dgm.max_velocity)
	return {
		'kill': kill,
		'victim': victim,
		'final_blow': final_blow,
		'attackers': attackers,
		'items': items,
		'slots': slots,
		'dogma': dogma,
	}

def battle_report(kill_id):
	with db.cursor() as c:
		# collect some data
		try:
			meta = db.get(c, '''
				SELECT kill_time, solar_system_id, "solarSystemName" AS system_name,
					security, class AS wh_class, static1, static2, effect AS wh_effect
				FROM kills
				LEFT JOIN wh_systems ON solar_system_id = id
				JOIN "mapSolarSystems" ON solar_system_id = "solarSystemID"
				WHERE kill_id = %s
				''', kill_id)
		except db.NoRowsException:
			return None
		after = meta['kill_time'] - datetime.timedelta(minutes=15)
		before = meta['kill_time'] + datetime.timedelta(minutes=15)
		kill_rows = db.query(c, '''
			SELECT kills.kill_id, kill_time, cost
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			WHERE solar_system_id = %s AND kill_time BETWEEN %s AND %s
			''', meta['solar_system_id'], after, before)
		kill_ids = list(map(operator.itemgetter('kill_id'), kill_rows))
		char_rows = db.query(c, '''
			SELECT
				kill_id, victim, final_blow, damage,
				character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name,
				ship_type_id, "typeName" AS ship_name
			FROM kill_characters
			JOIN "invTypes" ON ship_type_id = "typeID"
			WHERE kill_id IN ({})
			'''.format(','.join(map(str, kill_ids))))

	# organize characters and kills
	characters = {}
	for char in char_rows: # generate canonical chars
		character_id = char['character_id']
		canonical_char = characters.get(character_id)
		if canonical_char is None:
			characters[character_id] = char
		elif char['victim'] and not canonical_char['victim']: # prefer canonicalizing victims
			characters[character_id] = char
		elif canonical_char['ship_type_id'] == 0: # prefer canonicalizing characters with ships
			characters[character_id] = char
		elif canonical_char['victim'] and canonical_char['ship_type_id'] in [670, 33328]: # pod
			characters[character_id] = char
			char['pod'] = canonical_char['kill_id']
		elif char['victim'] and char['ship_type_id'] in [670, 33328]:
			canonical_char['pod'] = char['kill_id']
		char['faction'] = None
		char['damage_dealt'] = 0
		char['sub_chars'] = []
	kills = {}
	for kill in kill_rows:
		kills[kill['kill_id']] = {'victim': None, 'attackers': [], 'cost': kill['cost']}
	for char in char_rows:
		canonical_char = characters[char['character_id']]
		kill = kills[char['kill_id']]
		if char['victim']:
			kill['victim'] = canonical_char
			if id(char) == id(canonical_char):
				canonical_char['death_id'] = canonical_char['kill_id']
				canonical_char['cost'] = kill['cost']
		else:
			kill['attackers'].append(canonical_char)
			canonical_char['damage_dealt'] += char['damage']

		# add this as a sub char?
		add_sub_char = True
		if id(char) == id(canonical_char) or char['ship_type_id'] in [0, 670, 33328]:
			add_sub_char = False
		elif not char['victim']:
			if char['ship_type_id'] == canonical_char['ship_type_id']:
				add_sub_char = False
			else:
				for sub_char in canonical_char['sub_chars']:
					if sub_char['ship_type_id'] == char['ship_type_id']:
						add_sub_char = False
						break
		if add_sub_char:
			canonical_char['sub_chars'].append(char)
			if char['victim']:
				char['death_id'] = char['kill_id']
				char['cost'] = kills[char['kill_id']]['cost']

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
						break
				else:
					for attacker in kill['attackers']:
						# settle for an NPC
						if attacker['faction'] is not None:
							break
					else:
						continue
				attacker_faction = attacker['faction']
				victim['faction'] = 1 - attacker_faction
				change = True
			for attacker in kill['attackers']:
				if attacker['faction'] is None and \
						(attacker['corporation_id'] != victim['corporation_id'] or \
						len(kill['attackers']) < 3):
					attacker['faction'] = attacker_faction
					change = True

	# prepare output lists
	factions = [[], [], []]
	del_keys = ['kill_id', 'final_blow', 'victim', 'damage']
	for char in characters.values():
		if char['faction'] is None:
			char['faction'] = 2
		for key in del_keys:
			del char[key]
		factions[char['faction']].append(char)
		for sub_char in char['sub_chars']:
			for key in del_keys:
				del sub_char[key]
			factions[char['faction']].append(sub_char)
		del char['sub_chars']
	for faction in factions:
		faction.sort(key=operator.itemgetter('damage_dealt'), reverse=True)

	meta['kill_time'] = _format_kill_time(meta['kill_time'])
	meta['security_status'] = _security_status(meta['security'], meta['wh_class'])
	return {'meta': meta, 'factions': factions}

def top_cost():
	with db.cursor() as c:
		last_kill = db.get(c, 'SELECT MAX(kill_id) AS kill_id FROM kills')
		kills = db.query(c, '''
			SELECT kills.kill_id, cost, solar_system_id, kill_time,
				ship_type_id, "typeName" AS ship_name
			FROM kills
			JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
			JOIN kill_characters ON kill_characters.kill_id = kills.kill_id
			JOIN "invTypes" ON "typeID" = ship_type_id
			WHERE victim = TRUE AND kills.kill_id IN (
				SELECT kill_id FROM kill_costs WHERE kill_id > %s
				ORDER BY cost DESC LIMIT 25
			)
			ORDER BY cost DESC
			''', last_kill['kill_id'] - 2500)
		# joining "mapSolarSystems" on the initial query causes filesort on large dbs for some reason
		# do a manual join
		system_ids = set(map(operator.itemgetter('solar_system_id'), kills))
		system_rows = db.query(c, '''
			SELECT "solarSystemID" as solar_system_id, "solarSystemName" AS system_name,
				security, class AS wh_class
			FROM "mapSolarSystems"
			LEFT JOIN wh_systems ON "solarSystemID" = wh_systems.id
			WHERE "solarSystemID" IN ({})
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
					kills.kill_id, kill_costs.cost AS total_cost, item_costs.cost AS hull_cost, "typeName" AS ship_name
				FROM kills
				JOIN kill_costs ON kill_costs.kill_id = kills.kill_id
				JOIN kill_characters ON kill_characters.kill_id = kills.kill_id
				JOIN item_costs ON item_costs.type_id = ship_type_id
				JOIN "invTypes" ON "typeID" = ship_type_id
				WHERE victim = TRUE AND kills.kill_id > %s
			''', kill_id)
	return kills

def _format_kill_time(kill_time):
	return kill_time.strftime('%Y-%m-%d %H:%M')

def _security_status(security, wh_class):
		if wh_class:
			security_status = 'wspace'
		elif security >= 0.45:
			security_status = 'high'
		elif security > 0.0:
			security_status = 'low'
		else:
			security_status = 'null'
		return security_status
