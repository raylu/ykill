#!/usr/bin/env python3

import atexit
import json
import sys
import traceback

import tornado.gen
import tornado.ioloop
import tornado.websocket

import daemon
import db
import db.queries
import log

@tornado.gen.coroutine
def main():
	conn = yield tornado.websocket.websocket_connect('wss://ws.eve-kill.net/', connect_timeout=5)

	if len(sys.argv) == 2 and sys.argv[1] == '-d':
		daemon.daemonize()

	def exit():
		log.close()
		conn.close()
	atexit.register(exit)

	while True:
		msg = yield conn.read_message()
		if msg is None:
			log.write('stomp disconnected')
			log.flush()
			break
		handle_message(msg)

inserted = 0
def handle_message(message):
	global inserted
	try:
		data = json.loads(message)
		with db.cursor() as c:
			db.queries.insert_kill(c, data)
		inserted += 1
		if inserted % 500 == 0:
			log.write('websocket inserted {} kills'.format(inserted))
	except:
		log.write('websocket error: {}\n{}'.format(message, traceback.format_exc()))
		raise

if __name__ == '__main__':
	tornado.ioloop.IOLoop.instance().run_sync(main)
