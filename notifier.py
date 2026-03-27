"""
通知推送模組
支援: Email (HTML格式) / LINE Notify
"""
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    EMAIL_ENABLED, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER,
    EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
    LINE_NOTIFY_ENABLED, LINE_NOTIFY_TOKEN,
)

logger = logging.getLogger(__name__)


def send_email(subject: str, html_body: str, plain_body: str = "") -> bool:
    """
    發送 HTML 格式 Email

    Gmail 設定說明：
    1. 到 Google 帳戶 > 安全性 > 開啟兩步驟驗證
    2. 搜尋「應用程式密碼」，產生 16 碼密碼填入 .env
    """
    if not EMAIL_ENABLED:
        logger.info("Email 通知已停用（EMAIL_ENABLED=false）")
        return False

    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        logger.error("Email 設定不完整，請檢查 .env 中 EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECEIVER")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        if plain_body:
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

        logger.info(f"Email 已發送至 {EMAIL_RECEIVER}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Email 認證失敗，請確認帳號密碼（Gmail 需使用應用程式密碼）")
        return False
    except Exception as e:
        logger.error(f"Email 發送失敗: {e}")
        return False


def send_line_notify(message: str) -> bool:
    """
    發送 LINE Notify 通知
    取得 Token: https://notify-bot.line.me/my/
    單則訊息上限約 1000 字，過長會自動截斷
    """
    if not LINE_NOTIFY_ENABLED:
        logger.info("LINE Notify 已停用（LINE_NOTIFY_ENABLED=false）")
        return False

    if not LINE_NOTIFY_TOKEN:
        logger.error("LINE_NOTIFY_TOKEN 未設定")
        return False

    # LINE Notify 單則上限
    if len(message) > 950:
        message = message[:950] + "\n...(訊息過長已截斷)"

    try:
        resp = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"},
            data={"message": message},
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info("LINE Notify 發送成功")
            return True
        else:
            logger.error(f"LINE Notify 失敗: HTTP {resp.status_code} — {resp.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error("LINE Notify 連線逾時")
        return False
    except Exception as e:
        logger.error(f"LINE Notify 發送失敗: {e}")
        return False
