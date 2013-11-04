#!/usr/bin/env python3

from collections import defaultdict

import db

def update_for_kill(kill):
	with db.cursor() as c:
		char_rows = db.query(c, '''
			SELECT alliance_id, alliance_name, corporation_id, corporation_name,
				character_id, character_name, victim
			FROM kill_characters WHERE kill_id = ?
			''', kill['kill_id'])
		for row in char_rows:
			if row['victim']:
				victim_alliance = row['alliance_id']
				victim_corp = row['corporation_id']
				break
		entities = {
			'alliance': victim_alliance,
			'corporation': victim_corp,
			'character': None,
		}
		for entity_type, victim in entities.items():
			entity_dict = defaultdict(lambda: {'name': None, 'killed': 0, 'lost': 0})
			for row in char_rows:
				entity_id = row[entity_type + '_id']
				if entity_id != 0:
					entity = entity_dict[entity_id]
					entity['name'] = row[entity_type + '_name']
					if row['victim']:
						entity['lost'] = kill['cost']
					elif row[entity_type + '_id'] != victim:
						entity['killed'] = kill['cost']

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

def main():
	with db.cursor() as c:
		print('truncating')
		db.execute(c, 'TRUNCATE TABLE alliances')
		db.execute(c, 'TRUNCATE TABLE corporations')
		db.execute(c, 'TRUNCATE TABLE characters')
		print('updating stats')
		db.execute(c, 'SELECT kill_id, cost from kill_costs WHERE cost > 0 ORDER BY kill_id ASC')
		i = 0
		while True:
			r = c.fetchone()
			if r is None:
				break
			update_for_kill(r)
			i += 1
			if i % 1000 == 0:
				print('updated for', i, 'kills')

if __name__ == '__main__':
	main()
