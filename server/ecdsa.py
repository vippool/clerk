#========================================================#
#                                                        #
#  VP-clerk: ecdsa.py - ECDSA 実装モジュール             #
#                                                        #
#                            (C) 2019-2021 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from binascii import hexlify
from binascii import unhexlify
from os import urandom

# secp256k1 曲線のパラメータ
ec_prm_l = 256
ec_prm_p = int( 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F', 16 )
ec_prm_a = int( '0000000000000000000000000000000000000000000000000000000000000000', 16 )
ec_prm_b = int( '0000000000000000000000000000000000000000000000000000000000000007', 16 )
ec_prm_n = int( 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141', 16 )
ec_point_g_x = int( '79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798', 16 )
ec_point_g_y = int( '483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8', 16 )

# モンゴメリ乗算を行うためのパラメータ
mng_prm_d = int( 'C9BD1905155383999C46C2C295F2B761BCB223FEDC24A059D838091DD2253531', 16 )
mng_prm_s = int( '1000007a2000e90a1', 16 )
mng_prm_m = int( 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF', 16 )

# 曲線の係数体上で非平方数となる値の１例
sqrt_b = int( 3 )


# x の y に対する逆元を求める
def inverse( x, y ):
	r0 = x
	r1 = y
	a0 = 1
	a1 = 0

	# 拡張ユークリッドの互除法
	while r1 > 0:
		q1 = r0 // r1
		r2 = r0 % r1
		a2 = a0 - q1 * a1
		r0 = r1
		r1 = r2
		a0 = a1
		a1 = a2

	if r0 < 0:
		r0 = r0 + y

	return a0


# x の GF(y) 上での平方根を求める
def sqrt( x, y ):
	# 位数 - 1 から 2 冪の値を分離する
	s = 0
	t = y - 1
	while (t & 1) == 0:
		t = t >> 1
		s = s + 1

	# 適当な非平方数の t 乗を求める
	b = pow( sqrt_b, t, y )

	# x の逆元を求める
	xi = inverse( x, y )

	# x の (t+1)/2 乗を求める
	r = pow( x, int((t + 1) // 2), y )

	for i in range( s - 2, -1, -1 ):
		n = int( 1 ) << i
		d = pow( r * r * xi, n, y )
		if d != 1:
			r = r * b % y
		b = b * b % y

	return r


# モンゴメリドメインでの値
class montgomery:
	# モンゴメリ乗算
	@staticmethod
	def mng_mult( a, b ):
		t = a * b
		u = int(t) & mng_prm_m
		u = (u * mng_prm_d) & mng_prm_m
		k = int(t + u * ec_prm_p) >> ec_prm_l
		if k >= ec_prm_p:
			k = k - ec_prm_p
		return k

	# 通常の値からモンゴメリドメインに変換して格納する
	def __init__( self, x, conv = True ):
		if conv:
			self.x = self.mng_mult( x, mng_prm_s )
		elif isinstance( x, montgomery ):
			self.x = x.x
		else:
			self.x = x

	# 元の値に戻して取得する
	def get( self ):
		return self.mng_mult( self.x, 1 )

	# 加算
	def __add__( self, rhs ):
		t = self.x + rhs.x
		if t >= ec_prm_p:
			t = t - ec_prm_p
		return montgomery( t, False )

	# 減算
	def __sub__( self, rhs ):
		t = self.x - rhs.x
		if t < 0:
			t = t + ec_prm_p
		return montgomery( t, False )

	# 乗算
	def __mul__( self, rhs ):
		return montgomery( self.mng_mult( self.x, rhs.x ), False )

	# 逆元を求める
	def inv( self ):
		t = inverse( self.x, ec_prm_p )
		t = self.mng_mult( t, mng_prm_s )
		return montgomery( t )


# 楕円曲線の座標クラス
class ec_point:
	# アフィン座標からヤコビアン座標に変換して格納する
	def __init__( self, x, y, z = 1, conv = True ):
		self.coord_x = montgomery( x, conv )
		self.coord_y = montgomery( y, conv )
		self.coord_z = montgomery( z, conv )
		self.mng_a = montgomery( ec_prm_a )

	# アフィン座標に変換する
	def affine( self ):
		# z 座標の逆元を求める
		z_i = self.coord_z.inv()

		# z 座標の 2 乗 3 乗を求める
		z_i2 = z_i * z_i
		z_i3 = z_i * z_i2

		# モンゴメリドメインでの x, y 座標を求める
		x = self.coord_x * z_i2
		y = self.coord_y * z_i3

		# モンゴメリ表現から元に戻す
		return x.get(), y.get()

	# 2 倍算
	def double( self ):
		# 各座標値の 2 乗を計算
		x_2 = self.coord_x * self.coord_x
		y_2 = self.coord_y * self.coord_y
		z_2 = self.coord_z * self.coord_z

		# y, z は 4 乗も計算
		y_4 = y_2 * y_2
		z_4 = z_2 * z_2

		# x の 4 倍を求める
		x_x4 = self.coord_x + self.coord_x
		x_x4 = x_x4 + x_x4

		# x^2 の 3 倍を求める
		x_2_x3 = x_2 + x_2
		x_2_x3 = x_2 + x_2_x3

		# y^4 の 8 倍を求める
		y_4_x8 = y_4 + y_4
		y_4_x8 = y_4_x8 + y_4_x8
		y_4_x8 = y_4_x8 + y_4_x8

		# 2 倍算のテンポラリ値
		s = x_x4 * y_2
		m = self.mng_a * z_4 + x_2_x3
		m_2 = m * m

		# x, y, z 座標の計算
		x = m_2 - s - s
		y = m * (s - x) - y_4_x8
		z = self.coord_y * self.coord_z
		z = z + z

		return ec_point( x, y, z, False )

	# 加算
	def __add__( self, rhs ):
		# ヤコビアン座標で同一点であれば 2 倍算を行う
		if self.coord_x == rhs.coord_x and self.coord_y == rhs.coord_y and self.coord_z == rhs.coord_z:
			return self.double()

		# 自身が無限遠点なら加算相手が結果そのままになる
		if self.coord_z.x == 0:
			return rhs

		# 相手が無限遠点なら何もしない
		if rhs.coord_z.x == 0:
			return self

		# それぞれの z 座標の 2 乗 3 乗を求める
		z1_2 = self.coord_z * self.coord_z
		z2_2 = rhs.coord_z * rhs.coord_z
		z1_3 = z1_2 * self.coord_z
		z2_3 = z2_2 * rhs.coord_z

		# 楕円曲線上の落とした時の座標の n 倍を求める
		u1 = self.coord_x * z2_2
		u2 = rhs.coord_x * z1_2
		s1 = self.coord_y * z2_3
		s2 = rhs.coord_y * z1_3

		if u1 == u2:
			if s1 == s2:
				# 楕円曲線上の落とした時に同じ点に落ちるならば 2 倍算
				return self.double()
			else:
				# 共役点の和は無限遠点
				return ec_point( 0, 0, 0 )

		# 加算のテンポラリ値
		h = u2 - u1
		r = s2 - s1
		h_2 = h * h
		r_2 = r * r
		h_3 = h * h_2
		u1h2 = u1 * h_2

		# x, y, z 座標の計算
		x = r_2 - (h_3 + u1h2 + u1h2)
		y = (r * (u1h2 - x)) - (s1 * h_3)
		z = self.coord_z * rhs.coord_z * h

		return ec_point( x, y, z, False )

	# 座標のスカラ倍を求める
	def scalar( self, lhs ):
		# 初期値は無限遠点
		r = ec_point( 0, 0, 0 )

		# テンポラリ
		t = self

		# バイナリ法でスカラ倍を求める
		for i in range( 0, ec_prm_l ):
			tt = r + t
			if (lhs & 1) != 0:
				r = tt
			t = t + t
			lhs = lhs >> 1

		return r

	@staticmethod
	def selfTest():
		p = ec_point( ec_point_g_x, ec_point_g_y )

		# 位数をかけると無限遠点に飛ぶ
		r = p.scalar( ec_prm_n )
		x, y = r.affine()
		print('x: %064x' % x)
		print('y: %064x' % y)
		if x == 0 and y == 0:
			print('ok.')
		else:
			print('ng.')

		# 適当な秘密鍵
		r = p.scalar( int( 'D2E85CC6AC3A6701040D7E9B57F1F24CD748A20626F06F2D5844059D024F5256', 16 ) )
		x, y = r.affine()
		print('x: %064x' % x)
		print('y: %064x' % y)
		if x == int( 'D76F60853013746C8D0160CDCF2630309A2170D105FF6C96503F46A1A0BCC4D8', 16 ) and y == int( '0F9D1C3D8AC0C2D8C589A839E226D60FFD513B3941AC92DC20EDF6EF337BC4E0', 16 ):
			print('ok.')
		else:
			print('ng.')


# ECDSA 公開鍵の作成
def pubKey( privKey ):
	g = ec_point( ec_point_g_x, ec_point_g_y )
	kg = g.scalar( privKey )
	return kg.affine()


# ECDSA 署名の作成
def sign( hash, privKey ):
	g = ec_point( ec_point_g_x, ec_point_g_y )

	while True:
		# [ 1, n-1 ] の範囲で乱数を生成する
		k = int( hexlify( urandom( 32 ) ), 16 )
		k = (k + 1) % ec_prm_n

		# k * G を計算する
		kg = g.scalar( k )
		x, y = kg.affine()

		# r を求める
		r = x % ec_prm_n
		if r == 0:
			continue

		# s を求める
		ki = inverse( k, ec_prm_n )
		s = (ki * (hash + r * privKey)) % ec_prm_n
		if s == 0:
			continue

		return r, s


# ECDSA 署名の検証
def verify( hash, signature_r, signature_s, pubKeyX, pubKeyY ):
	# ヤコビアン座標を使っている都合上、無限遠点は ( 0, 0 ) になる
	if pubKeyX == 0 and pubKeyY == 0:
		return False

	# 公開鍵が楕円曲線上の点であることを確認する
	lhs = (pubKeyY * pubKeyY) % ec_prm_p
	rhs = (pubKeyX * pubKeyX * pubKeyX + ec_prm_a * pubKeyX + ec_prm_b) % ec_prm_p
	if lhs != rhs:
		return False

	# 位数を確認する
	q = ec_point( pubKeyX, pubKeyY )
	nq = q.scalar( ec_prm_n )
	if nq.coord_z.x != 0:
		return False

	# r と s の値域を確認する
	if signature_r < 1 or ec_prm_n <= signature_r:
		return False
	if signature_s < 1 or ec_prm_n <= signature_s:
		return False

	w = inverse( signature_s, ec_prm_n )
	u1 = (hash * w) % ec_prm_n
	u2 = (signature_r * w) % ec_prm_n

	g = ec_point( ec_point_g_x, ec_point_g_y )
	r = g.scalar( u1 ) + q.scalar( u2 )
	x, y = r.affine()

	return (x % ec_prm_n) == signature_r


# バイナリ配列の公開鍵から X, Y 座標を計算する
def decompress( pubKey ):
	# エラーの場合は None を返す
	x = None
	y = None

	# uncompressed 形式の場合は X, Y 座標が連続している
	if pubKey[0] == 0x04 and len( pubKey ) == 65:
		x = int( hexlify( pubKey[1:33] ), 16 )
		y = int( hexlify( pubKey[33:65] ), 16 )

	# compressed 形式の場合は X 座標を取り出してから計算する
	if (pubKey[0] == 0x02 or pubKey[0] == 0x03) and len( pubKey ) == 33:
		x = int( hexlify( pubKey[1:33] ), 16 )
		y_2 = x * x * x + ec_prm_a * x + ec_prm_b
		y = sqrt( y_2, ec_prm_p )

		if (pubKey[0] & 1) != (y & 1):
			y = ec_prm_p - y

	return x, y


# 単独で実行した場合はセルフテスト
if __name__ == '__main__':
	ec_point.selfTest()

	for i in range( 0, 10 ):
		h = int( hexlify( urandom( 32 ) ), 16 )
		k = int( hexlify( urandom( 32 ) ), 16 )
		pkx, pky = pubKey( k )

		# uncompressed 形式
		s = bytearray( unhexlify( '04%064X%064X' % (pkx, pky) ) )
		if decompress( s ) != (pkx, pky):
			print(pkx, pky)

		# compressed 形式
		s = bytearray( unhexlify( '%02X%064X' % (2 + (pky & 1), pkx) ) )
		if decompress( s ) != (pkx, pky):
			print(pkx, pky)

		# 署名作成と検証
		r, s = sign( h, k )
		print(verify( h, r, s, pkx, pky ))
