from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from ..models import Trade, ExchangeAccount, Strategy
from ..utils.octobot_api import OctoBotAPI
from sqlalchemy import func
import pandas as pd
from datetime import datetime, timedelta

dashboard = Blueprint('dashboard', __name__)
octobot_api = OctoBotAPI()

@dashboard.route('/dashboard')
@login_required
def index():
    # 获取用户的交易账户
    exchange_accounts = ExchangeAccount.query.filter_by(user_id=current_user.id).all()
    
    # 获取用户的策略
    strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    
    # 获取最近的交易记录
    recent_trades = Trade.query.filter_by(user_id=current_user.id)\
        .order_by(Trade.created_at.desc())\
        .limit(10)\
        .all()
    
    # 获取交易统计数据
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    trade_stats = {
        'total_trades': Trade.query.filter_by(user_id=current_user.id).count(),
        'today_trades': Trade.query.filter_by(user_id=current_user.id)\
            .filter(Trade.created_at >= today_start)\
            .count(),
        'successful_trades': Trade.query.filter_by(user_id=current_user.id, status='completed').count(),
        'failed_trades': Trade.query.filter_by(user_id=current_user.id, status='failed').count()
    }
    
    # 计算成功率
    if trade_stats['total_trades'] > 0:
        trade_stats['success_rate'] = (trade_stats['successful_trades'] / trade_stats['total_trades']) * 100
    else:
        trade_stats['success_rate'] = 0
    
    return render_template('dashboard/index.html',
                         exchange_accounts=exchange_accounts,
                         strategies=strategies,
                         recent_trades=recent_trades,
                         trade_stats=trade_stats)

@dashboard.route('/api/dashboard/portfolio')
@login_required
def get_portfolio():
    try:
        # 获取所有交易账户的资产组合
        portfolio_data = []
        exchange_accounts = ExchangeAccount.query.filter_by(user_id=current_user.id).all()
        
        total_value = 0
        for account in exchange_accounts:
            account_portfolio = octobot_api.get_portfolio(account.id)
            if account_portfolio:
                portfolio_data.extend(account_portfolio['assets'])
                total_value += account_portfolio['total_value']
        
        # 合并相同资产的数据
        df = pd.DataFrame(portfolio_data)
        if not df.empty:
            df = df.groupby('symbol').agg({
                'amount': 'sum',
                'value': 'sum',
                'change_24h': 'mean'
            }).reset_index()
            
            portfolio_data = df.to_dict('records')
        
        return jsonify({
            'status': 'success',
            'data': {
                'assets': portfolio_data,
                'total_value': total_value
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard.route('/api/dashboard/trade-history')
@login_required
def get_trade_history():
    try:
        # 获取最近 7 天的交易历史
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        trades = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.created_at >= start_date,
            Trade.created_at <= end_date
        ).all()
        
        # 将交易数据转换为DataFrame进行分析
        trade_data = [{
            'timestamp': trade.created_at,
            'symbol': trade.symbol,
            'side': trade.side,
            'amount': float(trade.amount),
            'price': float(trade.price),
            'value': float(trade.amount) * float(trade.price),
            'status': trade.status
        } for trade in trades]
        
        df = pd.DataFrame(trade_data)
        if not df.empty:
            # 按日期分组计算每日交易统计
            df['date'] = df['timestamp'].dt.date
            daily_stats = df.groupby('date').agg({
                'value': 'sum',
                'timestamp': 'count'
            }).rename(columns={'timestamp': 'count'})
            
            # 计算盈亏
            profit_loss = df[df['status'] == 'completed'].groupby('date')['value'].sum()
            
            # 合并统计数据
            result = {
                'dates': daily_stats.index.strftime('%Y-%m-%d').tolist(),
                'trade_counts': daily_stats['count'].tolist(),
                'trade_volumes': daily_stats['value'].round(2).tolist(),
                'profit_loss': profit_loss.round(2).tolist() if not profit_loss.empty else []
            }
        else:
            result = {
                'dates': [],
                'trade_counts': [],
                'trade_volumes': [],
                'profit_loss': []
            }
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard.route('/api/dashboard/strategy-performance')
@login_required
def get_strategy_performance():
    try:
        strategies = Strategy.query.filter_by(user_id=current_user.id).all()
        
        performance_data = []
        for strategy in strategies:
            # 获取策略的性能指标
            status = octobot_api.get_strategy_status(strategy.id)
            if status:
                performance = {
                    'id': strategy.id,
                    'name': strategy.name,
                    'type': strategy.type,
                    'status': status['status'],
                    'total_trades': status['total_trades'],
                    'win_rate': status['win_rate'],
                    'profit_loss': status['profit_loss'],
                    'sharpe_ratio': status['sharpe_ratio'],
                    'max_drawdown': status['max_drawdown']
                }
                performance_data.append(performance)
        
        return jsonify({
            'status': 'success',
            'data': performance_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard.route('/api/dashboard/market-overview')
@login_required
def get_market_overview():
    try:
        # 获取用户交易的所有交易对的市场数据
        symbols = Trade.query.with_entities(Trade.symbol)\
            .filter_by(user_id=current_user.id)\
            .distinct()\
            .all()
        
        market_data = []
        for symbol in symbols:
            price_data = octobot_api.get_price(symbol[0])
            if price_data:
                market_data.append({
                    'symbol': symbol[0],
                    'price': price_data['price'],
                    'change_24h': price_data['change_24h'],
                    'volume_24h': price_data['volume_24h'],
                    'high_24h': price_data['high_24h'],
                    'low_24h': price_data['low_24h']
                })
        
        return jsonify({
            'status': 'success',
            'data': market_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 