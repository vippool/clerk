#========================================================#
#                                                        #
#  VP-clerk: base_handler.py - 共通リクエストハンドラ    #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import webapp2
import logging
import json
from coind import coind_factory

# バリデーションに失敗した場合に投げる例外
class ValidationError( Exception ):
	def __init__( self, element, msg ):
		self.element = element
		self.msg = msg

class BaseHandler( webapp2.RequestHandler ):
	def get_request_coind_type( self ):
		coind_type = self.request.get('coind_type')

		# ベリファイのためにクライアントを構築してみる
		try:
			cd = coind_factory( coind_type )
		except Exception as e:
			raise ValidationError( 'coind_type', e.message )

		return coind_type

	def get_request_int( self, name, default = None ):
		n = self.request.get( name )

		if n is None:
			return default

		try:
			return int( n )
		except Exception:
			return default

	def write_json( self, r ):
		self.response.headers['Access-Control-Allow-Origin'] = '*'
		self.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
		self.response.headers['Access-Control-Allow-Headers'] = '*'
		self.response.headers['Content-Type'] = 'application/json'
		self.response.write( json.dumps(r) )

	def handle_exception( self, exception, debug ):
		# デフォルトではバックトレース有効
		logging_flag = True

		# 例外の種類によって適切なエラーコードと json データを返す
		if isinstance( exception, ValidationError ):
			self.response.set_status( 400 )
			self.write_json( { 'exception': 'validation', 'element': exception.element, 'msg': exception.msg } )
		elif isinstance( exception, webapp2.HTTPException ):
			self.response.set_status( exception.code )
			self.write_json( { 'exception': 'HTTPException', 'explanation': exception.explanation } )

			# 404 エラーの場合はログに残さない
			if( exception.code == 404 ):
				logging_flag = False
		else:
			self.response.set_status( 500 )
			self.write_json( { 'exception': 'Exception', 'type': exception.__class__.__name__, 'args': exception.args } )

		# GAE システムログにバックトレースを残す
		if( logging_flag ):
			logging.exception( exception )
