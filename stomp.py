#!/usr/bin/env python3

import atexit
import json
import sys
import time
import traceback

import daemon
if len(sys.argv) == 2 and sys.argv[1] == '-d':
	daemon.daemonize() # need to do this before importing db

import config
import db
import db.queries
import log
import stomp

class KillListener:
	inserted = 0

	def on_message(self, headers, message):
		try:
			data = json.loads(message)
			with db.cursor() as c:
				db.queries.insert_kill(c, data)
			self.inserted += 1
			if self.inserted % 500 == 0:
				log.write('stomp inserted {} kills'.format(self.inserted))
		except Exception as e:
			log.write('stomp error: {}, {}\n{}'.format(headers, message, traceback.format_exc()))

	def on_error(self, headers, message):
		log.write('stomp error: {}, {}'.format(headers, message))
		log.flush()

	def on_disconnected(self):
		log.write('stomp disconnected')
		log.flush()

conn = stomp.Connection([('stomp.eve-kill.net', 61613)])
conn.set_listener('', KillListener())

def exit():
	if conn.is_connected():
		conn.disconnect()
	log.close()
atexit.register(exit)

conn.start()
conn.connect(config.db.stomp_username, config.db.stomp_password, wait=True)
log.write('stomp subscribing')
conn.subscribe(destination='/topic/kills', id=1, ack='auto')
while True:
	try:
		time.sleep(60)
	except KeyboardInterrupt:
		break
	log.flush()
