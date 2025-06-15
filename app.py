from flask import Flask, request, render_template, redirect, session
from supabase import create_client, Client
import os
import secrets
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from email_util import send_email
from threading import Thread

from flask import abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(days=7)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

token_table = supabase.table('Tokens')
subscriber_table = supabase.table('Subscribers')

def render_message_page(title, message):
    return render_template("message.html", title=title, message=message)


def create_token(email, purpose, ip):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    token_table.insert({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "token": token,
        "purpose": purpose,
        "expires_at": expires_at,
        "ip": ip,
        "is_used": False
    }).execute()
    return token

def is_valid_token(token, purpose):
    rows = token_table.select("*").eq("token", token).eq("purpose", purpose).execute().data
    if not rows or rows[0]["is_used"]:
        return False
    expires_at = isoparse(rows[0]["expires_at"])
    return expires_at > datetime.now(timezone.utc)

def update_token_usage(token):
    token_table.update({"is_used": True}).eq("token", token).execute()

@app.route('/')
def index():
    if session.get("user_email"):
        return redirect("/dashboard")
    return render_template("index.html")

myurl = 'https://pinggle.me'

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].strip().lower()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # 查詢帳號
    sub = subscriber_table.select("is_active").eq("email", email).execute()
    is_existing_user = bool(sub.data)
    is_active = sub.data[0]["is_active"] if is_existing_user else False

    # 建立 token
    token = secrets.token_urlsafe(32)
    purpose = "subscribe" if not is_existing_user else "login"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    token_table.insert({
        "email": email,
        "token": token,
        "purpose": purpose,
        "expires_at": expires_at,
        "ip": ip,
        "is_used": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    link = f"{myurl}/verify?token={token}"
    btn = "立即訂閱" if purpose == "subscribe" else "立即登入"
    html = f"""
    <html><body style="font-family:Arial;background:#fff;padding:20px;">
    <div style="max-width:600px;margin:auto;border:1px solid #eee;border-radius:10px;padding:30px;background:#f9f9f9;">
      <h2 style="color:#b35400;">Pinggle 通知系統</h2>
      <p>請點擊以下連結{btn}：</p>
      <a href="{link}" style="display:inline-block;background-color:#b35400;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;">{btn}</a>
      <p style="margin-top:20px;font-size:14px;color:#888;">此連結 30 分鐘內有效</p>
    </div></body></html>
    """

    Thread(target=send_email, args=([email], f"Pinggle：{btn}連結", html)).start()
    return render_template("message.html", title="信件已寄出", message="請查收信箱點擊連結完成驗證。")

@app.route("/verify")
def verify():
    token = request.args.get("token")
    if not token:
        return render_template("message.html", title="驗證失敗", message="缺少 token")

    res = token_table.select("*").eq("token", token).execute()
    if not res.data:
        return render_template("message.html", title="驗證失敗", message="無效的連結")

    row = res.data[0]
    if row["is_used"] or isoparse(row["expires_at"]) < datetime.now(timezone.utc):
        return render_template("message.html", title="驗證失敗", message="連結已過期")

    email = row["email"]
    purpose = row["purpose"]

    # 更新 token 使用狀態
    token_table.update({"is_used": True}).eq("token", token).execute()

    session.permanent = True
    session["user_email"] = email

    # 若是新帳號，順便建立訂閱資料
    if purpose == "subscribe":
        subscriber_table.insert({
            "email": email,
            "plan": "monthly",
            "is_active": True,
            "subscribes_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
        }).execute()

    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    email = session.get("user_email")
    if not email:
        return redirect("/")

    sub = subscriber_table.select("is_active, ends_at").eq("email", email).execute()
    is_active = sub.data[0]["is_active"] if sub.data else False
    ends_at = sub.data[0]["ends_at"] if sub.data else None
    return render_template("dashboard.html", email=email, is_active=is_active, ends_at=ends_at)

@app.route("/subscribe-action")
def subscribe_action():
    email = session.get("user_email")
    if not email:
        return redirect("/")

    # 建立或更新訂閱資料
    now = datetime.now(timezone.utc)
    next_billing = (now + timedelta(days=30)).date().isoformat()

    subscriber_table.upsert({
        "email": email,
        "plan": "monthly",
        "is_active": True,
        "subscribes_at": now.isoformat(),
        "ends_at": next_billing
    }, on_conflict=['email']).execute()

    return redirect("/dashboard")

@app.route("/unsubscribe-action")
def unsubscribe():
    email = session.get("user_email")
    if email:
        subscriber_table.update({"is_active": False}).eq("email", email).execute()
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect("/")

@app.route('/privacy')
def privacy():
    return render_template("privacy.html")

@app.route('/terms')
def terms():
    return render_template("terms.html")



@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    if text.lower() == "/start":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入你訂閱時填寫的 Email（例如：xxx@gmail.com）")
        )
    elif "@" in text and "." in text:
        email = text.lower()
        res = subscriber_table.select("email").eq("email", email).execute()
        if res.data:
            subscriber_table.update({
                "line_user_id": user_id,
                "notify_line": True
            }).eq("email", email).execute()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="✅ 綁定成功！之後新品會以 LINE 通知你")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="找不到這個 Email，請確認你是否已在網站完成訂閱")
            )

def send_line_message(user_id, message):
    line_bot_api.push_message(user_id, TextSendMessage(text=message))



if __name__ == '__main__':
    app.run(debug=True)
