import os
from datetime import timedelta

class Config:
    # 基本配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///user/data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_TYPE = 'filesystem'
    
    # OctoBot配置
    OCTOBOT_URL = os.getenv('OCTOBOT_URL', 'http://localhost:5001')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'logs/app.log'
    
    # 交易所配置
    SUPPORTED_EXCHANGES = [
        'binance',  # 币安
        'huobi',    # 火币
        'okx',      # OKX
        'bybit',    # Bybit
        'gate',     # Gate.io
        'kucoin',   # KuCoin
        'mexc'      # MEXC
    ]
    
    # 交易对配置
    SUPPORTED_TRADING_PAIRS = {
        'USDT': [
            'BTC/USDT',
            'ETH/USDT',
            'BNB/USDT',
            'SOL/USDT',
            'XRP/USDT',
            'ADA/USDT',
            'DOGE/USDT'
        ],
        'USDC': [
            'BTC/USDC',
            'ETH/USDC'
        ],
        'BTC': [
            'ETH/BTC',
            'BNB/BTC'
        ]
    }
    
    # 策略配置
    STRATEGY_TYPES = [
        'grid',      # 网格交易
        'dca',       # 定投策略
        'trend',     # 趋势跟踪
        'arbitrage', # 套利策略
        'signal'     # 信号策略
    ]
    
    # 风险控制配置
    DEFAULT_RISK_CONFIG = {
        'stop_loss': 5.0,        # 止损比例
        'take_profit': 10.0,     # 止盈比例
        'max_position': 1.0,     # 最大持仓量
        'max_trades_per_day': 10 # 每日最大交易次数
    }
    
    # 通知配置
    NOTIFICATION_TYPES = [
        'trade',     # 交易通知
        'risk',      # 风险提醒
        'system',    # 系统通知
        'strategy'   # 策略通知
    ]
    
    # 回测配置
    BACKTESTING_CONFIG = {
        'timeframes': ['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
        'max_candles': 10000,
        'default_timeframe': '1h'
    }
    
    # 性能监控配置
    PERFORMANCE_CONFIG = {
        'update_interval': 60,  # 更新间隔（秒）
        'max_points': 1000,     # 最大数据点数
        'metrics': [
            'cpu_usage',
            'memory_usage',
            'disk_usage',
            'network_traffic'
        ]
    }

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # 生产环境特定配置
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