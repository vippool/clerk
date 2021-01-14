#========================================================#
#                                                        #
#  VP-clerk: getaddress.py - 公開鍵からアドレスに変換    #
#                                                        #
#                            (C) 2019-2021 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from base_handler import ValidationError
from util import encode_coin_address
from util import parse_pub_key

class handler( BaseHandler ):
	def get( self, request ):
		coind_type = self.get_request_coind_type(request)
		pub_key = request.args.get('pub_key')

		# 公開鍵をバイナリ配列にする
		d1 = parse_pub_key( pub_key, 'pub_key' )

		# アドレスに変換する
		address = encode_coin_address( d1, coind_type )

		return self.write_json( { 'address': address } )
