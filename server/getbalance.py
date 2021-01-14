#========================================================#
#                                                        #
#  VP-clerk: getbalance.py - 指定アドレスの残高照会      #
#                                                        #
#                            (C) 2019-2021 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from webob import exc
from base_handler import BaseHandler
from base_handler import ValidationError
from cloudsql import CloudSQL
from util import SATOSHI_COIN
import json
import time

class handler( BaseHandler ):
	def get( self, request ):
		coind_type = self.get_request_coind_type(request)
		addresses = request.args.get('addresses')
		offset = self.get_request_int(request, 'offset', 0)
		limit = self.get_request_int(request, 'limit', None)

		# アドレス json を解析する
		try:
			addresses = ' '.join( json.loads( addresses ) )
		except ValueError as e:
			raise ValidationError( 'addresses', e.msg )

		db = CloudSQL( coind_type )
		with db.cursor() as c:
			# 現在の残高を取得する
			c.execute( 'SELECT balance, serial FROM balance WHERE addresses = %s ORDER BY serial DESC LIMIT 1', (addresses,) )
			r = c.fetchone()

			if r is None:
				raise exc.HTTPNotFound()

			balance = r['balance'] / SATOSHI_COIN
			max_serial = r['serial']

			# 取得範囲を限定する
			if limit is not None:
				under_serial = max_serial - offset - limit + 1
			else:
				under_serial = 0
			over_serial = max_serial - offset + 1

			# 履歴順に辞書を配列で格納する
			history = []
			c.execute( 'SELECT height, txid, time, gain, balance FROM balance WHERE addresses = %s AND serial >= %s AND serial < %s ORDER BY serial', (addresses, under_serial, over_serial) )
			for e in c.fetchall():
				history.append({
					'height': e['height'],
					'txid': e['txid'],
					'time': int( time.mktime( e['time'].timetuple() ) ),
					'gain': e['gain'] / SATOSHI_COIN,
					'balance': e['balance'] / SATOSHI_COIN
				})

		return self.write_json( { 'balance': balance, 'history': history } )
