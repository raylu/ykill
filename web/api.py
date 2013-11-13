import datetime
import json

import tornado.web

from config import web as config
import db.queries

class APIBaseHandler(tornado.web.RequestHandler):
	def set_default_headers(self):
		self.set_header('Access-Control-Allow-Origin', '*')
		self.set_header('Access-Control-Allow-Headers', 'X-Requested-With, X-Request')

	def compute_etag(self):
		return None

	def respond_json(self, data):
		self.set_header('Content-Type', 'application/json; charset=UTF-8')
		for chunk in json.JSONEncoder(indent='\t').iterencode(data):
			self.write(chunk)
		self.finish()

	def options(self, *args):
		return

class SearchHandler(APIBaseHandler):
	def get(self):
		q = self.get_argument('q')
		data = db.queries.search(q)
		self.respond_json(data)

class KillListHandler(APIBaseHandler):
	def get(self, entity_type, entity_id, list_type):
		if list_type in ['/kills', '/losses']:
			list_type = list_type[1:]
		elif list_type is not None:
			raise tornado.web.HTTPError(400)
		page = int(self.get_argument('page', 1))
		kills = db.queries.kill_list(entity_type, entity_id, list_type, page)
		if kills is None:
			raise tornado.web.HTTPError(404)
		self.respond_json(kills)

class KillHandler(APIBaseHandler):
	def get(self, kill_id):
		kill = db.queries.kill(kill_id)
		if kill is None:
			raise tornado.web.HTTPError(404)
		self.respond_json(kill)

class BattleReportHandler(APIBaseHandler):
	def get(self, kill_id):
		try:
			kill_id = int(kill_id)
		except ValueError:
			raise tornado.web.HTTPError(400)
		kills = db.queries.battle_report(kill_id)
		if kills is None:
			raise tornado.web.HTTPError(404)
		self.respond_json(kills)

class TopCostHandler(APIBaseHandler):
	def get(self):
		kills = db.queries.top_cost()
		self.respond_json(kills)

class LastHandler(APIBaseHandler):
	def get(self, kill_id):
		if kill_id is not None:
			try:
				kill_id = int(kill_id[1:])
			except ValueError:
				raise tornado.web.HTTPError(400)
		kills = db.queries.last(kill_id)
		self.respond_json(kills)

def start():
	tornado.web.Application(
		handlers=[
			(r'/search', SearchHandler),
			(r'/(alliance|corporation|character|system)/(\d+)(/.*)?', KillListHandler),
			(r'/kill/(.+)/battle_report', BattleReportHandler),
			(r'/kill/(.+)', KillHandler),
			(r'/top/cost', TopCostHandler),
			(r'/last(/.+)?', LastHandler),
		],
		debug=config.debug,
	).listen(config.api_port)
	print('listening on :%d' % config.api_port)
