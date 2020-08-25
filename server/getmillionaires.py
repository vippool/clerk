#========================================================#
#                                                        #
#  VP-clerk: getmillionaires.py - 長者番付               #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from cloudsql import CloudSQL
from util import SATOSHI_COIN

class handler( BaseHandler ):
	def get( self, request ):
		coind_type = self.get_request_coind_type(request)
		offset = self.get_request_int(request, 'offset', 0)
		limit = self.get_request_int(request, 'limit', 10)

		db = CloudSQL( coind_type )
		with db as c:
			# 現在の残高をソートして取得する
			r = []
			c.execute( 'SELECT * FROM current_balance ORDER BY balance DESC LIMIT %s OFFSET %s', (limit, offset) )
			for e in c.fetchall():
				r.append({
					'addresses': e['addresses'].split(' '),
					'balance': e['balance'] / SATOSHI_COIN
				})

		self.write_json( r )
