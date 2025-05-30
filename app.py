from flask import Flask, request, jsonify
import hashlib
import urllib.parse
from Crypto.Cipher import AES
import base64
import json

app = Flask(__name__)

# 替換成你的藍新金鑰資料
MERCHANT_ID = '你的 MerchantID'
HASH_KEY = '你的 HashKey'
HASH_IV = '你的 HashIV'

# AES 加密
def aes_encrypt(data):
    data = urllib.parse.urlencode(data)
    pad = 32 - len(data) % 32
    data += chr(pad) * pad
    cipher = AES.new(HASH_KEY.encode('utf-8'), AES.MODE_CBC, HASH_IV.encode('utf-8'))
    encrypted = cipher.encrypt(data.encode('utf-8'))
    return base64.b64encode(encrypted).decode()

# SHA256 簽名
def sha256_hash(trade_info):
    raw = f'HashKey={HASH_KEY}&{trade_info}&HashIV={HASH_IV}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()

@app.route('/create-order', methods=['POST'])
def create_order():
    data = request.json
    order = {
        "MerchantID": MERCHANT_ID,
        "RespondType": "JSON",
        "TimeStamp": "1700000000",
        "Version": "1.5",
        "MerchantOrderNo": "ORDER12345",  # 改成你的訂單編號生成方式
        "Amt": 100,
        "ItemDesc": "Hermès 訂閱服務",
        "Email": data.get('email', 'test@example.com'),
        "TokenTerm": "token_term",  # 必要參數
        "TokenSwitch": "on",        # 開啟信用卡定期扣款
        "PeriodAmt": 100,           # 每期金額
        "PeriodType": "M",          # 每月
        "PeriodPoint": 1,           # 每月第 1 天扣款
        "PeriodStartType": 2,       # 下一期開始
        "PeriodTimes": 12           # 總共期數
    }

    trade_info = aes_encrypt(order)
    trade_sha = sha256_hash(trade_info)

    return jsonify({
        "MerchantID": MERCHANT_ID,
        "TradeInfo": trade_info,
        "TradeSha": trade_sha,
        "Version": "1.5"
    })

@app.route('/newebpay_notify', methods=['POST'])
def notify():
    data = request.form
    print("收到藍新通知", data)
    return "OK"

@app.route('/')
def index():
    return 'Hello, this is Latest Subscription API!'

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=10000)

