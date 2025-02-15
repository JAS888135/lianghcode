from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default='user', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # 关系定义
    exchange_accounts = db.relationship('ExchangeAccount', backref='user', lazy=True, cascade='all, delete-orphan')
    strategies = db.relationship('Strategy', backref='user', lazy=True, cascade='all, delete-orphan')
    trades = db.relationship('Trade', backref='user', lazy=True, cascade='all, delete-orphan')
    risk_configs = db.relationship('RiskConfig', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    alert_rules = db.relationship('AlertRule', backref='user', lazy=True, cascade='all, delete-orphan')
    alert_history = db.relationship('AlertHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    telegram_config = db.relationship('TelegramConfig', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')

class ExchangeAccount(db.Model):
    __tablename__ = 'exchange_accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    exchange = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # 关系定义
    trades = db.relationship('Trade', backref='exchange_account', lazy=True, cascade='all, delete-orphan')
    risk_configs = db.relationship('RiskConfig', backref='exchange_account', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_exchange_account_user_exchange', 'user_id', 'exchange'),
    )

class Strategy(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    config = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # 关系定义
    trades = db.relationship('Trade', backref='strategy', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_strategy_user_type', 'user_id', 'type'),
    )

class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    exchange_account_id = db.Column(db.Integer, db.ForeignKey('exchange_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id', ondelete='SET NULL'), index=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False, index=True)
    side = db.Column(db.String(10), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)
    order_id = db.Column(db.String(100), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_trade_user_symbol', 'user_id', 'symbol'),
        db.Index('idx_trade_user_status', 'user_id', 'status'),
    )

class RiskConfig(db.Model):
    __tablename__ = 'risk_configs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    exchange_account_id = db.Column(db.Integer, db.ForeignKey('exchange_accounts.id', ondelete='CASCADE'), nullable=True, index=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    max_position = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)
    take_profit = db.Column(db.Float, nullable=False)
    max_trades_per_day = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_risk_config_user_symbol', 'user_id', 'symbol'),
        db.Index('idx_risk_config_account_symbol', 'exchange_account_id', 'symbol'),
    )

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_notification_user_type', 'user_id', 'type'),
        db.Index('idx_notification_user_read', 'user_id', 'is_read'),
    )

class AlertRule(db.Model):
    __tablename__ = 'alert_rules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    symbol = db.Column(db.String(20), index=True)
    condition = db.Column(db.String(20), nullable=False, index=True)
    threshold = db.Column(db.Float, nullable=False)
    threshold_secondary = db.Column(db.Float)
    timeframe = db.Column(db.String(10), index=True)
    description = db.Column(db.Text)
    notify_email = db.Column(db.Boolean, nullable=False, default=True)
    notify_telegram = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # 关系定义
    alert_history = db.relationship('AlertHistory', backref='rule', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_alert_rule_user_type', 'user_id', 'type'),
        db.Index('idx_alert_rule_user_symbol', 'user_id', 'symbol'),
    )

class AlertHistory(db.Model):
    __tablename__ = 'alert_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('alert_rules.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    is_processed = db.Column(db.Boolean, nullable=False, default=False, index=True)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_alert_history_user_type', 'user_id', 'type'),
        db.Index('idx_alert_history_user_level', 'user_id', 'level'),
        db.Index('idx_alert_history_user_processed', 'user_id', 'is_processed'),
    )

class TelegramConfig(db.Model):
    __tablename__ = 'telegram_configs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    chat_id = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    notification_types = db.Column(db.JSON, nullable=False, default=lambda: {
        'trade': True,
        'alert': True,
        'system': True,
        'performance': True
    })
    quiet_hours_start = db.Column(db.Integer)  # 0-23
    quiet_hours_end = db.Column(db.Integer)    # 0-23
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_telegram_config_user_active', 'user_id', 'is_active'),
    ) 