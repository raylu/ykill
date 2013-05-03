import oursql

from config import db as dbconfig

conn = oursql.connect(host=dbconfig.host, db=dbconfig.database, user=dbconfig.user, passwd=dbconfig.password, autoreconnect=True)

def ykill_cursor():
	return conn.cursor(oursql.DictCursor)

def execute(cursor, sql, *values):
	cursor.execute(sql, values)

def query(cursor, sql, *values):
	execute(cursor, sql, *values)
	return cursor.fetchall()
