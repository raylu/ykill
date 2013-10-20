#!/usr/bin/env python3

import json
import operator
import os

import cleancss
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.web

from config import web as config

class BaseHandler(tornado.web.RequestHandler):
	def render(self, *args, **kwargs):
		kwargs['host'] = config.host
		return super(BaseHandler, self).render(*args, **kwargs)

	def render_string(self, *args, **kwargs):
		s = super(BaseHandler, self).render_string(*args, **kwargs)
		return s.replace(b'\n', b'') # this is like Django's {% spaceless %}

class MainHandler(BaseHandler):
	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		http_client = tornado.httpclient.AsyncHTTPClient()
		kills_url = 'https://zkillboard.com/api/kills/corporationID/98182803/limit/1'
		losses_url = 'https://zkillboard.com/api/losses/corporationID/98182803/limit/1'
		kills_res, losses_res = yield [http_client.fetch(kills_url), http_client.fetch(losses_url)]
		kills = json.loads(kills_res.body.decode('utf-8'))
		losses = json.loads(losses_res.body.decode('utf-8'))
		kills = sorted(kills + losses, key=operator.itemgetter('killTime'), reverse=True)
		self.render('home.html', kills=kills)


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
			(r"/(css/.+)\.css", CSSHandler),
		],
		template_path=os.path.join(os.path.dirname(__file__), 'templates'),
		static_path=os.path.join(os.path.dirname(__file__), 'static'),
		cookie_secret=config.cookie_secret,
		debug=config.debug,
	).listen(config.port)
	print('listening on :%d' % config.port)
	tornado.ioloop.IOLoop.instance().start()
