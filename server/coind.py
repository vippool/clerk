#========================================================#
#                                                        #
#  VP-clerk: coind.py - coind 接続クライアント           #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import httplib
import base64
import json
import config

class coind_base:
	def run( self, method, params ):
		header = {
			'Authorization': 'Basic %s' % base64.standard_b64encode( '%s:%s' % ( self.rpc_user, self.rpc_pass ) )
		}
		body = {
			'method': method,
			'params': params
		}
		conn = httplib.HTTPConnection( self.rpc_addr, self.rpc_port )
		conn.request( 'POST', '/', json.dumps(body), header )
		res = conn.getresponse()
		if res.status == 200:
			js = json.loads( res.read() )
			if js['error'] == None:
				return js['result']
			raise Exception( 'coind error: %s' % js['error'] )
		else:
			raise Exception( 'coind error: %d' % res.status, res.read() )

class monacoind( coind_base ):
	def __init__( self ):
		self.rpc_addr = config.monacoind_addr
		self.rpc_port = config.monacoind_port
		self.rpc_user = config.monacoind_user
		self.rpc_pass = config.monacoind_pass

class monacoind_test( coind_base ):
	def __init__( self ):
		self.rpc_addr = config.monacoind_test_addr
		self.rpc_port = config.monacoind_test_port
		self.rpc_user = config.monacoind_test_user
		self.rpc_pass = config.monacoind_test_pass

def coind_factory( coind_type ):
	if coind_type == 'monacoind':
		return monacoind()
	if coind_type == 'monacoind_test':
		return monacoind_test()
	raise Exception( 'unknown coind_type: %s' % coind_type )
