import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import and_
from ..models import db, AlertRule, AlertHistory, User, ExchangeAccount
from ..utils.octobot_api import OctoBotAPI
from ..utils.notification import send_email, send_telegram
from ..utils.indicators import calculate_rsi, calculate_macd, calculate_volatility

logger = logging.getLogger(__name__)
octobot_api = OctoBotAPI()

def check_alerts():
    """
    检查所有活跃的预警规则，生成预警并发送通知
    """
    try:
        # 获取所有活跃的预警规则
        active_rules = AlertRule.query.filter_by(is_active=True).all()
        
        for rule in active_rules:
            try:
                # 获取用户信息
                user = User.query.get(rule.user_id)
                if not user:
                    logger.error(f'预警规则 {rule.id} 的用户不存在')
                    continue
                
                # 获取交易对数据
                if rule.symbol:
                    symbols = [rule.symbol]
                else:
                    # 如果未指定交易对，获取用户所有活跃的交易对
                    accounts = ExchangeAccount.query.filter_by(user_id=user.id, is_active=True).all()
                    symbols = []
                    for account in accounts:
                        symbols.extend(account.trading_pairs.split(','))
                    symbols = list(set(symbols))  # 去重
                
                for symbol in symbols:
                    # 获取K线数据
                    timeframe = rule.timeframe or '1h'  # 默认1小时
                    klines = octobot_api.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=100  # 获取足够的数据用于计算指标
                    )
                    
                    if not klines:
                        logger.warning(f'无法获取交易对 {symbol} 的K线数据')
                        continue
                    
                    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    # 根据规则类型计算指标
                    value = None
                    if rule.type == 'price':
                        value = float(df['close'].iloc[-1])
                    elif rule.type == 'volume':
                        value = float(df['volume'].iloc[-1])
                    elif rule.type == 'volatility':
                        value = calculate_volatility(df['close'])
                    elif rule.type == 'drawdown':
                        highest = df['close'].rolling(window=20).max()
                        current = df['close'].iloc[-1]
                        value = (highest.iloc[-1] - current) / highest.iloc[-1] * 100
                    elif rule.type == 'rsi':
                        value = calculate_rsi(df['close'])[-1]
                    elif rule.type == 'macd':
                        macd, signal, hist = calculate_macd(df['close'])
                        value = hist[-1]
                    
                    if value is None:
                        logger.warning(f'无法计算交易对 {symbol} 的 {rule.type} 指标')
                        continue
                    
                    # 检查是否触发预警条件
                    is_triggered = False
                    if rule.condition == '>' and value > rule.threshold:
                        is_triggered = True
                    elif rule.condition == '<' and value < rule.threshold:
                        is_triggered = True
                    elif rule.condition == '>=' and value >= rule.threshold:
                        is_triggered = True
                    elif rule.condition == '<=' and value <= rule.threshold:
                        is_triggered = True
                    elif rule.condition == '==' and value == rule.threshold:
                        is_triggered = True
                    elif rule.condition == 'between' and rule.threshold_secondary and \
                         value >= min(rule.threshold, rule.threshold_secondary) and \
                         value <= max(rule.threshold, rule.threshold_secondary):
                        is_triggered = True
                    
                    if is_triggered:
                        # 检查是否已经存在相同的未处理预警
                        recent_alert = AlertHistory.query.filter(
                            and_(
                                AlertHistory.rule_id == rule.id,
                                AlertHistory.symbol == symbol,
                                AlertHistory.is_processed == False,
                                AlertHistory.created_at >= datetime.utcnow() - timedelta(hours=1)
                            )
                        ).first()
                        
                        if not recent_alert:
                            # 创建新的预警记录
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
                            db.session.commit()
                            
                            # 发送通知
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
                            
                            logger.info(f'已为用户 {user.username} 创建预警: {alert.title}')
                
            except Exception as e:
                logger.error(f'处理预警规则 {rule.id} 时出错: {str(e)}')
                continue
                
    except Exception as e:
        logger.error(f'检查预警时出错: {str(e)}')

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