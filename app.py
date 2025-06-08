from flask import Flask, request, render_template, render_template_string
from supabase import create_client, Client
import os
import secrets
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from email_util import send_email

app = Flask(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

token_table = supabase.table('Tokens')
subscriber_table = supabase.table('Subscribers')

def render_message_page(title, message):
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ max-width: 600px; margin: 50px auto; font-family: Arial; }}
            .box {{ padding: 30px; border: 1px solid #ccc; border-radius: 8px; background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>{title}</h2>
            <p>{message}</p>
            <a href="/" class="btn btn-outline-primary mt-3">回首頁</a>
        </div>
    </body>
    </html>
    """)

# create confirm email content
def create_confirm_email_content(email, token, is_active):

    if is_active:
        html_content = f"""
        <html>
        <body>
            <h2>訂閱確認</h2>
            <p>您已經訂閱過新品通知，無需再次操作</p>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <html>
        <body>
            <h1>訂閱確認</h1>
            <p>請點擊以下連結完成訂閱：</p>
            <a href="https://bf44-2407-4d00-4c00-421-34e2-8d55-555a-ff55.ngrok-free.app/confirm-subscribe?token={token}&email={email}">確認訂閱</a>
            <p>連結 30 分鐘內有效</p>
        </body>
        </html>
        """
    return html_content

def create_status_email_content(email, status):
    html_content = f"""
    <html>
    <body>
        <h2>Hermès 訂閱狀態查詢結果</h2>
        <p>{email} 的訂閱狀態為：<strong>{status}</strong></p>
        <p>若您不是本人，請忽略此信。</p>
    </body>
    </html>
    """
    return html_content

def create_unsubscribe_email_content(email, token, is_active):

    if is_active:
        html_content = f"""
        <html>
        <body>
            <h2>取消訂閱連結</h2>
            <p>請點擊以下連結取消訂閱：</p>
            <a href="https://bf44-2407-4d00-4c00-421-34e2-8d55-555a-ff55.ngrok-free.app/unsubscribe?token={token}&email={email}">取消訂閱</a>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <html>
        <body>
            <h2>取消訂閱通知</h2>
            <p>您已經取消訂閱，無需再次操作。</p>
        </body>
        </html>
        """
    return html_content
@app.route('/')
def index():
    return render_template('index.html')




def create_token(email, purpose):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    # 刪除舊的紀錄，插入新的 pending 訂閱
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

def is_valid_token(token):
    response = token_table.select("*").eq("token", token).execute()
    if not response.data:
        print(f"Token {token} not found")
        return False
    if response.data[0]["is_used"]:
        print(f"Token {token} has already been used")
        return False
    expires_at = isoparse(response.data[0]["expires_at"])

    return expires_at > datetime.now(timezone.utc)

def update_token_usage(token):
    # 更新 token 狀態為已使用
    token_table.update({"is_used": True}).eq("token", token).execute()

    # 刪除過期的 token
    expiration_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    token_table.delete().lt("created_at", expiration_time.isoformat()).execute()

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form["email"].strip().lower()

    response = subscriber_table.select("is_active").eq("email", email).execute()
    is_active = False
    if response.data:
        is_active = response.data[0].get("is_active")
        if is_active:
            token = None

    if not is_active:
        token = create_token(email, 'subscribe')

    email_content = create_confirm_email_content(email, token, is_active)
    send_email([email], "Hermès Notify 確認訂閱", email_content)
    return render_template('result.html', title="確認信已發送", message="已發送確認信件，請查收信箱")


@app.route("/send-status-link", methods=["POST"])
def send_status_link():
    email = request.form["email"].strip()

    # 查訂閱狀態
    response = subscriber_table.select("*").eq("email", email).execute()
    if not response.data:
        status = "尚未訂閱"
    else:
        row = response.data[0]
        is_active = row.get("is_active")
        ends_at = isoparse(row.get("ends_at"))

        if is_active:
            status = "訂閱中，下一次扣款日期為 " + ends_at.strftime("%Y-%m-%d")
        else:
            if datetime.now(timezone.utc).date() <= ends_at.date():
                status = "已取消訂閱，在" + ends_at.strftime("%Y-%m-%d") + " 之前，您將可以繼續使用此服務"
            else:
                status = "已取消訂閱，且已過期"

    content = create_status_email_content(email, status)
    send_email([email], "Hermès Notify 訂閱狀態", content)
    return render_template('result.html', title="查詢結果已寄出", message="請查收您的信箱")


@app.route("/send-unsubscribe-link", methods=["POST"])
def send_unsubscribe_link():
    email = request.form["email"].strip().lower()
    response = subscriber_table.select("is_active").eq("email", email).execute()

    if not response.data:
        return render_message_page("錯誤", "查無此 Email 訂閱紀錄")
    
    is_active = response.data[0].get("is_active")
    token = create_token(email, 'unsubscribe')
    content = create_unsubscribe_email_content(email, token, is_active)
    send_email([email], "Hermès Notify 取消訂閱", content)
    return render_template('result.html', title="取消連結已寄出", message="已寄出取消連結，請查收信箱")


@app.route("/confirm-subscribe")
def confirm_subscribe():
    token = request.args.get("token")
    if not is_valid_token(token):
        return render_message_page("錯誤", "無效的或已過期，請重新訂閱")
    
    token_row = supabase.table("Tokens").select("email").eq("token", token).eq("purpose", 'subscribe').execute().data[0]
    email = token_row["email"]

    update_token_usage(token)

    subscriber_table.upsert({
        "email": email,
        "plan": "monthly",
        "is_active": True,
        "subscribes_at": datetime.now(timezone.utc).isoformat(),
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    }, on_conflict=['email']).execute()
    return render_template('result.html', title="訂閱成功", message=f"{email} 的訂閱已完成！")


@app.route("/unsubscribe")
def unsubscribe():
    token = request.args.get("token")
    if not is_valid_token(token):
        return render_message_page("連結過期", "無效或已過期，請重新進行取消")

    token_row = supabase.table("Tokens").select("email").eq("token", token).eq("purpose", 'unsubscribe').execute().data[0]
    email = token_row["email"]

    update_token_usage(token)

    subscriber_table.update({
        "is_active": False,
    }).eq("email", email).execute()

    result = subscriber_table.select("email, ends_at").eq("email", email).execute()
    ends_at = isoparse(result.data[0].get("ends_at"))
    
    return render_template('result.html', title="取消成功", message=f"{email} 的訂閱已取消！在 {ends_at.strftime('%Y-%m-%d')} 之前，您仍然可以使用此服務。")

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

'''
@app.route("/test-send")
def test_send():
    html = "<strong>這是測試信件，感謝你訂閱 Hermès Notify</strong>"
    result = send_email("aak.org@gmail.com", "Hermès Notify 測試信", html)
    return "寄信成功" if result == 202 else "寄信失敗"
'''

if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0',port=port)

