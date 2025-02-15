import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import and_
from ..models import db, AlertRule, AlertHistory, User, ExchangeAccount
from ..utils.octobot_api import OctoBotAPI
from ..utils.notification import send_email, send_telegram
from ..utils.indicators import calculate_rsi, calculate_macd, calculate_volatility
from ..utils.task_lock import task_lock
from ..utils.database import with_db_session, retry_on_db_error

logger = logging.getLogger(__name__)
octobot_api = OctoBotAPI()

@task_lock('alert_checker', timeout=300)  # 5分钟超时
@retry_on_db_error(max_retries=3)
def check_alerts():
    """检查所有活跃的预警规则，生成预警并发送通知"""
    try:
        # 批量获取所有活跃规则和相关用户信息
        rules_with_users = db.session.query(AlertRule, User).join(
            User, AlertRule.user_id == User.id
        ).filter(
            AlertRule.is_active == True
        ).all()
        
        # 获取所有活跃交易所账户
        active_accounts = {
            account.id: account for account in ExchangeAccount.query.filter_by(is_active=True).all()
        }
        
        for rule, user in rules_with_users:
            try:
                # 获取交易对列表
                symbols = [rule.symbol] if rule.symbol else get_account_symbols(active_accounts, user.id)
                
                # 批量获取K线数据
                klines_data = {}
                timeframe = rule.timeframe or '1h'
                for symbol in symbols:
                    klines = octobot_api.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=100
                    )
                    if klines:
                        klines_data[symbol] = pd.DataFrame(
                            klines,
                            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        )
                        klines_data[symbol]['timestamp'] = pd.to_datetime(
                            klines_data[symbol]['timestamp'],
                            unit='ms'
                        )
                
                # 批量处理预警
                process_alerts(rule, user, klines_data)
                
            except Exception as e:
                logger.error(f'处理预警规则 {rule.id} 时出错: {str(e)}')
                continue
                
    except Exception as e:
        logger.error(f'检查预警时出错: {str(e)}')

@with_db_session
def process_alerts(rule: AlertRule, user: User, klines_data: dict) -> None:
    """处理预警规则"""
    for symbol, df in klines_data.items():
        # 计算指标值
        value = calculate_indicator_value(rule.type, df)
        if value is None:
            continue
        
        # 检查是否触发预警
        if is_alert_triggered(rule, value):
            # 检查是否存在最近的相同预警
            if not has_recent_alert(rule.id, symbol):
                # 创建新预警
                create_alert(rule, user, symbol, value)

def get_account_symbols(accounts: dict, user_id: int) -> list:
    """获取用户的所有交易对"""
    symbols = set()
    for account in accounts.values():
        if account.user_id == user_id:
            symbols.update(account.trading_pairs.split(','))
    return list(symbols)

def calculate_indicator_value(indicator_type: str, df: pd.DataFrame) -> float:
    """计算技术指标值"""
    try:
        if indicator_type == 'price':
            return float(df['close'].iloc[-1])
        elif indicator_type == 'volume':
            return float(df['volume'].iloc[-1])
        elif indicator_type == 'volatility':
            return calculate_volatility(df['close'])
        elif indicator_type == 'drawdown':
            highest = df['close'].rolling(window=20).max()
            current = df['close'].iloc[-1]
            return (highest.iloc[-1] - current) / highest.iloc[-1] * 100
        elif indicator_type == 'rsi':
            return calculate_rsi(df['close'])[-1]
        elif indicator_type == 'macd':
            macd, signal, hist = calculate_macd(df['close'])
            return hist[-1]
        return None
    except Exception as e:
        logger.error(f'计算指标 {indicator_type} 失败: {str(e)}')
        return None

def is_alert_triggered(rule: AlertRule, value: float) -> bool:
    """检查是否触发预警条件"""
    if rule.condition == '>' and value > rule.threshold:
        return True
    elif rule.condition == '<' and value < rule.threshold:
        return True
    elif rule.condition == '>=' and value >= rule.threshold:
        return True
    elif rule.condition == '<=' and value <= rule.threshold:
        return True
    elif rule.condition == '==' and value == rule.threshold:
        return True
    elif rule.condition == 'between' and rule.threshold_secondary:
        min_val = min(rule.threshold, rule.threshold_secondary)
        max_val = max(rule.threshold, rule.threshold_secondary)
        return min_val <= value <= max_val
    return False

def has_recent_alert(rule_id: int, symbol: str) -> bool:
    """检查是否存在最近的相同预警"""
    return db.session.query(AlertHistory).filter(
        and_(
            AlertHistory.rule_id == rule_id,
            AlertHistory.symbol == symbol,
            AlertHistory.is_processed == False,
            AlertHistory.created_at >= datetime.utcnow() - timedelta(hours=1)
        )
    ).first() is not None

@with_db_session
def create_alert(rule: AlertRule, user: User, symbol: str, value: float) -> None:
    """创建新预警"""
    alert = AlertHistory(
        user_id=user.id,
        rule_id=rule.id,
        symbol=symbol,
        type=rule.type,
        level=get_alert_level(rule.type, value, rule.threshold),
        title=f'{symbol} {rule.name}预警',
        message=generate_alert_message(rule, symbol, value),
        value=value,
        is_read=False,
        is_processed=False
    )
    
    db.session.add(alert)
    db.session.flush()  # 获取alert.id
    
    # 发送通知
    try:
        if rule.notify_email and user.email:
            send_email(
                to=user.email,
                subject=alert.title,
                body=alert.message
            )
        
        if rule.notify_telegram and user.telegram_chat_id:
            send_telegram(
                chat_id=user.telegram_chat_id,
                message=f'*{alert.title}*\n{alert.message}'
            )
    except Exception as e:
        logger.error(f'发送预警通知失败: {str(e)}')

def get_alert_level(rule_type, value, threshold):
    """
    根据规则类型和触发值确定预警级别
    """
    if rule_type == 'drawdown':
        if value >= 20:
            return 'danger'
        elif value >= 10:
            return 'warning'
        else:
            return 'info'
    elif rule_type == 'volatility':
        if value >= 0.1:  # 10%
            return 'danger'
        elif value >= 0.05:  # 5%
            return 'warning'
        else:
            return 'info'
    elif rule_type == 'rsi':
        if value >= 80 or value <= 20:
            return 'danger'
        elif value >= 70 or value <= 30:
            return 'warning'
        else:
            return 'info'
    else:
        return 'info'

def generate_alert_message(rule, symbol, value):
    """
    生成预警消息
    """
    type_names = {
        'price': '价格',
        'volume': '成交量',
        'volatility': '波动率',
        'drawdown': '回撤',
        'rsi': 'RSI',
        'macd': 'MACD'
    }
    
    condition_names = {
        '>': '大于',
        '<': '小于',
        '>=': '大于等于',
        '<=': '小于等于',
        '==': '等于',
        'between': '介于'
    }
    
    type_name = type_names.get(rule.type, rule.type)
    condition_name = condition_names.get(rule.condition, rule.condition)
    
    if rule.condition == 'between' and rule.threshold_secondary:
        threshold_desc = f'{min(rule.threshold, rule.threshold_secondary)} 和 {max(rule.threshold, rule.threshold_secondary)} 之间'
    else:
        threshold_desc = str(rule.threshold)
    
    return (
        f'交易对 {symbol} 的{type_name}指标\n'
        f'当前值: {value:.4f}\n'
        f'触发条件: {condition_name} {threshold_desc}\n'
        f'规则描述: {rule.description}'
    ) 