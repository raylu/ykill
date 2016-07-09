#!/usr/bin/env python3

import sys
import time
import traceback

import daemon
if len(sys.argv) == 2 and sys.argv[1] == '-d':
	daemon.daemonize() # need to do this before importing db

import requests

import db
import db.queries
import log

inserted = 0
def handle_package(package):
	global inserted

	if package is None:
		return

	try:
		kill = package['killmail']

		# get ids and names
		munge(kill)
		# move items off of victim
		kill['items'] = kill['victim']['items']
		del kill['victim']['items']
		for item in kill['items']:
			item['typeID'] = item.pop('itemTypeID')
			item['qtyDropped'] = item.pop('quantityDropped', 0)
			item['qtyDestroyed'] = item.pop('quantityDestroyed', 0)
		# make sure entities are present
		# (alliance and faction can be missing for players; character and corporation can be missing for NPCs)
		for char in kill['attackers'] + [kill['victim']]:
			for entity in db.queries.entity_types + ['faction']:
				if entity + 'ID' not in char:
					char[entity + 'ID'] = 0
					char[entity + 'Name'] = ''
		# make sure weapon and ship are present
		for char in kill['attackers']:
			char.setdefault('weaponTypeID', 0)
			char.setdefault('shipTypeID', 0)

		with db.cursor() as c:
			db.queries.insert_kill(c, kill)
		inserted += 1
		if inserted % 500 == 0:
			log.write('redisq inserted %s kills' % inserted)
	except:
		log.write('redisq error: %s\n%s' % (package, traceback.format_exc()))
		log.close()
		sys.exit()

def munge(data):
	if isinstance(data, list):
		for el in data:
			munge(el)
	elif isinstance(data, dict):
		extra = {}
		for k, v in data.items():
			if isinstance(v, dict) and 'id_str' in v:
				extra[k + 'ID'] = v['id']
				name = v.get('name')
				if name:
					extra[k + 'Name'] = name
			else:
				munge(v)
		data.update(extra)

def main():
	rs = requests.Session()
	while True:
		try:
			data = rs.get('http://redisq.zkillboard.com/listen.php').json()
			handle_package(data['package'])
		except KeyboardInterrupt:
			break
		except (ValueError, requests.exceptions.RequestException):
			log.write('redisq error; waiting 5 minutes\n%s' % traceback.format_exc())
			time.sleep(300)
		log.flush()
main()
