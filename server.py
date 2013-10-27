#!/usr/bin/env python3

import os
import sys

import cleancss
import daemon
import tornado.httpclient
import tornado.ioloop
import tornado.web

from config import web as config
import web.api

class BaseHandler(tornado.web.RequestHandler):
	def render(self, *args, **kwargs):
		kwargs['api_host'] = config.api_host
		return super(BaseHandler, self).render(*args, **kwargs)

	def render_string(self, *args, **kwargs):
		s = super(BaseHandler, self).render_string(*args, **kwargs)
		return s.replace(b'\n', b'') # this is like Django's {% spaceless %}

class MainHandler(BaseHandler):
	def get(self):
		self.render('home.html')

class SearchHandler(BaseHandler):
	def get(self):
		self.render('search.html')

class KillListHandler(BaseHandler):
	def get(self, entity_type):
		self.render('kill_list.html')

class KillHandler(BaseHandler):
	def get(self):
		self.render('kill.html')

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
			(r'/(alliance|corporation|character)/.+', KillListHandler),
			(r'/kill/.+', KillHandler),
			(r'/(css/.+)\.css', CSSHandler),
		],
		template_path=os.path.join(os.path.dirname(__file__), 'web/templates'),
		debug=config.debug,
	).listen(config.port)
	web.api.start()
	if len(sys.argv) == 2 and sys.argv[1] == '-d':
		daemon.daemonize()
	print('listening on :%d' % config.port)
	tornado.ioloop.IOLoop.instance().start()
