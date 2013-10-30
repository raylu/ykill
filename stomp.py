#!/usr/bin/env python3

import atexit
import json
import sys
import time
import traceback

import daemon
import db
import importer
import log
import stomp

class KillListener:
	inserted = 0

	def on_message(self, headers, message):
		try:
			data = json.loads(message)
			with db.cursor() as c:
				importer.insert_kill(c, data)
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

conn = stomp.Connection([('stomp.zkillboard.com', 61613)])
conn.set_listener('', KillListener())

if len(sys.argv) == 2 and sys.argv[1] == '-d':
	daemon.daemonize()

def exit():
	conn.disconnect()
	log.close()
atexit.register(exit)

conn.start()
conn.connect()
log.write('stomp subscribing')
conn.subscribe(destination='/topic/kills', id=1, ack='auto')
while True:
	try:
		time.sleep(60)
	except KeyboardInterrupt:
		break
	log.flush()
