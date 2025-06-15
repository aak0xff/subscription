
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from threading import Thread

'''
def send_email(to_email, subject, html_content):
    message = Mail(
        from_email=('no-reply@pinggle.me', 'Pinggle Hermes 通知系統'),
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        print(os.environ.get('SENDGRID_API_KEY'))
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        return response.status_code
    except Exception as e:
        print(e)
        return None

'''
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(email_addr_list, subject, html_content):
    from_addr = "aak.org@gmail.com"
    to_addr = from_addr  # 主收件人（會收到）
    bcc_list = email_addr_list  # 實際通知對象（隱藏收件人）

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    msg.attach(MIMEText(html_content, 'html'))

    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = from_addr
    smtp_pass = "tuha gusr lyuj itts"  # 建議用 os.environ 讀取

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr] + bcc_list, msg.as_string())

    print("✅ Email 已成功發送！")
