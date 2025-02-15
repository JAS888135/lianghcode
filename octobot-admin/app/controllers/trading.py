from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from ..models import db, Trade, ExchangeAccount, Strategy, RiskConfig
from ..utils.octobot_api import OctoBotAPI
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
trading = Blueprint('trading', __name__)
octobot_api = OctoBotAPI()

@trading.route('/trading/manual')
@login_required
def manual():
    # 获取用户的交易账户
    exchange_accounts = ExchangeAccount.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    # 获取交易对配置
    from flask import current_app
    trading_pairs = current_app.config['SUPPORTED_TRADING_PAIRS']
    
    return render_template('trading/manual.html',
                         exchange_accounts=exchange_accounts,
                         trading_pairs=trading_pairs)

@trading.route('/trading/auto')
@login_required
def auto():
    # 获取用户的策略
    strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    
    # 获取运行中的策略状态
    active_strategies = []
    for strategy in strategies:
        status = octobot_api.get_strategy_status(strategy.id)
        if status and status['status'] == 'active':
            active_strategies.append({
                'id': strategy.id,
                'name': strategy.name,
                'type': strategy.type,
                'status': status
            })
    
    return render_template('trading/auto.html',
                         strategies=strategies,
                         active_strategies=active_strategies)

@trading.route('/trading/orders')
@login_required
def orders():
    # 获取所有订单
    trades = Trade.query.filter_by(user_id=current_user.id)\
        .order_by(Trade.created_at.desc())\
        .limit(100)\
        .all()
    
    return render_template('trading/orders.html', trades=trades)

@trading.route('/trading/history')
@login_required
def history():
    # 获取历史交易记录
    trades = Trade.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(Trade.created_at.desc()).all()
    
    return render_template('trading/history.html', trades=trades)

@trading.route('/api/trading/place-order', methods=['POST'])
@login_required
def place_order():
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['exchange_account_id', 'symbol', 'side', 'type', 'amount']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400
        
        # 获取交易账户
        account = ExchangeAccount.query.filter_by(
            id=data['exchange_account_id'],
            user_id=current_user.id
        ).first()
        
        if not account:
            return jsonify({
                'status': 'error',
                'message': '交易账户不存在'
            }), 404
        
        # 检查风险控制
        risk_config = RiskConfig.query.filter_by(
            user_id=current_user.id,
            exchange_account_id=account.id,
            symbol=data['symbol']
        ).first()
        
        if risk_config:
            # 检查持仓限制
            if data['amount'] > risk_config.max_position:
                return jsonify({
                    'status': 'error',
                    'message': f'交易数量超过最大持仓限制 ({risk_config.max_position})'
                }), 400
            
            # 检查每日交易次数
            today = datetime.utcnow().date()
            today_trades = Trade.query.filter(
                Trade.user_id == current_user.id,
                Trade.exchange_account_id == account.id,
                Trade.symbol == data['symbol'],
                Trade.created_at >= today
            ).count()
            
            if today_trades >= risk_config.max_trades_per_day:
                return jsonify({
                    'status': 'error',
                    'message': f'已达到每日最大交易次数限制 ({risk_config.max_trades_per_day})'
                }), 400
        
        # 准备订单数据
        order_data = {
            'exchange_id': account.id,
            'symbol': data['symbol'],
            'type': data['type'],
            'side': data['side'],
            'amount': float(data['amount'])
        }
        
        # 如果是限价单，添加价格
        if data['type'] == 'limit' and 'price' in data:
            order_data['price'] = float(data['price'])
        
        # 如果设置了止损止盈
        if 'stop_loss' in data:
            order_data['stop_loss'] = float(data['stop_loss'])
        if 'take_profit' in data:
            order_data['take_profit'] = float(data['take_profit'])
        
        # 发送订单到OctoBot
        response = octobot_api.place_order(order_data)
        
        if not response or 'error' in response:
            raise Exception(response.get('error', '下单失败'))
        
        # 创建交易记录
        trade = Trade(
            user_id=current_user.id,
            exchange_account_id=account.id,
            symbol=data['symbol'],
            type=data['type'],
            side=data['side'],
            amount=data['amount'],
            price=data.get('price', response.get('price', 0)),
            status='pending',
            order_id=response.get('order_id')
        )
        
        db.session.add(trade)
        db.session.commit()
        
        logger.info(f'用户 {current_user.username} 成功下单: {trade.symbol} {trade.side} {trade.amount}')
        
        return jsonify({
            'status': 'success',
            'message': '订单已提交',
            'data': {
                'trade_id': trade.id,
                'order_id': trade.order_id
            }
        })
        
    except Exception as e:
        logger.error(f'下单失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading.route('/api/trading/cancel-order', methods=['POST'])
@login_required
def cancel_order():
    try:
        data = request.get_json()
        
        if 'trade_id' not in data:
            return jsonify({
                'status': 'error',
                'message': '缺少交易ID'
            }), 400
        
        # 获取交易记录
        trade = Trade.query.filter_by(
            id=data['trade_id'],
            user_id=current_user.id
        ).first()
        
        if not trade:
            return jsonify({
                'status': 'error',
                'message': '交易记录不存在'
            }), 404
        
        if trade.status != 'pending':
            return jsonify({
                'status': 'error',
                'message': '只能取消待处理的订单'
            }), 400
        
        # 发送取消请求到OctoBot
        response = octobot_api.cancel_order(trade.order_id)
        
        if not response or 'error' in response:
            raise Exception(response.get('error', '取消订单失败'))
        
        # 更新交易状态
        trade.status = 'cancelled'
        db.session.commit()
        
        logger.info(f'用户 {current_user.username} 取消订单: {trade.id}')
        
        return jsonify({
            'status': 'success',
            'message': '订单已取消'
        })
        
    except Exception as e:
        logger.error(f'取消订单失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading.route('/api/trading/order-status/<int:trade_id>')
@login_required
def get_order_status(trade_id):
    try:
        # 获取交易记录
        trade = Trade.query.filter_by(
            id=trade_id,
            user_id=current_user.id
        ).first()
        
        if not trade:
            return jsonify({
                'status': 'error',
                'message': '交易记录不存在'
            }), 404
        
        # 获取订单状态
        if trade.order_id:
            status = octobot_api.get_orders(trade.order_id)
            if status:
                return jsonify({
                    'status': 'success',
                    'data': status
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'status': trade.status
            }
        })
        
    except Exception as e:
        logger.error(f'获取订单状态失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@trading.route('/api/trading/market-info/<symbol>')
@login_required
def get_market_info(symbol):
    try:
        # 获取市场数据
        market_data = octobot_api.get_price(symbol)
        
        if not market_data:
            return jsonify({
                'status': 'error',
                'message': '获取市场数据失败'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': market_data
        })
        
    except Exception as e:
        logger.error(f'获取市场数据失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 