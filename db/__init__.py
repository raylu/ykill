import psycopg2
import psycopg2.extras

from config import db as dbconfig

conn = psycopg2.connect(dbconfig.dsn)

def cursor():
	return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def execute(cursor, sql, *values):
	cursor.execute(sql, values)

def query(cursor, sql, *values):
	execute(cursor, sql, *values)
	return cursor.fetchall()

class NoRowsException(Exception): pass
class MultipleRowsException(Exception): pass

def get(cursor, sql, *values):
	execute(cursor, sql, *values)
	result = cursor.fetchone()
	if result is None:
		raise NoRowsException('no rows returned', sql, values)
	if cursor.fetchone() is not None:
		raise MultipleRowsException('multiple results returned', sql, values)
	return result
