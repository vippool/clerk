#========================================================#
#                                                        #
#  VP-clerk: cloudsql.py - Cloud SQL 接続クラス          #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import os
import config
import MySQLdb
import MySQLdb.cursors

def CloudSQL( coind_type ):
	if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
		connection = MySQLdb.connect(
			unix_socket = os.path.join( '/cloudsql', config.cloudsql_name ),
			user = config.cloudsql_user,
			passwd = config.cloudsql_pass,
			db = coind_type,
			cursorclass = MySQLdb.cursors.DictCursor,
			autocommit = False
		)
		return connection.cursor()
	else:
		connection = MySQLdb.connect(
			host = '127.0.0.1',
			user = config.cloudsql_user,
			passwd = config.cloudsql_pass,
			db = coind_type,
			cursorclass = MySQLdb.cursors.DictCursor,
			autocommit = False
		)
		return connection.cursor()
