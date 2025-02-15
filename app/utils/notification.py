import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from flask import current_app
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 通知限流器
class RateLimiter:
    _limits = {}
    
    @classmethod
    def check_rate_limit(cls, key: str, max_count: int, period: int) -> bool:
        """
        检查是否超过限流阈值
        
        参数:
            key: 限流键
            max_count: 时间段内最大允许次数
            period: 时间段（秒）
        """
        now = time.time()
        if key not in cls._limits:
            cls._limits[key] = []
        
        # 清理过期记录
        cls._limits[key] = [t for t in cls._limits[key] if now - t < period]
        
        # 检查是否超过限制
        if len(cls._limits[key]) >= max_count:
            return False
        
        # 添加新记录
        cls._limits[key].append(now)
        return True

def rate_limit(max_count: int, period: int):
    """限流装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args[0]}"  # 使用函数名和第一个参数作为限流键
            if not RateLimiter.check_rate_limit(key, max_count, period):
                logger.warning(f'触发限流: {key}')
                return False
            return func(*args, **kwargs)
        return wrapper
    return decorator

def retry(max_retries: int = 3, delay: int = 1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f'发送通知失败，尝试重试 ({attempt + 1}/{max_retries}): {str(e)}')
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
            logger.error(f'发送通知失败，已达到最大重试次数: {str(last_error)}')
            return False
        return wrapper
    return decorator

@rate_limit(max_count=10, period=3600)  # 每小时最多10条通知
@retry(max_retries=3, delay=1)
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
        raise

@rate_limit(max_count=20, period=3600)  # 每小时最多20条通知
@retry(max_retries=3, delay=1)
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
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        logger.info(f'已发送Telegram通知至 {chat_id}')
        return True
        
    except Exception as e:
        logger.error(f'发送Telegram通知失败: {str(e)}')
        raise 