#========================================================#
#                                                        #
#  VP-clerk: getrecentblkid.py - 最近のブロックIDを取得  #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from cloudsql import CloudSQL

class handler( BaseHandler ):
	def get( self ):
		coind_type = self.get_request_coind_type()
		n = self.get_request_int('n', 10)

		db = CloudSQL( coind_type )
		with db as c:
			# 最新のものから順に取り出して応答を作成
			r = []
			c.execute( 'SELECT height, hash, miners FROM blockheader ORDER BY height DESC LIMIT %s', {n,} )
			for e in c.fetchall():
				r.append({
					'height': e['height'],
					'hash': e['hash'],
					'miners': e['miners'].split(' '),
				})

		# JSON にシリアライズして返却
		self.write_json( r )
