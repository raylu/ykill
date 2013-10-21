import datetime
import json

import tornado.web

from config import web as config
import db.queries

class JSONDateEncoder(json.JSONEncoder):
	def default(self, data):
		if isinstance(data, datetime.datetime):
			return str(data)
		return super(JSONDateEncoder, self).default(data)

class APIHandler(tornado.web.RequestHandler):
	def set_default_headers(self):
		self.set_header('Access-Control-Allow-Origin', '*')
		self.set_header('Access-Control-Allow-Headers', 'X-Requested-With, X-Request')

	def compute_etag(self):
		return None

	def respond_json(self, data):
		self.set_header('Content-Type', 'application/json; charset=UTF-8')
		for chunk in JSONDateEncoder(indent='\t').iterencode(data):
			self.write(chunk)
		self.finish()

	def options(self, *args):
		return

class SearchHandler(APIHandler):
	def get(self):
		q = self.get_argument('q')
		data = db.queries.search(q)
		self.respond_json(data)

class CorporationHandler(APIHandler):
	def get(self, corp_id):
		kills = db.queries.corporation(corp_id)
		self.respond_json(kills)

class KillHandler(APIHandler):
	def get(self, kill_id):
		kill = db.queries.kill(kill_id)
		self.respond_json(kill)

def start():
	tornado.web.Application(
		handlers=[
			(r'/search', SearchHandler),
			(r'/corporation/(.+)', CorporationHandler),
			(r'/kill/(.+)', KillHandler),
		],
		debug=config.debug,
	).listen(config.api_port)
	print('listening on :%d' % config.api_port)