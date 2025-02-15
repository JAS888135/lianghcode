from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from ..models import db, Strategy, Trade, ExchangeAccount
from ..utils.octobot_api import OctoBotAPI
import logging

logger = logging.getLogger(__name__)
strategy = Blueprint('strategy', __name__)
octobot_api = OctoBotAPI()

@strategy.route('/strategy/list')
@login_required
def list():
    # 获取用户的所有策略
    strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    
    # 获取每个策略的状态和性能数据
    strategy_data = []
    for strat in strategies:
        status = octobot_api.get_strategy_status(strat.id)
        if status:
            strategy_data.append({
                'id': strat.id,
                'name': strat.name,
                'type': strat.type,
                'status': status['status'],
                'performance': status.get('performance', {})
            })
    
    return render_template('strategy/list.html', strategies=strategy_data)

@strategy.route('/strategy/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # 验证必要字段
            required_fields = ['name', 'type', 'config']
            if not all(field in data for field in required_fields):
                return jsonify({
                    'status': 'error',
                    'message': '缺少必要的参数'
                }), 400
            
            # 创建新策略
            new_strategy = Strategy(
                user_id=current_user.id,
                name=data['name'],
                type=data['type'],
                config=data['config']
            )
            
            db.session.add(new_strategy)
            db.session.commit()
            
            logger.info(f'用户 {current_user.username} 创建新策略: {new_strategy.name}')
            
            return jsonify({
                'status': 'success',
                'message': '策略创建成功',
                'data': {
                    'strategy_id': new_strategy.id
                }
            })
            
        except Exception as e:
            logger.error(f'创建策略失败: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # GET请求返回创建页面
    return render_template('strategy/create.html')

@strategy.route('/strategy/<int:strategy_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_strategy(strategy_id):
    # 获取策略
    strat = Strategy.query.filter_by(
        id=strategy_id,
        user_id=current_user.id
    ).first()
    
    if not strat:
        return jsonify({
            'status': 'error',
            'message': '策略不存在'
        }), 404
    
    if request.method == 'GET':
        # 获取策略详情
        status = octobot_api.get_strategy_status(strat.id)
        return render_template('strategy/detail.html',
                             strategy=strat,
                             status=status)
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # 更新策略配置
            if 'name' in data:
                strat.name = data['name']
            if 'config' in data:
                strat.config = data['config']
            
            db.session.commit()
            
            logger.info(f'用户 {current_user.username} 更新策略: {strat.name}')
            
            return jsonify({
                'status': 'success',
                'message': '策略更新成功'
            })
            
        except Exception as e:
            logger.error(f'更新策略失败: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    elif request.method == 'DELETE':
        try:
            # 检查策略是否在运行
            status = octobot_api.get_strategy_status(strat.id)
            if status and status['status'] == 'active':
                return jsonify({
                    'status': 'error',
                    'message': '请先停止策略再删除'
                }), 400
            
            db.session.delete(strat)
            db.session.commit()
            
            logger.info(f'用户 {current_user.username} 删除策略: {strat.name}')
            
            return jsonify({
                'status': 'success',
                'message': '策略已删除'
            })
            
        except Exception as e:
            logger.error(f'删除策略失败: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

@strategy.route('/strategy/<int:strategy_id>/start', methods=['POST'])
@login_required
def start_strategy(strategy_id):
    try:
        # 获取策略
        strat = Strategy.query.filter_by(
            id=strategy_id,
            user_id=current_user.id
        ).first()
        
        if not strat:
            return jsonify({
                'status': 'error',
                'message': '策略不存在'
            }), 404
        
        # 启动策略
        response = octobot_api.start_strategy({
            'strategy_id': strat.id,
            'config': strat.config
        })
        
        if not response or 'error' in response:
            raise Exception(response.get('error', '启动策略失败'))
        
        logger.info(f'用户 {current_user.username} 启动策略: {strat.name}')
        
        return jsonify({
            'status': 'success',
            'message': '策略已启动'
        })
        
    except Exception as e:
        logger.error(f'启动策略失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@strategy.route('/strategy/<int:strategy_id>/stop', methods=['POST'])
@login_required
def stop_strategy(strategy_id):
    try:
        # 获取策略
        strat = Strategy.query.filter_by(
            id=strategy_id,
            user_id=current_user.id
        ).first()
        
        if not strat:
            return jsonify({
                'status': 'error',
                'message': '策略不存在'
            }), 404
        
        # 停止策略
        response = octobot_api.stop_strategy(strat.id)
        
        if not response or 'error' in response:
            raise Exception(response.get('error', '停止策略失败'))
        
        logger.info(f'用户 {current_user.username} 停止策略: {strat.name}')
        
        return jsonify({
            'status': 'success',
            'message': '策略已停止'
        })
        
    except Exception as e:
        logger.error(f'停止策略失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@strategy.route('/strategy/backtest', methods=['GET', 'POST'])
@login_required
def backtest():
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # 验证必要字段
            required_fields = ['strategy_id', 'start_date', 'end_date', 'timeframe']
            if not all(field in data for field in required_fields):
                return jsonify({
                    'status': 'error',
                    'message': '缺少必要的参数'
                }), 400
            
            # 获取策略
            strat = Strategy.query.filter_by(
                id=data['strategy_id'],
                user_id=current_user.id
            ).first()
            
            if not strat:
                return jsonify({
                    'status': 'error',
                    'message': '策略不存在'
                }), 404
            
            # 开始回测
            response = octobot_api.start_backtesting({
                'strategy_id': strat.id,
                'config': strat.config,
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'timeframe': data['timeframe']
            })
            
            if not response or 'error' in response:
                raise Exception(response.get('error', '启动回测失败'))
            
            return jsonify({
                'status': 'success',
                'message': '回测已启动',
                'data': {
                    'backtest_id': response['backtest_id']
                }
            })
            
        except Exception as e:
            logger.error(f'启动回测失败: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # GET请求返回回测页面
    strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    return render_template('strategy/backtest.html', strategies=strategies)

@strategy.route('/strategy/backtest/<backtest_id>/status')
@login_required
def get_backtest_status(backtest_id):
    try:
        # 获取回测状态
        status = octobot_api.get_backtesting_status(backtest_id)
        
        if not status:
            return jsonify({
                'status': 'error',
                'message': '获取回测状态失败'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        logger.error(f'获取回测状态失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@strategy.route('/strategy/optimize', methods=['GET', 'POST'])
@login_required
def optimize():
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # 验证必要字段
            required_fields = ['strategy_id', 'parameters', 'optimization_method']
            if not all(field in data for field in required_fields):
                return jsonify({
                    'status': 'error',
                    'message': '缺少必要的参数'
                }), 400
            
            # 获取策略
            strat = Strategy.query.filter_by(
                id=data['strategy_id'],
                user_id=current_user.id
            ).first()
            
            if not strat:
                return jsonify({
                    'status': 'error',
                    'message': '策略不存在'
                }), 404
            
            # TODO: 实现策略优化功能
            return jsonify({
                'status': 'error',
                'message': '策略优化功能即将推出'
            }), 501
            
        except Exception as e:
            logger.error(f'启动策略优化失败: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # GET请求返回优化页面
    strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    return render_template('strategy/optimize.html', strategies=strategies) 