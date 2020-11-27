#========================================================#
#                                                        #
#  VP-clerk: base_handler.py - 共通リクエストハンドラ    #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import json
from coind import coind_factory
from urllib.parse import parse_qs

# バリデーションに失敗した場合に投げる例外
class ValidationError( Exception ):
	def __init__( self, element, msg ):
		self.element = element
		self.msg = msg

class BaseHandler():
	def get_request_coind_type( self, request ):
		if request.method == "POST":
		    coind_type = request.form.get("coind_type")
		    if coind_type is None:
		    	coind_type = parse_qs( request.data.decode('utf-8') )['coind_type'][0]
		else:
		    coind_type = request.args["coind_type"]

		# ベリファイのためにクライアントを構築してみる
		try:
			cd = coind_factory( coind_type )
		except Exception as e:
			raise ValidationError( 'coind_type', e.args[0] )

		return coind_type

	def get_request_int( self, request, name, default = None ):
		if request.method == "POST":
			n = request.form.get(name, default)
		else:
			n = request.args.get(name, default)

		try:
			return int( n )
		except Exception:
			return default

	def write_json( self, r ):
		return json.dumps(r)
