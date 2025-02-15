import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from flask import current_app

logger = logging.getLogger(__name__)

def send_email(to: str, subject: str, body: str) -> bool:
    """
    发送邮件通知
    
    参数:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容
        
    返回:
        是否发送成功
    """
    try:
        # 获取邮件配置
        smtp_server = current_app.config['SMTP_SERVER']
        smtp_port = current_app.config['SMTP_PORT']
        smtp_username = current_app.config['SMTP_USERNAME']
        smtp_password = current_app.config['SMTP_PASSWORD']
        sender = current_app.config['MAIL_SENDER']
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        
        # 添加邮件内容
        msg.attach(MIMEText(body, 'plain'))
        
        # 连接SMTP服务器并发送
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        logger.info(f'已发送邮件通知至 {to}')
        return True
        
    except Exception as e:
        logger.error(f'发送邮件通知失败: {str(e)}')
        return False

def send_telegram(chat_id: str, message: str) -> bool:
    """
    发送Telegram通知
    
    参数:
        chat_id: Telegram聊天ID
        message: 消息内容
        
    返回:
        是否发送成功
    """
    try:
        # 获取Telegram配置
        bot_token = current_app.config['TELEGRAM_BOT_TOKEN']
        
        # 发送消息
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        
        logger.info(f'已发送Telegram通知至 {chat_id}')
        return True
        
    except Exception as e:
        logger.error(f'发送Telegram通知失败: {str(e)}')
        return False 