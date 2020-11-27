#========================================================#
#                                                        #
#  VP-clerk: main.py - API サーバのメイン                #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from flask import *
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging
from base_handler import ValidationError

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

app = Flask(__name__)

# ロギングの設定
@app.before_request
def before_request():
    client = google.cloud.logging.Client()
    handler = CloudLoggingHandler( client )
    logging.getLogger().setLevel( logging.INFO )
    setup_logging( handler )

# CORS の設定
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Content-Type", "application/json")
    return response

# 各 API のハンドラー
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

@app.route("/api/v1/submittx", methods=["POST"])
def submittransaction():
    return submittx.handler().post(request)

# 非公開 API
@app.route("/maintain/sendrawtransaction", methods=["POST"])
def sendrawtx():
    return sendrawtransaction.handler().post(request)

@app.route("/maintain/cron/update_db", methods=["GET", "POST"])
def updateDb():
    if request.method == "GET":
        return update_db.handler().get()
    else:
        return update_db.handler().post(request)

# エラーハンドラ
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def error(e):
    if e.code != "404":
        logging.exception(e)
    return jsonify({"exception": "Exception", "type": e.name, "args": e.description}), e.code

@app.errorhandler(ValidationError)
def validationError(e):
    logging.exception(e)
    return jsonify({"exception": "validation", "msg": e.msg, "element": e.element}), 400

@app.errorhandler(Exception)
def exceptionError(e):
    logging.exception(e)
    return jsonify({"exception": "Exception", "msg": e.args, "type": e.__doc__}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8888, threaded=True)
