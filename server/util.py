#========================================================#
#                                                        #
#  VP-clerk: util.py - 各種ユーティリティ                #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import ValidationError

from binascii import hexlify
from binascii import unhexlify
from struct import pack
from hashlib import sha256
from Crypto.Hash import RIPEMD

SATOSHI_COIN = 100000000.0      # コインの最小単位
ADDRESS_LENGTH = 34

# アドレスのプレフィックスを返す
def address_prefix( coind_type ):
	if coind_type == 'bitcoind':
		return b'\x00'
	if coind_type == 'bitcoind_test':
		return b'\x6f'
	if coind_type == 'monacoind':
		return b'\x32'
	if coind_type == 'monacoind_test':
		return b'\x6f'
	raise Exception( 'unknown coind_type: %s' % coind_type )

# BASE58 エンコード
def b58encode( src ):
	mapping = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

	r = ''
	n = int( hexlify( src ), 16 )
	for i in range( 0, ADDRESS_LENGTH ):
		r = mapping[n % 58] + r
		n = int(n / 58)

	return r

# BASE58 デコード
def b58decode( src, elem ):
	mapping = [
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1, 0, 1, 2, 3, 4, 5, 6, 7, 8,-1,-1,-1,-1,-1,-1,
		-1, 9,10,11,12,13,14,15,16,-1,17,18,19,20,21,-1,
		22,23,24,25,26,27,28,29,30,31,32,-1,-1,-1,-1,-1,
		-1,33,34,35,36,37,38,39,40,41,42,43,-1,44,45,46,
		47,48,49,50,51,52,53,54,55,56,57,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
	]

	if len( src ) != ADDRESS_LENGTH:
		raise ValidationError( elem, 'len' )

	n = int()
	for i in range( 0, ADDRESS_LENGTH ):
		x = ord( src[i] )
		if x < 0 or x > 255:
			raise ValidationError( elem, 'b58decode' )
		x = mapping[ x ]
		if x == -1:
			raise ValidationError( elem, 'b58decode' )
		n = n * 58 + x

	return unhexlify( '%050x' % n )

# 公開鍵からコインアドレスを生成する
def encode_coin_address( pub_key, coind_type ):
	# ハッシュ値を計算する
	ripemd160 = RIPEMD.new()
	ripemd160.update( sha256( pub_key ).digest() )
	binary = address_prefix( coind_type ) + ripemd160.digest()

	# チェックサムを計算する
	cksum = sha256( sha256( binary ).digest() ).digest()

	# 最後に Base58 エンコードして完成
	return b58encode( binary + cksum[0:4] )

# コインアドレスをバリデーションしてからハッシュ値に変換する
def decode_coin_address( addr, coind_type, elem ):
	# まずはバイナリ配列に変換する
	binary = b58decode( addr, elem )

	# 正しければ 25 Byte になるはず
	if len( binary ) != 25:
		raise ValidationError( elem, 'len' )

	# アドレスのプレフィックスを確認
	if binary[0:1] != address_prefix( coind_type ):
		raise ValidationError( elem, 'address_prefix' )

	# チェックサムを確認する
	cksum = sha256( sha256( binary[0:21] ).digest() ).digest()
	if binary[21:25] != cksum[0:4]:
		raise ValidationError( elem, 'cksum' )

	# 先頭を除く 160bit がアドレスのハッシュ値
	return binary[1:21]

# 公開鍵をバリデーションしてからバイナリ配列に変換する
def parse_pub_key( pub_key, elem ):
	# まず 16 進数としてパースできる必要がある
	try:
		b = bytearray( unhexlify( pub_key ) )
	except TypeError as e:
		raise ValidationError( elem, e.msg )

	# プレフィックスがないものは論外
	if len( b ) < 1:
		raise ValidationError( elem, 'len' )

	# compressed 形式なら長さを確認して返す
	if b[0] == 0x02 or b[0] == 0x03:
		if len( b ) != 33:
			raise ValidationError( elem, 'len' )

		return b

	# uncompressed 形式なら長さを確認して compressed 形式に変換する
	if b[0] == 0x04:
		if len( b ) != 65:
			raise ValidationError( elem, 'len' )

		if b[64] % 2 == 1:
			b[0] = 0x03
		else:
			b[0] = 0x02

		return b[0:33]

	raise ValidationError( elem, 'prefix' )

# var_int 形式のバイト配列に変換する
def var_int( n ):
	if n < 0xFD:
		return bytearray( chr( n ) )
	if n <= 0xFFFF:
		return bytearray( '\xFD' + pack( '<H', n ) )
	if n <= 0xFFFFFFFF:
		return bytearray( '\xFE' + pack( '<I', n ) )
	return bytearray( '\xFF' + pack( '<Q', n ) )

# CVE-2018-17144 によって UTXO の重複使用が可能になる
def CVE_2018_17144( coind_type, txid ):
	target = [
	]
	for e in target:
		if coind_type == e[0] and txid == e[1]:
			return True
	return False
