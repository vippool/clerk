#========================================================#
#                                                        #
#  VP-clerk: submittx.py - 送金トランザクション作成      #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from google.appengine.api import taskqueue
from base_handler import BaseHandler
from base_handler import ValidationError
from util import parse_pub_key
from util import var_int
from struct import pack
from binascii import hexlify
from binascii import unhexlify
from hashlib import sha256
from base64 import b64encode
from base64 import b64decode
import ecdsa
import json
import bz2

class handler( BaseHandler ):
	@staticmethod
	def der_encode( sign ):
		r = unhexlify( sign[0:64] )
		s = unhexlify( sign[64:128] )

		# DER 形式に符号無しはないので、R の最上位ビットがたっていたら 0x00 を頭につける
		if ord( r[0] ) & 0x80:
			r = bytearray( '\x00' ) + r

		# S が楕円曲線群の位数 N の半分より大きければ、N-S を S' として使用する
		# - 必ず最上位ビットが落ちるので 1 バイト節約できるらしい
		# - S'=N-S としても、署名検証時に楕円曲線上の点が上下反転するだけで X 座標は変化しないため正常に検証を pass する
		sn = int( sign[64:128], 16 )
		lim = int( "7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0", 16 )
		if sn >= lim:
			sn = int( "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16 ) - sn
			s = unhexlify( '%064X' % sn )

		# 0 で始まるバイトは省略する
		while r[0] == '\x00':
			r = r[1:]
		while s[0] == '\x00':
			s = s[1:]

		r = bytearray( '\x02' + chr( len( r ) ) ) + r
		s = bytearray( '\x02' + chr( len( s ) ) ) + s

		der = r + s
		der = bytearray( '\x30' ) + chr( len( der ) ) + der

		return der

	@classmethod
	def make_script( cls, sign, pub_key, vin_type ):
		r = bytearray()

		if vin_type == 'pubkeyhash':
			s = cls.der_encode( sign[0] ) + bytearray( '\x01' )
			r = r + bytearray( chr( len( s ) ) ) # PUSHx
			r = r + s

			r = r + bytearray( chr( len( pub_key ) ) ) # PUSHx
			r = r + pub_key
		else:
			r = r + bytearray( '\x00' ) # OP_0

			for e in sign:
				s = cls.der_encode( e ) + bytearray( '\x01' )
				r = r + bytearray( chr( len( s ) ) ) # PUSHx
				r = r + s

		return r

	def post( self, request ):
		coind_type = self.get_request_coind_type(request)

		# パラメータを取得する
		try:
			params = request.json["params"]
		except ValueError as e:
			raise ValidationError( 'params', e.message )

		sign = params['sign']
		pub_key = params.get( 'pub_key', u'' )
		payload = params['payload']

		# payload をパースする
		try:
			payload = json.loads( bz2.decompress( b64decode( payload ) ) )
		except ValueError as e:
			raise ValidationError( 'params', e.message )
		except Exception as e:
			raise ValidationError( 'params', 'decompress' )

		# payload のハッシュ値検査
		if sha256( payload['body'] ).hexdigest() != payload['hash']:
			raise ValidationError( 'params', 'sha256' )

		# payload の本体をパースする
		try:
			payload = json.loads( payload['body'] )
		except ValueError as e:
			raise ValidationError( 'params', e.message )

		# payload を分解
		vin_txid = payload['vin_txid']
		vin_idx = payload['vin_idx']
		vin_type = payload['vin_type']
		vin_reqSigs = payload['vin_reqSigs']
		vout_lt = unhexlify( payload['vout_lt'] )
		hash = payload['hash']
		from_pk = payload['from_pk']
		log_data = payload['log_data']


		# sign の検証
		if not isinstance( sign, list ):
			raise ValidationError( 'sign', 'list' )
		if len( sign ) != len( hash ):
			raise ValidationError( 'sign', 'n' )
		for i in range( 0, len( hash ) ):
			if not isinstance( sign[i], list ):
				raise ValidationError( 'sign', 'list' )
			if len( sign[i] ) != vin_reqSigs[i]:
				raise ValidationError( 'sign', 'reqSigs' )

			for e in sign[i]:
				if len( e ) != 128:
					raise ValidationError( 'sign', 'len' )

				# 形式検査 : 16進としてパースできれば OK
				try:
					unhexlify( e )
				except TypeError as e:
					raise ValidationError( 'sign', e.message )


		# pub_key の検証
		if not isinstance( pub_key, str ):
			raise ValidationError( 'pub_key', 'unicode' )
		if vin_type == 'pubkeyhash':
			# 形式検査とパース
			pub_key = parse_pub_key( pub_key, 'pub_key' )


		# 電子署名の検証
		if vin_type == 'pubkeyhash':
			for i in range( 0, len( hash ) ):
				# 署名対象ハッシュ値を数値に
				h = int( hash[i]['hash'], 16 )

				# 署名をパース
				sig_r = int( sign[i][0][0:64], 16 )
				sig_s = int( sign[i][0][64:128], 16 )

				# 公開鍵をパース
				pk_x, pk_y = ecdsa.decompress( pub_key )

				if not ecdsa.verify( h, sig_r, sig_s, pk_x, pk_y ):
					raise ValidationError( 'sign', 'verify' )
		elif vin_type == 'multisig':
			for i in range( 0, len( hash ) ):
				# 署名対象ハッシュ値を数値に
				h = int( hash[i]['hash'], 16 )

				# 何番目の公開鍵まで走査したか
				k = 0

				for e in sign[i]:
					# 署名をパース
					sig_r = int( e[0:64], 16 )
					sig_s = int( e[64:128], 16 )

					while True:
						# 有効な公開鍵があるか
						if k == len( from_pk ):
							raise ValidationError( 'sign', 'verify' )

						# preparetx に送った公開鍵をパース
						pk_x, pk_y = ecdsa.decompress( bytearray( b64decode( from_pk[k] ) ) )
						k = k + 1

						# 署名検証に成功したら次へ進む
						if ecdsa.verify( h, sig_r, sig_s, pk_x, pk_y ):
							break


		# トランザクションデータの先頭はバージョン番号から始まる
		tx = bytearray( pack( '<i', 2 ) )

		# vin の組み立て
		tx = tx + bytearray( var_int( len( vin_txid ) ) )
		for i in range( 0, len( vin_txid ) ):
			# アンロックスクリプト (入力スクリプト) の作成
			script = self.make_script( sign[i], pub_key, vin_type )

			# 入力トランザクションを追加
			tx = tx + bytearray( unhexlify( vin_txid[i] )[::-1] + pack( '<I', vin_idx[i] ) )
			tx = tx + var_int( len( script ) ) + script + bytearray( pack( '<I', 0 ) )

		# vout～locktime 区間を連結
		tx = tx + vout_lt


		# ログデータに追記
		log_data['sign'] = sign
		log_data['tx'] = hexlify( tx )


		# キューに投げるデータを payload としてまとめる
		payload_body = json.dumps( {
			'tx': hexlify( tx ),
			'log_data': log_data
		} )

		# さらにハッシュをつけて包む
		payload = {
			'body': payload_body,
			'hash': sha256( payload_body ).hexdigest()
		}

		# taskqueue に積む
		taskqueue.add(
			url = '/maintain/sendrawtransaction',
			params = {
				'coind_type': coind_type,
				'payload': b64encode( bz2.compress( json.dumps( payload ) ) )
			},
			queue_name = 'send-tx'
		)

		# 作成した TXID を返す
		self.write_json( {
			'result': hexlify( sha256( sha256( tx ).digest() ).digest()[::-1] )
		} )
