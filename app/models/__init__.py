from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class ExchangeAccount(db.Model):
    __tablename__ = 'exchange_accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exchange = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Strategy(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exchange_account_id = db.Column(db.Integer, db.ForeignKey('exchange_accounts.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'))
    symbol = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    order_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class RiskConfig(db.Model):
    __tablename__ = 'risk_configs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)  # 'GLOBAL' 表示全局设置
    max_position = db.Column(db.Float, nullable=False)  # 最大持仓金额
    stop_loss = db.Column(db.Float, nullable=False)    # 止损比例
    take_profit = db.Column(db.Float, nullable=False)  # 止盈比例
    max_trades_per_day = db.Column(db.Integer, nullable=False)  # 每日最大交易次数
    max_leverage = db.Column(db.Float, default=1.0)    # 最大杠杆倍数
    max_drawdown = db.Column(db.Float, default=50.0)   # 最大回撤限制
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class AlertRule(db.Model):
    __tablename__ = 'alert_rules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    symbol = db.Column(db.String(20))  # 为空表示适用于所有交易对
    type = db.Column(db.String(50), nullable=False)  # price, volume, volatility, drawdown, etc.
    condition = db.Column(db.String(20), nullable=False)  # >, <, >=, <=, ==, between
    threshold = db.Column(db.Float, nullable=False)
    threshold_secondary = db.Column(db.Float)  # 用于between条件的第二个阈值
    timeframe = db.Column(db.String(20))  # 1m, 5m, 15m, 1h, etc.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notify_email = db.Column(db.Boolean, default=True)
    notify_telegram = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class AlertHistory(db.Model):
    __tablename__ = 'alert_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('alert_rules.id'))
    symbol = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # info, warning, danger
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float)  # 触发预警时的具体数值
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    is_processed = db.Column(db.Boolean, nullable=False, default=False)
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) 