﻿#========================================================#
#                                                        #
#  VP-clerk: update_db.py - DB 更新コマンド              #
#                                                        #
#                            (C) 2019-2021 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from coind import coind_factory
from cloudsql import CloudSQL
from base_handler import BaseHandler
from datetime import datetime
from urllib.parse import urlencode
from util import SATOSHI_COIN
from util import CVE_2018_17144
import base64
import logging
import bz2
import json
import copy
import time
import MySQLdb
import config
from cloudtasks import CloudTasksClient

TIMEOUT = 480.0               # sync のタイムアウト時間 (秒)
LOCK_TIMEOUT = 900            # ロックのタイムアウト時間 (秒)

def ignore_txid( coind_type, txid ):
	# 第 0 ブロックのトランザクションは取得できない
	if coind_type == 'monacoind' and txid == '35e405a8a46f4dbc1941727aaf338939323c3b955232d0317f8731fe07ac4ba6':
		return True
	elif coind_type == 'monacoind_test' and txid == '35e405a8a46f4dbc1941727aaf338939323c3b955232d0317f8731fe07ac4ba6':
		return True
	elif coind_type == 'bitcoind' and txid == '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b':
		return True
	elif coind_type == 'bitcoind_test' and txid == '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b':
		return True
	else:
		return False

# コインノードからデータを取得して同期を行う
def sync( db, coind_type, max_leng ):
	# コインノードクライアントの初期化
	cd = coind_factory( coind_type )

	# コインノードが保持しているブロックの高さ
	cd_height = cd.run( 'getblockcount', [] )

	# 開始時の DB 内ブロック高
	with db.cursor() as c:
		c.execute( 'SELECT IFNULL(MAX(height)+1,0) FROM blockheader' )
		start_block_height = c.fetchone()['IFNULL(MAX(height)+1,0)']

	# 開始時刻を記録
	start_time = time.time()

	# 制限時間まで同期を繰り返す
	for i in range( max_leng ):
		# 経過時間を確認
		if time.time() - start_time > TIMEOUT:
			return

		# 今回更新するブロック
		block_height = start_block_height + i

		# 更新不要な場合は終了
		if block_height > cd_height:
			return

		# 以降の同期作業はトランザクション内で行う
		db.begin()
		c = db.cursor()
		try:
			# 新規追加するブロックのデータを取得

			# ブロックハッシュを取得
			blockhash = cd.run( 'getblockhash', [ int(block_height) ] )

			# ブロックデータを取得
			cd_block = cd.run( 'getblock', [ blockhash ] )

			# 縮小版の json データ作成
			# - 信用できないデータは出力時に補完する
			block_json_reduce = copy.deepcopy( cd_block )
			block_json_reduce.pop( 'nextblockhash', None )
			block_json_reduce.pop( 'previousblockhash', None )
			block_json_reduce.pop( 'confirmations' )

			# マイナーは一旦空にしておく
			miners = None

			# 所属するトランザクションのデータを順次追加
			for txid in cd_block['tx']:
				if ignore_txid( coind_type, txid ):
					continue

				# トランザクションデータを取得する
				if coind_type == 'bitcoind':
					# bitcoind の場合、重複 TXID があるので、第三引数にブロックハッシュを渡す
					cd_transaction = cd.run( 'getrawtransaction', [ txid, 1, blockhash ] )
				else:
					# それ以外の場合、monacoind は第三引数を与えるとエラーになる
					cd_transaction = cd.run( 'getrawtransaction', [ txid, 1 ] )

				# 縮小版の json データ作成
				# - 信用できないデータは出力時に補完する。大きいデータは捨てる。
				# - scriptPubKey の HEX は storage で使いたいので残すことにした @ 2020/12/11-
				tx_json_reduce = copy.deepcopy( cd_transaction )
				tx_json_reduce.pop( 'hex' )
				tx_json_reduce.pop( 'confirmations' )
				for e in tx_json_reduce['vin']:
					if 'scriptSig' in e:
						e['scriptSig'].pop( 'hex' )
				#for e in tx_json_reduce['vout']:
				#	e['scriptPubKey'].pop( 'hex' )

				# BIP-30 違反検査は通常は対象とする
				bip30_exception = False

				# BIP-34 適用以前には 2 つだけ BIP-30 に違反するトランザクションが存在する
				if coind_type == 'bitcoind':
					if block_height == 91842 and blockhash == '00000000000a4d0a398161ffc163c503763b1f4360639393e0e4c8e300e0caec':
						bip30_exception = True
					elif block_height == 91880 and blockhash == '00000000000743f190a18c5577a3c2d2a1f610ae9601ac046a38084ccb7cd721':
						bip30_exception = True

				# BIP-30 違反検査は一旦強制的に無効化する
				bip30_exception = True
				# BIP-30 を厳密に守ろうとすると、バースデイパラドックスや鳩ノ巣原理によって
				# 通常のトランザクションでの TXID 衝突まで考慮して、全検査を行う必要があるはずだが、
				# bitcoin 開発陣は BIP-34 による coinbase トランザクションの対策だけで
				# 十分に BIP-30 を守ることができると考えているらしく、BIP-34 施行以降は BIP-30 違反検査を省略している。
				# また、BIP-34 施行以前の coinbase トランザクションとの衝突可能性についても考察されており、
				# 次に問題となり得るのはブロック高 1,983,702 で、およそ 2045 年ごろと予測しているため、
				# それまでは完全に BIP-30 違反検査を省略するよう、bitcoind が実装されている。
				# bitcoind からフォークした monacoind も同様の実装となっており、こちらは
				# BIP-34 施行以降であるため、施行以前の coinbase トランザクションとの衝突も気にする必要がなく、
				# 完全に BIP-30 違反検査を省略する実装となっている。
				# つまり、確率的にはいずれ TXID の衝突が発生するはずだが、現状の bitcoind, monacoind の実装では
				# それを検知できずに承認してしまうという問題を抱えている。
				# 現実問題として、実際に衝突が発生した時点で問題が発生するため、急遽 BIP が作られるだろうから、
				# そのタイミングで VP-clerk も追従すればよいという方針で、とりあえず現状は、
				# coind の承認したトランザクションは全て受け入れるものとして実装を進める。

				# BIP-30 違反検査
				if not bip30_exception:
					c.execute( 'SELECT * FROM transaction_link WHERE ISNULL(vin_height) AND ISNULL(vin_txid) AND ISNULL(vin_idx) AND vout_txid = %s', (txid,) )
					if len( c.fetchall() ) != 0:
						raise Exception( 'BIP-30 violation' )

				# このトランザクションの合計出金額を計算する
				total_output = 0
				for vout in cd_transaction['vout']:
					total_output += vout['value'] * SATOSHI_COIN

				# トランザクションデータの作成
				c.execute(
					'INSERT INTO transaction VALUES ( %s, %s, %s, %s, %s, %s, %s, %s )',
					(
						txid,
						block_height,
						cd_block['hash'],
						datetime.fromtimestamp( cd_transaction['time'] ),
						len( cd_transaction['vin'] ),
						len( cd_transaction['vout'] ),
						total_output,
						base64.b64encode( bz2.compress( json.dumps( tx_json_reduce ).encode('utf-8') ) ).decode('ascii')
					)
				)

				# トランザクションリンクの片割れを作成
				destinations = []
				for vout in cd_transaction['vout']:
					# 宛先アドレスの組み立て
					scriptPubKey = vout['scriptPubKey']
					if 'addresses' in scriptPubKey:
						vout_addr = ' '.join( scriptPubKey['addresses'] )

						# 宛先全部のリストを構成
						destinations.append( vout_addr )
					else:
						vout_addr = None

					# リンクデータ作成
					c.execute(
						'INSERT INTO transaction_link VALUES ( %s, %s, %s, %s, %s, %s, %s, %s )',
						(
							None, # 受け取り TX の時に書くので UTXO として None を書く
							None,
							None,
							block_height,
							txid,
							vout['n'],
							vout_addr,
							vout['value'] * SATOSHI_COIN
						)
					)

				# コインベーストランザクションの場合はマイナーとして宛先を設定
				if 'coinbase' in cd_transaction['vin'][0]:
					miners = ' '.join( destinations )

				# トランザクションリンクの対向側を設定
				for idx in range( len( cd_transaction['vin'] ) ):
					vin = cd_transaction['vin'][idx]
					if 'txid' in vin:
						c.execute(
							'UPDATE transaction_link SET vin_height = %s, vin_txid = %s, vin_idx = %s WHERE ISNULL(vin_height) AND ISNULL(vin_txid) AND ISNULL(vin_idx) AND vout_txid = %s AND vout_idx = %s',
							(
								block_height,
								txid,
								idx,
								vin['txid'],
								vin['vout']
							)
						)
						if c.rowcount != 1:
							if c.rowcount == 0:
								# CVE-2018-17144 の攻撃対象となったトランザクションの場合は重複利用を無視する
								if not CVE_2018_17144( coind_type, txid ):
									raise Exception( block_height, txid, idx, 'missing transaction_link' )
							else:
								raise Exception( block_height, txid, idx, 'BIP-30 violation' )

				# トランザクションでの残高増減表を作成
				alter_balance = {}
				c.execute( 'SELECT * FROM transaction_link WHERE (vin_height = %s AND vin_txid = %s) OR (vout_height = %s AND vout_txid = %s)', (block_height, txid, block_height, txid) )
				for e in c.fetchall():
					addr = e['addresses']

					# アドレスがない場合は無視
					if addr is None:
						continue

					# 該当アドレスの情報がなければ先に 0 クリア
					if not addr in alter_balance:
						alter_balance[addr] = 0

					# どちらにヒットしたかによって増減表を更新する
					if e['vin_height'] == block_height and e['vin_txid'] == txid:
						alter_balance[addr] -= e['value']
					elif e['vout_height'] == block_height and e['vout_txid'] == txid:
						alter_balance[addr] += e['value']
					else:
						raise Exception( 'unknown transaction_link' )

				# レコードを追加する
				for addr, gain in alter_balance.items():
					# 直前までの残高と次のシリアルナンバーを取得する
					balance = 0
					serial = 0
					c.execute( 'SELECT serial, balance FROM balance WHERE addresses = %s ORDER BY serial DESC LIMIT 1', (addr,) )
					for e in c.fetchall():
						balance = e['balance']
						serial = e['serial'] + 1

					# 残高更新
					balance += gain

					# レコード追加
					c.execute(
						'INSERT INTO balance VALUES ( %s, %s, %s, %s, %s, %s, %s )',
						(
							addr,
							block_height,
							txid,
							serial,
							datetime.fromtimestamp( cd_transaction['time'] ),
							balance,
							gain
						)
					)

					# 最終残高の更新
					if serial == 0:
						c.execute(
							'INSERT INTO current_balance VALUES ( %s, %s )',
							(
								addr,
								balance
							)
						)
					else:
						c.execute(
							'UPDATE current_balance SET balance = %s WHERE addresses = %s',
							(
								balance,
								addr
							)
						)

			# ブロックヘッダの作成
			c.execute(
				'INSERT INTO blockheader VALUES( %s, %s, %s, %s, %s )',
				(
					block_height,
					cd_block['hash'],
					datetime.fromtimestamp( cd_block['time'] ),
					miners,
					base64.b64encode( bz2.compress( json.dumps( block_json_reduce ).encode('utf-8') ) )
				)
			)
			db.commit()
		except Exception as e:
			db.rollback()
			raise e
		finally:
			c.close()
		

# 1 ブロック分データを巻き戻す
# - 何度同じ height で実行しても問題ない
# - 何かしたら True を返す。何もしなかったら False を返す。
def revert( db, coind_type, height ):

	# トランザクション内で実行する
	db.begin()
	c = db.cursor()
	try:
		# ブロックヘッダの確認
		c.execute( 'SELECT * FROM blockheader WHERE height = %s', (height,) )
		block = c.fetchone()

		# ブロックヘッダがない場合は以降の処理は不要
		if block is None:
			return False

		# ここから巻き戻しを行う
		logging.info( '%s: revert() %d.' % (coind_type, height) )

		# ブロックヘッダは削除する
		c.execute( 'DELETE FROM blockheader WHERE height = %s', (height,) )
		if c.rowcount != 1:
			raise Exception( 'missing blockheader' )

		# ブロックの json データを読み込む
		json_block = json.loads( bz2.decompress( base64.b64decode( block['json'] ) ) )

		for txid in reversed( json_block['tx'] ):
			# トランザクションのデータを取得する
			c.execute( 'SELECT * FROM transaction WHERE height = %s AND txid = %s', ( height, txid ) )
			tx = c.fetchone()
			if tx is None:
				raise Exception( 'missing transaction' )

			# json データを読み込む
			json_tx = json.loads( bz2.decompress( base64.b64decode( tx['json'] ) ) )

			# 残高の変化があったアドレスのリスト
			# - unique にするために辞書を使う
			addresses = {}
			c.execute( 'SELECT addresses FROM transaction_link WHERE (vin_height = %s AND vin_txid = %s) OR (vout_height = %s AND vout_txid = %s)', (height, txid, height, txid) )
			for e in c.fetchall():
				if e['addresses'] is not None:
					addresses[ e['addresses'] ] = True

			# トランザクションデータは削除するだけでいい
			c.execute( 'DELETE FROM transaction WHERE height = %s AND txid = %s', ( height, txid ) )
			if c.rowcount != 1:
				raise Exception( height, txid, 'missing transaction' )

			# 出力側トランザクションリンクも削除するだけでいい
			c.execute( 'DELETE FROM transaction_link WHERE vout_height = %s AND vout_txid = %s AND ISNULL( vin_height ) AND ISNULL( vin_txid ) AND ISNULL( vin_idx )', (height, txid) )
			if c.rowcount != tx['vout_n']:
				raise Exception( txid, 'missing transaction_link (vout_n)' )

			# 入力側トランザクションリンクは NULL クリア
			# - 乱暴に vin_height, vin_txid 一致だけで消して rowcount を無視する手もあるが一応ループを回して確認する。
			for idx in range( tx['vin_n'] ):
				if 'txid' in json_tx['vin'][idx]:
					c.execute( 'UPDATE transaction_link SET vin_height = NULL, vin_txid = NULL, vin_idx = NULL WHERE vin_height = %s AND vin_txid = %s AND vin_idx = %s', (height, txid, idx) )
					if c.rowcount != 1:
						if not CVE_2018_17144( coind_type, txid ):
							raise Exception( height, txid, idx, 'missing transaction_link (vin)' )

			# 一応関連データが残っていないか確認する
			c.execute( 'SELECT * FROM transaction_link WHERE (vin_height = %s AND vin_txid = %s) OR (vout_height = %s AND vout_txid = %s)', (height, txid, height, txid) )
			if len( c.fetchall() ) != 0:
				raise Exception( height, txid, 'surviving transaction_link' )

			# 各アドレスの残高を巻き戻す
			# - 何も考えずに height, txid で一致を取って消してもよかったが、current_balance の更新が必要なので...
			for addr in addresses.keys():
				# 残高データの最新シリアル番号を取得する
				c.execute( 'SELECT MAX(serial) FROM balance WHERE addresses = %s', (addr,) )
				serial = c.fetchone()['MAX(serial)']

				# 最新の残高を更新する
				if serial == 0:
					c.execute( 'DELETE FROM current_balance WHERE addresses = %s', (addr,) )
					if c.rowcount != 1:
						raise Exception( height, txid, addr, 'missing current_balance' )
				else:
					c.execute( 'SELECT balance FROM balance WHERE addresses = %s AND serial = %s', (addr, serial - 1) )
					balance = c.fetchone()['balance']

					c.execute( 'UPDATE current_balance SET balance = %s WHERE addresses = %s', (balance, addr) )

				# 残高データ削除
				c.execute( 'DELETE FROM balance WHERE addresses = %s AND height = %s AND txid = %s AND serial = %s', (addr, height, txid, serial) )
				if c.rowcount != 1:
					raise Exception( height, txid, addr, 'missing balance' )

			# 一応関連データが残っていないか確認する
			c.execute( 'SELECT * FROM balance WHERE height = %s AND txid = %s', (height, txid) )
			if len( c.fetchall() ) != 0:
				raise Exception( height, txid, 'surviving balance' )
		db.commit()
	except Exception as e:
		db.rollback()
		raise e
	finally:
		c.close()

	return True

# コインノードのブロックハッシュと比較して必要なら巻き戻しを行う
# - 問題なければ True, 巻き戻しを行った場合 False を返す
def check_db_state( db, coind_type ):
	# 最新のブロック情報を取得する
	with db.cursor() as c:
		c.execute( 'SELECT * FROM blockheader ORDER BY height DESC LIMIT 1' )
		block = c.fetchone()

	# DB が空っぽなら何もしないでいい
	if block is None:
		return True

	# コインノードクライアントの初期化
	cd = coind_factory( coind_type )

	# ブロックハッシュを確認
	db_blockhash = block['hash']
	cd_blockhash = cd.run( 'getblockhash', [ block['height'] ] )

	# 一致していたら問題なく次へ進んでいい
	if db_blockhash == cd_blockhash:
		return True

	# この高さのブロックを一旦削除する
	revert( db, coind_type, block['height'] )

	return False

# データベースの作成とテーブルの作成、初期化を行う
def init_db( coind_type ):
	# 一旦標準データベースに接続してデータベースの作成を行う
	db = CloudSQL ( 'mysql' )
	db.begin()
	c = db.cursor()
	try:
		# 本来であればプレイスホルダを使用したいところだが、
		# MySQL の仕様では DB 名は文字列ではないらしいので、
		# % で SQL 文を組み立てる。coind_type は入力チェックをパスしているため、
		# SQL インジェクションにはならないはず。
		c.execute( 'CREATE DATABASE %s' % coind_type )
		db.commit()
	except Exception as e:
		db.rollback()
		raise e
	finally:
		c.close()
		db.close()

	# 作成したデータベースに接続して、テーブルを作成する
	# MySQL 仕様によると、CREATE TABLE は暗黙コミットされるので
	# トランザクションの意味はまったくないが、失敗したら手動で
	# DB ごと消せばいいのでとりあえずこれで
	db = CloudSQL( coind_type )
	db.begin()
	c = db.cursor()
	try:
		c.execute('''
			CREATE TABLE state (
				running_flag BOOL NOT NULL,
				running_time DATETIME
			)
		''')
		c.execute('''
			CREATE TABLE blockheader (
				height BIGINT UNSIGNED NOT NULL PRIMARY KEY,
				hash VARCHAR(128) NOT NULL,
				time DATETIME NOT NULL,
				miners TEXT,
				json LONGTEXT NOT NULL,
				INDEX( hash )
			)
		''')
		c.execute('''
			CREATE TABLE transaction (
				txid VARCHAR(128) NOT NULL,
				height BIGINT UNSIGNED NOT NULL,
				blockhash VARCHAR(128) NOT NULL,
				time DATETIME NOT NULL,
				vin_n INT NOT NULL,
				vout_n INT NOT NULL,
				total_output BIGINT UNSIGNED NOT NULL,
				json LONGTEXT NOT NULL,
				INDEX( time ),
				INDEX( txid ),
				PRIMARY KEY( height, txid )
			)
		''')
		c.execute('''
			CREATE TABLE transaction_link (
				vin_height BIGINT UNSIGNED,
				vin_txid VARCHAR(128),
				vin_idx INT,
				vout_height BIGINT UNSIGNED NOT NULL,
				vout_txid VARCHAR(128) NOT NULL,
				vout_idx INT NOT NULL,
				addresses VARCHAR(1300) CHARACTER SET ASCII,
				value BIGINT UNSIGNED NOT NULL,
				INDEX( addresses, vin_txid ),
				INDEX( vin_height, vin_txid, vin_idx, vout_txid, vout_idx ),
				INDEX( vin_height, vin_txid, vin_idx ),
				INDEX( vout_height, vout_txid, vout_idx )
			)
		''')
		c.execute('''
			CREATE TABLE balance (
				addresses VARCHAR(1300) CHARACTER SET ASCII NOT NULL,
				height BIGINT UNSIGNED NOT NULL,
				txid VARCHAR(128) NOT NULL,
				serial BIGINT UNSIGNED NOT NULL,
				time DATETIME NOT NULL,
				balance BIGINT UNSIGNED NOT NULL,
				gain BIGINT NOT NULL,
				INDEX( height, txid ),
				INDEX( addresses, serial ),
				PRIMARY KEY( addresses, height, txid )
			)
		''')
		c.execute('''
			CREATE TABLE current_balance (
				addresses VARCHAR(1300) CHARACTER SET ASCII NOT NULL PRIMARY KEY,
				balance BIGINT UNSIGNED NOT NULL,
				INDEX( balance )
			)
		''')
		c.execute( 'INSERT INTO state VALUES ( 0, NULL )' )
		db.commit()
	except Exception as e:
		db.rollback()
		raise e
	finally:
		c.close()

	return db

def run( coind_type, max_leng ):
	try:
		# 指定された coind のデータベースへ接続する
		db = CloudSQL( coind_type )
	except MySQLdb.OperationalError:
		# 接続に失敗した場合、データベースの作成から行う
		db = init_db( coind_type )
		logging.info( coind_type + ': DB initialized.' )

	# 同時実行を防ぐため、ロックをかける
	with db.cursor() as c:
		# 同時実行がない場合、もしくは指定秒数以上経過していれば UPDATE に成功する
		c.execute( 'UPDATE state SET running_flag = 1, running_time = NOW() WHERE running_flag = 0 OR TIMESTAMPADD( SECOND, %d, running_time ) < NOW()' % LOCK_TIMEOUT )
		if c.rowcount != 1:
			# ロック確保に失敗したらここで止める
			raise Exception( 'running another!!' )

		db.commit()
		
	# 開始時のポイントを覚えておく
	with db.cursor() as c:
		c.execute( 'SELECT IFNULL(MAX(height)+1,0) FROM blockheader' )
		start_block_height = c.fetchone()['IFNULL(MAX(height)+1,0)']

	# ここで DB 更新作業を行う
	if check_db_state( db, coind_type ):
		# 巻き戻しを行わなかった場合のみ更新に進む
		sync( db, coind_type, max_leng )

	# 終了時のポイントを取得する
	with db.cursor() as c:
		c.execute( 'SELECT IFNULL(MAX(height)+1,0) FROM blockheader' )
		end_block_height = c.fetchone()['IFNULL(MAX(height)+1,0)']

	# ロック解除
	with db.cursor() as c:
		c.execute( 'UPDATE state SET running_flag = 0, running_time = NULL' )
		db.commit()

	# 実行結果をログと戻り値の双方に記述する
	result = 'update_db: %d => %d' % ( start_block_height, end_block_height )

	logging.info( '%s: %s' % ( coind_type, result ) )
	return { 'result': result }

# アップデートをシリアライズするため queue を経由する
class handler( BaseHandler ):
	def add_cloudtasks( self, queue_name, coind_type, max_leng ):
		client = CloudTasksClient()
		parent = client.queue_path( config.gcp_project_id, config.gcp_location_id, queue_name )
		task_request_body = urlencode( {
			'coind_type': coind_type,
			'max_leng': max_leng
		} ).encode('ascii')
		task = {
			'app_engine_http_request': {
				'http_method': 'POST',
				'relative_uri': '/maintain/cron/update_db',
				'headers': { 'Content-Type': 'application/x-www-form-urlencoded' },
				'body': task_request_body
			}
		}
		client.create_task( parent=parent, task=task )

	def get( self ):
		self.add_cloudtasks( 'update-main-db-monacoind', 'monacoind', 7000 )
		self.add_cloudtasks( 'update-main-db-monacoind-test', 'monacoind_test', 7000 )
		return "OK"

	def post( self, request ):
		coind_type = self.get_request_coind_type(request)
		max_leng = self.get_request_int( request, 'max_leng', 7000 )
		return json.dumps( run( coind_type, max_leng ) )
