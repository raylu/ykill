#!/usr/bin/env python3

from collections import defaultdict
import json
import operator
import os

import cleancss
import tornado.httpclient
import tornado.ioloop
import tornado.web

from config import web as config
import db

class BaseHandler(tornado.web.RequestHandler):
	def render(self, *args, **kwargs):
		kwargs['host'] = config.host
		return super(BaseHandler, self).render(*args, **kwargs)

	def render_string(self, *args, **kwargs):
		s = super(BaseHandler, self).render_string(*args, **kwargs)
		return s.replace(b'\n', b'') # this is like Django's {% spaceless %}

class MainHandler(BaseHandler):
	def get(self):
		self.render('home.html')

class SearchHandler(BaseHandler):
	def get(self):
		q = self.get_argument('q')
		with db.cursor() as c:
			corps = db.query(c, '''
				SELECT DISTINCT corporation_id, corporation_name FROM characters
				WHERE corporation_name LIKE ?
				''', '%{}%'.format(q))
		self.render('search.html', corps=corps)

class CorporationHandler(BaseHandler):
	def get(self, corp_id):
		with db.cursor() as c:
			kills = db.query(c, '''
				SELECT DISTINCT(kills.kill_id), kill_time FROM kills
				JOIN characters on characters.kill_id = kills.kill_id
				WHERE corporation_id = ?
				''', corp_id)
			kill_ids = list(map(operator.itemgetter('kill_id'), kills))
			char_rows = db.query(c, '''
				SELECT
					kill_id, victim, final_blow,
					character_id, character_name, corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name
				FROM characters
				WHERE kill_id IN ({})
				'''.format(','.join(map(str, kill_ids))))
			characters = defaultdict(dict)
			for char in char_rows:
				kill_id = char['kill_id']
				if char['victim']:
					characters[kill_id]['victim'] = char
				elif char['final_blow']:
					characters[kill_id]['final_blow'] = char
			for kill in kills:
				chars = characters[kill['kill_id']]
				kill['victim'] = chars['victim']
				kill['final_blow'] = chars['final_blow']
		self.render('corporation.html', kills=kills)

class KillHandler(BaseHandler):
	def get(self, kill_id):
		with db.cursor() as c:
			kill = db.get(c, '''
				SELECT kill_time, solarSystemName, security FROM kills
				JOIN eve.mapSolarSystems on solar_system_id = solarSystemID
				WHERE kill_id = ?
				''', kill_id)
			characters = db.query(c, '''
				SELECT ship_type_id, character_id, character_name,
					corporation_id, corporation_name, alliance_id, alliance_name, faction_id, faction_name
					typeName
				FROM characters
				JOIN eve.invTypes on ship_type_id = typeID
				WHERE kill_id = ?
				''', kill_id)
		self.render('kill.html', kill=kill, characters=characters)

class CSSHandler(tornado.web.RequestHandler):
	def get(self, css_path):
		css_path = os.path.join(os.path.dirname(__file__), 'web', 'static', css_path) + '.ccss'
		with open(css_path, 'r') as f:
			self.set_header('Content-Type', 'text/css')
			self.write(cleancss.convert(f))

if __name__ == '__main__':
	tornado.web.Application(
		handlers=[
			(r'/', MainHandler),
			(r'/search', SearchHandler),
			(r'/corporation/(.+)', CorporationHandler),
			(r'/kill/(.+)', KillHandler),
			(r'/(css/.+)\.css', CSSHandler),
		],
		template_path=os.path.join(os.path.dirname(__file__), 'web/templates'),
		cookie_secret=config.cookie_secret,
		debug=config.debug,
	).listen(config.port)
	print('listening on :%d' % config.port)
	tornado.ioloop.IOLoop.instance().start()
