#========================================================#
#                                                        #
#  VP-clerk: cloudsql.py - Cloud SQL 接続クラス          #
#                                                        #
#                            (C) 2019-2021 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import os
import config
import MySQLdb
import MySQLdb.cursors

def CloudSQL( coind_type ):
	if os.getenv('GAE_ENV', '').startswith('standard'):
		return MySQLdb.connect(
			unix_socket = os.path.join( '/cloudsql', config.cloudsql_name ),
			user = config.cloudsql_user,
			passwd = config.cloudsql_pass,
			db = coind_type,
			cursorclass = MySQLdb.cursors.DictCursor,
			autocommit = False
		)
	else:
		return MySQLdb.connect(
			host = '127.0.0.1',
			user = config.cloudsql_user,
			passwd = config.cloudsql_pass,
			db = coind_type,
			cursorclass = MySQLdb.cursors.DictCursor,
			autocommit = False
		)
