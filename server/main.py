#========================================================#
#                                                        #
#  VP-clerk: main.py - API サーバのメイン                #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import webapp2
import json

import update_db
import sendrawtransaction
import getrecentblkid
import getblock
import getrecenttxid
import gettransaction
import getbalance
import getmillionaires
import getaddress
import preparetx
import submittx

app = webapp2.WSGIApplication([
	# 公開 API
	('/api/v1/recentblkid', getrecentblkid.handler),
	('/api/v1/block', getblock.handler),
	('/api/v1/recenttxid', getrecenttxid.handler),
	('/api/v1/transaction', gettransaction.handler),
	('/api/v1/balance', getbalance.handler),
	('/api/v1/millionaires', getmillionaires.handler),
	('/api/v1/address', getaddress.handler),
	('/api/v1/preparetx', preparetx.handler),
	('/api/v1/submittx', submittx.handler),

	# 非公開 API
	('/maintain/sendrawtransaction', sendrawtransaction.handler),
	('/maintain/cron/update_db', update_db.handler)
])
