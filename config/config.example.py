import os
from datetime import timedelta

class Config:
    # 基本配置
    SECRET_KEY = 'your-secret-key-here'  # 请修改为随机字符串
    SQLALCHEMY_DATABASE_URI = 'sqlite:///user/data.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'max_overflow': 5,
        'connect_args': {
            'connect_timeout': 10,
            'timeout': 30
        }
    }
    
    # 数据库重试配置
    DB_MAX_RETRIES = 3
    DB_RETRY_DELAY = 1  # 秒
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_TYPE = 'filesystem'
    
    # OctoBot配置
    OCTOBOT_URL = 'http://localhost:5001'
    
    # 邮件配置
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'your-email@gmail.com'
    SMTP_PASSWORD = 'your-app-password'
    MAIL_SENDER = 'OctoBot Alert <your-email@gmail.com>'
    
    # Telegram配置
    TELEGRAM_BOT_TOKEN = 'your-bot-token'
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'logs/app.log'
    
    # 预警检查配置
    ALERT_CHECK_INTERVAL = 60  # 秒
    MAX_ALERTS_PER_HOUR = 10
    ALERT_COOLDOWN = 3600  # 秒

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 