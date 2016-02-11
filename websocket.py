#!/usr/bin/env python3

import atexit
import json
import sys
import time
import traceback

import tornado.gen
import tornado.ioloop
import tornado.websocket

import daemon
import db
import db.queries
import log

conn = None

@tornado.gen.coroutine
def main():
	if len(sys.argv) == 2 and sys.argv[1] == '-d':
		daemon.daemonize()

	def exit():
		conn.close()
		log.close()
	atexit.register(exit)

	while True:
		run()
		time.sleep(15)

@tornado.gen.coroutine
def run():
	conn = yield tornado.websocket.websocket_connect('wss://ws.eve-kill.net/kills', connect_timeout=5)
	msg = yield conn.read_message()
	assert(isinstance(json.loads(msg), list)) # server info line

	while True:
		msg = yield conn.read_message()
		if msg is None:
			log.write('websocket disconnected')
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
