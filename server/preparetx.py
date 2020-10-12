#========================================================#
#                                                        #
#  VP-clerk: preparetx.py - 送金準備                     #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from base_handler import ValidationError
from cloudsql import CloudSQL
from util import encode_coin_address
from util import decode_coin_address
from util import parse_pub_key
from util import var_int
from util import SATOSHI_COIN
from struct import pack
from binascii import hexlify
from binascii import unhexlify
from hashlib import sha256
from base64 import b64encode
import base64
import json
import bz2

class handler( BaseHandler ):
	@staticmethod
	def make_script( hash, pk, req_sigs ):
		r = b''

		if len( hash ) == 1:
			# P2PKH
			r = r + b'\x76' # OP_DUP
			r = r + b'\xa9' # OP_HASH160
			r = r + bytes( [len(hash[0])] ) # PUSHx
			r = r + hash[0]

			r = r + b'\x88' # OP_EQUALVERIFY
			r = r + b'\xac' # OP_CHECKSIG
		else:
			# MULTISIG
			r = r + bytes( [0x50 + req_sigs] ) # OP_x
			for e in pk:
				r = r + bytes( [len( e )] ) # PUSHx
				r = r + e
			r = r + bytes( [0x50 + len( pk )] ) # OP_x
			r = r + b'\xae' # OP_CHECKMULTISIG

		return r

	@staticmethod
	def make_data_script( data ):
		r = b''

		r = r + b'\x6a' # OP_RETURN

		r = r + bytes( [len( data )] ) # PUSHx
		r = r + data

		return r

	@staticmethod
	def make_vout( script, value ):
		return pack( '<Q', int(value) ) + var_int( len( script ) ) + script

	def get( self, request ):
		coind_type = self.get_request_coind_type(request)

		# パラメータを取得する
		try:
			params = json.loads( request.args.get( 'params' ) )
		except ValueError as e:
			raise ValidationError( 'params', e.msg )

		# パラメータを分解する
		params_from = params['from']
		params_to = params['to']
		req_sigs = params['req_sigs']
		value = params['value']
		fee = params['fee']
		data = params.get( 'data', None )


		# from を検査してからハッシュ値に変換する
		from_hash = []
		from_addr = []
		from_pk = []
		if not isinstance( params_from, list ):
			raise ValidationError( 'from', 'list' )
		for e in params_from:
			try:
				# コインアドレスとしてパースを試みる
				from_hash.append( decode_coin_address( e, coind_type, 'from' ) )
				from_addr.append( e )
				from_pk.append( None )
			except ValidationError:
				# ダメだったら公開鍵としてパースを試みる
				pk = parse_pub_key( e, 'from' )
				addr = encode_coin_address( pk, coind_type )
				from_hash.append( decode_coin_address( addr, coind_type, 'from' ) )
				from_addr.append( addr )
				from_pk.append( pk )

		# MULTISIG の場合は公開鍵がなければならない
		if len( params_from ) != 1:
			for e in from_pk:
				if e is None:
					raise ValidationError( 'from', 'pub_key' )

		# to を検査してからハッシュ値に変換する
		to_hash = []
		to_addr = []
		to_pk = []
		if not isinstance( params_to, list ):
			raise ValidationError( 'to', 'list' )
		for e in params_to:
			try:
				# コインアドレスとしてパースを試みる
				to_hash.append( decode_coin_address( e, coind_type, 'to' ) )
				to_addr.append( e )
				to_pk.append( None )
			except ValidationError:
				# ダメだったら公開鍵としてパースを試みる
				pk = parse_pub_key( e, 'to' )
				addr = encode_coin_address( pk, coind_type )
				to_hash.append( decode_coin_address( addr, coind_type, 'to' ) )
				to_addr.append( addr )
				to_pk.append( pk )

		# MULTISIG の場合は公開鍵がなければならない
		if len( params_to ) != 1:
			for e in to_pk:
				if e is None:
					raise ValidationError( 'to', 'pub_key' )

		# req_sigs の検査
		if not isinstance( req_sigs, int ):
			raise ValidationError( 'req_sigs', 'int' )
		if req_sigs > len( params_to ):
			raise ValidationError( 'req_sigs', 'len' )

		# 送金額の確認
		if value < 0.0:
			raise ValidationError( 'value', '0' )

		# トランザクション手数料の確認
		if fee <= 0.0:
			raise ValidationError( 'fee', '0' )

		# OP_RETURN データの検査
		if data is not None:
			try:
				# 16進数文字列で...
				data = unhexlify( data )

				# ...75 Byte 以下
				if len( data ) > 75:
					raise ValidationError( 'data', 'len' )
			except TypeError as e:
				raise ValidationError( 'data', e.msg )


		# 入力トランザクションの検索
		input_value = 0
		vin_txid = []
		vin_idx = []
		vin_type = ''
		vin_reqSigs = []
		db = CloudSQL( coind_type )
		with db.cursor() as c:
			c.execute( 'SELECT * FROM transaction_link WHERE addresses = %s AND ISNULL(vin_txid)', (' '.join( from_addr ),) )
			for e in c.fetchall():
				# トランザクションの生データ取得
				c.execute( 'SELECT json FROM transaction WHERE txid = %s AND height = %s', (e['vout_txid'], e['vout_height']) )
				raw = json.loads( bz2.decompress( base64.b64decode( c.fetchone()['json'] ) ) )

				# P2PKH か MULTISIG でなければスキップ
				type = raw['vout'][e['vout_idx']]['scriptPubKey']['type']
				if len( from_addr ) == 1:
					if type != 'pubkeyhash':
						continue
				else:
					if type != 'multisig':
						continue

				input_value += e['value']
				vin_txid.append( e['vout_txid'] )
				vin_idx.append( e['vout_idx'] )
				vin_type = type
				vin_reqSigs.append( raw['vout'][e['vout_idx']]['scriptPubKey']['reqSigs'] )

				if input_value >= (value + fee) * SATOSHI_COIN:
					break

		# 残高が足りるか確認
		if input_value < (value + fee) * SATOSHI_COIN:
			raise Exception( "You don't have enough money." )


		vout_n = 0
		vout_lt = b''

		# vout[0] (送金出力) の作成
		vout_lt = vout_lt + self.make_vout( self.make_script( to_hash, to_pk, req_sigs ), value * SATOSHI_COIN )
		vout_n += 1

		# vout[1] (おつり出力) の作成
		rem = int( input_value - (value + fee) * SATOSHI_COIN )
		if rem != 0:
			vout_lt = vout_lt + self.make_vout( self.make_script( from_hash, from_pk, max( vin_reqSigs ) ), rem )
			vout_n += 1

		# vout[2] (OP_RETURN の作成)
		if data is not None:
			vout_lt = vout_lt + self.make_vout( self.make_data_script( data ), 0 )
			vout_n += 1

		# vout～locktime 区間のバイナリ組み立て
		vout_lt = var_int( vout_n ) + vout_lt + pack( '<I', 0 )


		# 入力トランザクションごとに署名対象のハッシュ値を求める
		sign_hash = []
		for i in range( 0, len( vin_txid ) ):
			# 入力トランザクションの出力スクリプト
			# - 送金元アドレスから P2PKH を仮定して生成する
			script = self.make_script( from_hash, from_pk, vin_reqSigs[i] );

			# 先頭は vin の個数
			vin = var_int( len( vin_txid ) )

			# 全入力トランザクションを結合
			for j in range( 0, len( vin_txid ) ):
				# 入力トランザクションを追加
				vin = vin + unhexlify( vin_txid[j] )[::-1] + pack( '<I', vin_idx[j] )

				# 該当する入力のときだけスクリプトを挿入
				if i == j:
					vin = vin + var_int( len( script ) ) + script
				else:
					vin = vin + var_int( 0 )

				# シーケンスは 0 固定
				vin = vin + pack( '<I', 0 )

			# txCopy を完成させる
			tx = pack( '<i', 2 ) + vin + vout_lt + pack( '<I', 1 )

			# SHA256 ハッシュを計算して署名対象のハッシュ値とする
			sign_hash.append({
				'txid': vin_txid[i],
				'hash': sha256( sha256( tx ).digest() ).hexdigest(),
				'reqSigs': vin_reqSigs[i]
			})

		b64_pk = []
		for e in from_pk:
			if e is not None:
				b64_pk.append( b64encode( e ) )
			else:
				b64_pk.append( None )

		# 後半ステージに送る情報をペイロードにまとめる
		payload_body = json.dumps( {
			'hash': sign_hash,
			'from_pk': b64_pk,
			'vin_txid': vin_txid,
			'vin_idx': vin_idx,
			'vin_type': vin_type,
			'vin_reqSigs': vin_reqSigs,
			'vout_lt': hexlify( vout_lt ).decode('ascii'),
			'log_data': {
				'params_from': params_from,
				'params_to': params_to,
				'sign_hash': sign_hash
			}
		} )

		# さらにハッシュをつけて包む
		payload = {
			'body': payload_body,
			'hash': sha256( payload_body.encode('utf-8') ).hexdigest()
		}

		return self.write_json( {
			'sign': sign_hash,
			'payload': b64encode( bz2.compress( json.dumps( payload ).encode('utf-8') ) ).decode('ascii')
		} )
