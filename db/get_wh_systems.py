#!/usr/bin/env python3

import oursql
import requests

classes = {}
conn = oursql.connect(db='eve', user='eve', passwd='eve')
with conn as cursor:
	cursor.execute('''
		SELECT solarSystemID, wormholeClassID FROM mapSolarSystems
		JOIN mapLocationWormholeClasses ON regionID = locationID
	''')
	for r in cursor:
		classes[r[0]] = r[1]

rs = requests.Session()

r = rs.get('https://github.com/marbindrakon/eve-wspace/raw/develop/evewspace/Map/fixtures/wormholetypes.json')
wormholes = {}
for wormhole in r.json():
	destination = wormhole['fields']['target']
	if destination.endswith(' W-Space'):
		destination = destination[:2]
	elif destination.endswith('sec'):
		destination = destination[:-3].lower()
	else:
		continue
	wormholes[wormhole['pk']] = destination

r = rs.get('https://github.com/marbindrakon/eve-wspace/raw/develop/evewspace/Map/fixtures/wormholestatics.json')
statics = r.json()
print('INSERT INTO `wh_systems` VALUES')
for i, system in enumerate(statics):
	system_id = system['pk']
	system_class = classes[system_id]

	effect = system['fields']['effect']
	if effect:
		effect = '"%s"' % effect
	else:
		effect = 'NULL'

	static1 = system['fields']['static1']
	if static1:
		static1 = '"%s"' % wormholes[static1]
	else:
		static1 = 'NULL'
	static2 = system['fields']['static2']
	if static2:
		static2 = '"%s"' % wormholes[static2]
	else:
		static2 = 'NULL'

	line = '(%d, %d, %s, %s, %s)' % (system_id, system_class, effect, static1, static2)
	print(line, end='')
	if i == len(statics) - 1:
		print(';')
	else:
		print(',')
