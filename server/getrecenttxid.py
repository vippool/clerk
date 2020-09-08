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
		db.begin()
		c = db.cursor()
		try:
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
			db.commit()
		except Exception as e:
			db.rollback()
			raise e
		finally:
			c.close()

		# JSON にシリアライズして返却
		return self.write_json( r )
