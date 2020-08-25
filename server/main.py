#========================================================#
#                                                        #
#  VP-clerk: main.py - API サーバのメイン                #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from flask import *
import logging
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

# CORSの設定
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Content-Type", "application/json")
    return response

# 各APIのハンドラー
## return以後の呼び出しについては以下デモレポジトリ参照
## https://github.com/ry0y4n/clerk-flask
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

# 非公開API
@app.route("/maintain/sendrawtransaction", methods=["POST"])
def sendrawtx():
    return sendrawtransaction.handler().post(request)

@app.route("/maintain/cron/update_db", methods=["GET", "POST"])
def updateDb():
    if request.method == "GET":
        return update_db.handler().get(request)
    else:
        return update_db.handler().post(request)

# base_handle.pyのhandle_exception代わり
## 各ステータスのエラーハンドラー (404以外ロギング)
@app.errorhandler(400)
def error_400(e):
    logging.exception(e)
    return jsonify({"exception": "Exception", "type": e.name, "args": e.description})

@app.errorhandler(404)
def error_404(e):
    return jsonify({"exception": "Exception", "type": e.name, "args": e.description})

@app.errorhandler(500)
def error_500(e):
    logging.exception(e)
    return jsonify({"exception": "Exception", "type": e.name, "args": e.description})

@app.errorhandler(ValidationError)
def validationError(e):
    return jsonify({"exception": "validation", "msg": e.msg, "element": e.element})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8888, threaded=True)
