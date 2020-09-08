#========================================================#
#                                                        #
#  VP-clerk: getblock.py - ブロック情報取得              #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from base_handler import ValidationError
from cloudsql import CloudSQL
from webob import exc
import json
import base64
import bz2

class handler( BaseHandler ):
	def get( self, request ):
		coind_type = self.get_request_coind_type(request)
		height = self.get_request_int(request, 'height', None)
		hash = request.args.get('hash', None)

		db = CloudSQL( coind_type )
		db.begin()
		c = db.cursor()
		try:
			# ブロックの取得
			if height is not None:
				c.execute( 'SELECT * FROM blockheader WHERE height = %s', (height,) )
			elif hash is not None:
				c.execute( 'SELECT * FROM blockheader WHERE hash = %s', (hash,) )
			else:
				raise ValidationError( 'condition', 'there is no height and hash' )

			blockheader = c.fetchone()

			if blockheader is None:
				# 存在しない場合
				raise exc.HTTPNotFound()

			# 現在のブロック高を取得する
			c.execute( 'SELECT MAX(height) FROM blockheader' )
			chain_height = c.fetchone()['MAX(height)']

			# 後続ブロックのハッシュ値を取得する
			c.execute( 'SELECT hash FROM blockheader WHERE height = %s', (blockheader['height']+1,) )
			nextblockhash = c.fetchone()
			if nextblockhash is not None:
				nextblockhash = nextblockhash['hash']

			# 直前ブロックのハッシュ値を取得する
			c.execute( 'SELECT hash FROM blockheader WHERE height = %s', (blockheader['height']-1,) )
			previousblockhash = c.fetchone()
			if previousblockhash is not None:
				previousblockhash = previousblockhash['hash']
			db.commit()
		except Exception as e:
			db.rollback()
			raise e
		finally:
			c.close()

		# コインノードからの生データをパース
		json_data = json.loads( bz2.decompress( base64.b64decode( blockheader['json'] ) ) )
		# 確認数を更新する
		json_data['confirmations'] = chain_height - blockheader['height'] + 1

		# 同期時に握りつぶした情報を補完する
		json_data['nextblockhash'] = nextblockhash
		json_data['previousblockhash'] = previousblockhash

		# JSON 形式でシリアライズして返す
		return self.write_json( json_data )
