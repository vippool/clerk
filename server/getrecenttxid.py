#========================================================#
#                                                        #
#  VP-clerk: getrecenttxid.py - 最近の TXID を取得       #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from util import SATOSHI_COIN
from base_handler import BaseHandler
from cloudsql import CloudSQL
import time

class handler( BaseHandler ):
	def get( self, request ):
		coind_type = self.get_request_coind_type(request)
		n = self.get_request_int( request, 'n', 10 )

		db = CloudSQL( coind_type )
		with db as c:
			c.execute( 'SELECT txid, time, height, total_output FROM transaction ORDER BY time DESC LIMIT %s', (n,) )

			r = []
			for e in c.fetchall():
				# 応答の要素を作成して追加
				r.append({
					'height': e['height'],
					'txid': e['txid'],
					'time': int( time.mktime( e['time'].timetuple() ) ),
					'value': e['total_output'] / SATOSHI_COIN
				})

		# JSON にシリアライズして返却
		self.write_json( r )
