
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from threading import Thread


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

def send_email_async(to_email, subject, html_content):
    def _send():
        send_email(to_email, subject, html_content)  # 你原本的寄信函式
    Thread(target=_send).start()



'''
def send_email(email_addr,html_content):

    content = MIMEText(html_content, 'html')


    # Email 設定
    from_addr = "aak.org@gmail.com"
    to_addr = "aak.org@gmail.com"
    bcc_list = email_addr
    subject = "新品上市通知"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    msg.attach(content)

    # 發送 Email (以 Gmail 為例)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = from_addr
    smtp_pass = "ilrq ubae vuqc ekni"  # 注意，不是 Gmail 密碼，要產生 App Password

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr]+bcc_list, msg.as_string())

    print("Email 已發送成功！")
'''