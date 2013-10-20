import oursql

from config import db as dbconfig

conn = oursql.connect(host=dbconfig.host, db=dbconfig.database, user=dbconfig.user, passwd=dbconfig.password, autoreconnect=True)

def cursor():
	return conn.cursor(oursql.DictCursor)

def execute(cursor, sql, *values):
	cursor.execute(sql, values)

def query(cursor, sql, *values):
	execute(cursor, sql, *values)
	return cursor.fetchall()

def get(cursor, sql, *values):
	execute(cursor, sql, *values)
	result = cursor.fetchone()
	if result is None:
		raise Exception('no rows returned for query: {} with values {}'.format(sql, values))
	if cursor.fetchone() is not None:
		raise Exception('multiple results returned for query'.format(sql, values))
	return result
