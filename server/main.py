#========================================================#
#                                                        #
#  VP-clerk: main.py - API サーバのメイン                #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import webapp2
from flask import *
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

# app = webapp2.WSGIApplication([
# 	# 公開 API
# 	('/api/v1/recentblkid', getrecentblkid.handler),
# 	('/api/v1/block', getblock.handler),
# 	('/api/v1/recenttxid', getrecenttxid.handler),
# 	('/api/v1/transaction', gettransaction.handler),
# 	('/api/v1/balance', getbalance.handler),
# 	('/api/v1/millionaires', getmillionaires.handler),
# 	('/api/v1/address', getaddress.handler),
# 	('/api/v1/preparetx', preparetx.handler),
# 	('/api/v1/submittx', submittx.handler),

# 	# 非公開 API
# 	('/maintain/sendrawtransaction', sendrawtransaction.handler),
# 	('/maintain/cron/update_db', update_db.handler)
# ])

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Content-Type", "application/json")

@app.route("/api/v1/recentblkid")
def recentblkid():
    return getrecentblkid.handler().get(request)

@app.route("/api/v1/block")
def block():
    return getblock.handler().get(request)

@app.route("/api/v1/recenttxid")
def recenttxid():
    return getrecenttxid.handler().get(request)

@app.route("/api/v1/transaction")
def transaction():
    return gettransaction.handler().get(request)

@app.route("/api/v1/balance")
def balance():
    return getbalance.handler().get(request)

@app.route("/api/v1/millionaires")
def millionaires():
    return getmillionaires.handler().get(request)

@app.route("/api/v1/address")
def address():
    return getaddress.handler().get(request)

@app.route("/api/v1/preparetx")
def preparetransaction():
    return preparetx.handler().get(request)

@app.route("/api/v1/submittx")
def submittransaction():
    return submittx.handler().get(request)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8888, threaded=True)