from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from ..models import db, RiskConfig, Trade, ExchangeAccount, AlertRule, AlertHistory
from ..utils.octobot_api import OctoBotAPI
import logging
from datetime import datetime, timedelta
import pandas as pd
import json
import io
import csv

logger = logging.getLogger(__name__)
risk = Blueprint('risk', __name__)
octobot_api = OctoBotAPI()

@risk.route('/risk/settings')
@login_required
def settings():
    # 获取全局风险设置
    global_risk = RiskConfig.query.filter_by(
        user_id=current_user.id,
        symbol='GLOBAL'
    ).first()
    
    if not global_risk:
        # 创建默认全局风险设置
        global_risk = RiskConfig(
            user_id=current_user.id,
            symbol='GLOBAL',
            max_position=10000,  # 默认最大持仓10000 USDT
            stop_loss=5,         # 默认止损5%
            take_profit=10,      # 默认止盈10%
            max_trades_per_day=10 # 默认每日最大交易次数
        )
        db.session.add(global_risk)
        db.session.commit()
    
    # 获取交易对风险设置
    pair_risks = RiskConfig.query.filter(
        RiskConfig.user_id == current_user.id,
        RiskConfig.symbol != 'GLOBAL'
    ).all()
    
    # 获取支持的交易对
    from flask import current_app
    trading_pairs = []
    for quote_currency, pairs in current_app.config['SUPPORTED_TRADING_PAIRS'].items():
        trading_pairs.extend(pairs)
    
    return render_template('risk/settings.html',
                         global_risk=global_risk,
                         pair_risks=pair_risks,
                         trading_pairs=trading_pairs)

@risk.route('/api/risk/global', methods=['POST'])
@login_required
def update_global_risk():
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = [
            'max_position_value',
            'max_trades_per_day',
            'max_leverage',
            'global_stop_loss',
            'global_take_profit',
            'max_drawdown'
        ]
        
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400
        
        # 更新或创建全局风险设置
        global_risk = RiskConfig.query.filter_by(
            user_id=current_user.id,
            symbol='GLOBAL'
        ).first()
        
        if not global_risk:
            global_risk = RiskConfig(
                user_id=current_user.id,
                symbol='GLOBAL'
            )
            db.session.add(global_risk)
        
        # 更新设置
        global_risk.max_position = data['max_position_value']
        global_risk.max_trades_per_day = data['max_trades_per_day']
        global_risk.max_leverage = data['max_leverage']
        global_risk.stop_loss = data['global_stop_loss']
        global_risk.take_profit = data['global_take_profit']
        global_risk.max_drawdown = data['max_drawdown']
        
        db.session.commit()
        logger.info(f'用户 {current_user.username} 更新了全局风险设置')
        
        return jsonify({
            'status': 'success',
            'message': '全局风险设置已更新'
        })
        
    except Exception as e:
        logger.error(f'更新全局风险设置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/pair', methods=['POST'])
@login_required
def update_pair_risk():
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['symbol', 'max_position', 'stop_loss', 'take_profit']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400
        
        # 更新或创建交易对风险设置
        pair_risk = RiskConfig.query.filter_by(
            user_id=current_user.id,
            symbol=data['symbol']
        ).first()
        
        if not pair_risk:
            pair_risk = RiskConfig(
                user_id=current_user.id,
                symbol=data['symbol']
            )
            db.session.add(pair_risk)
        
        # 更新设置
        pair_risk.max_position = data['max_position']
        pair_risk.stop_loss = data['stop_loss']
        pair_risk.take_profit = data['take_profit']
        
        db.session.commit()
        logger.info(f'用户 {current_user.username} 更新了 {data["symbol"]} 的风险设置')
        
        return jsonify({
            'status': 'success',
            'message': '交易对风险设置已更新'
        })
        
    except Exception as e:
        logger.error(f'更新交易对风险设置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/pair/<symbol>', methods=['GET'])
@login_required
def get_pair_risk(symbol):
    try:
        pair_risk = RiskConfig.query.filter_by(
            user_id=current_user.id,
            symbol=symbol
        ).first()
        
        if not pair_risk:
            return jsonify({
                'status': 'error',
                'message': '交易对风险设置不存在'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': {
                'symbol': pair_risk.symbol,
                'max_position': pair_risk.max_position,
                'stop_loss': pair_risk.stop_loss,
                'take_profit': pair_risk.take_profit
            }
        })
        
    except Exception as e:
        logger.error(f'获取交易对风险设置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/pair/<symbol>', methods=['DELETE'])
@login_required
def delete_pair_risk(symbol):
    try:
        pair_risk = RiskConfig.query.filter_by(
            user_id=current_user.id,
            symbol=symbol
        ).first()
        
        if not pair_risk:
            return jsonify({
                'status': 'error',
                'message': '交易对风险设置不存在'
            }), 404
        
        db.session.delete(pair_risk)
        db.session.commit()
        logger.info(f'用户 {current_user.username} 删除了 {symbol} 的风险设置')
        
        return jsonify({
            'status': 'success',
            'message': '交易对风险设置已删除'
        })
        
    except Exception as e:
        logger.error(f'删除交易对风险设置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/risk/monitor')
@login_required
def monitor():
    return render_template('risk/monitor.html')

@risk.route('/api/risk/monitor')
@login_required
def get_risk_monitor():
    try:
        # 获取账户风险指标
        risk_metrics = octobot_api.get_risk_status()
        
        if not risk_metrics:
            risk_metrics = {
                'account_risk': 0,
                'current_drawdown': 0,
                'position_stress': 0,
                'volatility_risk': 0
            }
        
        # 获取持仓风险数据
        positions = []
        trades = Trade.query.filter_by(
            user_id=current_user.id,
            status='open'
        ).all()
        
        for trade in trades:
            # 获取当前市场价格
            price_data = octobot_api.get_price(trade.symbol)
            if price_data:
                current_price = price_data['price']
                # 计算未实现盈亏
                pnl = ((current_price - trade.price) / trade.price) * 100
                # 计算距离止损距离
                risk_config = RiskConfig.query.filter_by(
                    user_id=current_user.id,
                    symbol=trade.symbol
                ).first()
                stop_loss_distance = abs(pnl) if risk_config else 0
                
                positions.append({
                    'symbol': trade.symbol,
                    'amount': trade.amount,
                    'unrealized_pnl': pnl,
                    'stop_loss_distance': stop_loss_distance,
                    'risk_level': min(100, max(0, abs(pnl) * 2))  # 简单的风险等级计算
                })
        
        # 获取最新的预警信息
        alerts = []
        # TODO: 实现预警信息获取逻辑
        
        return jsonify({
            'status': 'success',
            'data': {
                'metrics': risk_metrics,
                'positions': positions,
                'alerts': alerts
            }
        })
        
    except Exception as e:
        logger.error(f'获取风险监控数据失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/risk/alerts')
@login_required
def alerts():
    return render_template('risk/alerts.html')

@risk.route('/api/risk/alerts', methods=['GET'])
@login_required
def get_alerts():
    try:
        # 获取预警规则
        alert_rules = []  # TODO: 从数据库获取预警规则
        
        # 获取历史预警记录
        alert_history = []  # TODO: 从数据库获取历史预警记录
        
        return jsonify({
            'status': 'success',
            'data': {
                'rules': alert_rules,
                'history': alert_history
            }
        })
        
    except Exception as e:
        logger.error(f'获取预警数据失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules', methods=['GET'])
@login_required
def get_alert_rules():
    try:
        rules = AlertRule.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'symbol': rule.symbol,
                'type': rule.type,
                'condition': rule.condition,
                'threshold': rule.threshold,
                'threshold_secondary': rule.threshold_secondary,
                'timeframe': rule.timeframe,
                'is_active': rule.is_active,
                'notify_email': rule.notify_email,
                'notify_telegram': rule.notify_telegram,
                'created_at': rule.created_at.isoformat()
            } for rule in rules]
        })
    except Exception as e:
        logger.error(f'获取预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules', methods=['POST'])
@login_required
def create_alert_rule():
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['name', 'type', 'condition', 'threshold']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400
        
        # 创建新规则
        rule = AlertRule(
            user_id=current_user.id,
            name=data['name'],
            description=data.get('description', ''),
            symbol=data.get('symbol'),
            type=data['type'],
            condition=data['condition'],
            threshold=float(data['threshold']),
            threshold_secondary=float(data['threshold_secondary']) if 'threshold_secondary' in data else None,
            timeframe=data.get('timeframe'),
            is_active=data.get('is_active', True),
            notify_email=data.get('notify_email', True),
            notify_telegram=data.get('notify_telegram', False)
        )
        
        db.session.add(rule)
        db.session.commit()
        
        logger.info(f'用户 {current_user.username} 创建了新的预警规则: {rule.name}')
        
        return jsonify({
            'status': 'success',
            'message': '预警规则创建成功',
            'data': {
                'id': rule.id,
                'name': rule.name
            }
        })
        
    except Exception as e:
        logger.error(f'创建预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_alert_rule(rule_id):
    try:
        rule = AlertRule.query.filter_by(
            id=rule_id,
            user_id=current_user.id
        ).first()
        
        if not rule:
            return jsonify({
                'status': 'error',
                'message': '预警规则不存在'
            }), 404
        
        data = request.get_json()
        
        # 更新规则
        if 'name' in data:
            rule.name = data['name']
        if 'description' in data:
            rule.description = data['description']
        if 'symbol' in data:
            rule.symbol = data['symbol']
        if 'type' in data:
            rule.type = data['type']
        if 'condition' in data:
            rule.condition = data['condition']
        if 'threshold' in data:
            rule.threshold = float(data['threshold'])
        if 'threshold_secondary' in data:
            rule.threshold_secondary = float(data['threshold_secondary'])
        if 'timeframe' in data:
            rule.timeframe = data['timeframe']
        if 'is_active' in data:
            rule.is_active = bool(data['is_active'])
        if 'notify_email' in data:
            rule.notify_email = bool(data['notify_email'])
        if 'notify_telegram' in data:
            rule.notify_telegram = bool(data['notify_telegram'])
        
        db.session.commit()
        logger.info(f'用户 {current_user.username} 更新了预警规则: {rule.name}')
        
        return jsonify({
            'status': 'success',
            'message': '预警规则更新成功'
        })
        
    except Exception as e:
        logger.error(f'更新预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_alert_rule(rule_id):
    try:
        rule = AlertRule.query.filter_by(
            id=rule_id,
            user_id=current_user.id
        ).first()
        
        if not rule:
            return jsonify({
                'status': 'error',
                'message': '预警规则不存在'
            }), 404
        
        db.session.delete(rule)
        db.session.commit()
        logger.info(f'用户 {current_user.username} 删除了预警规则: {rule.name}')
        
        return jsonify({
            'status': 'success',
            'message': '预警规则已删除'
        })
        
    except Exception as e:
        logger.error(f'删除预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_alert_rule(rule_id):
    try:
        rule = AlertRule.query.filter_by(
            id=rule_id,
            user_id=current_user.id
        ).first()
        
        if not rule:
            return jsonify({
                'status': 'error',
                'message': '预警规则不存在'
            }), 404
        
        # 切换规则状态
        rule.is_active = not rule.is_active
        db.session.commit()
        
        status = '启用' if rule.is_active else '禁用'
        logger.info(f'用户 {current_user.username} {status}了预警规则: {rule.name}')
        
        return jsonify({
            'status': 'success',
            'message': f'预警规则已{status}',
            'data': {
                'is_active': rule.is_active
            }
        })
        
    except Exception as e:
        logger.error(f'切换预警规则状态失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-history', methods=['GET'])
@login_required
def get_alert_history():
    try:
        # 获取查询参数
        days = request.args.get('days', 7, type=int)
        symbol = request.args.get('symbol')
        level = request.args.get('level')
        
        # 构建查询
        query = AlertHistory.query.filter_by(user_id=current_user.id)
        
        if symbol:
            query = query.filter_by(symbol=symbol)
        if level:
            query = query.filter_by(level=level)
            
        # 时间范围
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AlertHistory.created_at >= start_date)
        
        # 获取结果
        alerts = query.order_by(AlertHistory.created_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'data': [{
                'id': alert.id,
                'rule_id': alert.rule_id,
                'symbol': alert.symbol,
                'type': alert.type,
                'level': alert.level,
                'title': alert.title,
                'message': alert.message,
                'value': alert.value,
                'is_read': alert.is_read,
                'is_processed': alert.is_processed,
                'created_at': alert.created_at.isoformat()
            } for alert in alerts]
        })
        
    except Exception as e:
        logger.error(f'获取预警历史失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-history/<int:alert_id>/process', methods=['POST'])
@login_required
def process_alert(alert_id):
    try:
        alert = AlertHistory.query.filter_by(
            id=alert_id,
            user_id=current_user.id
        ).first()
        
        if not alert:
            return jsonify({
                'status': 'error',
                'message': '预警记录不存在'
            }), 404
        
        # 更新处理状态
        alert.is_processed = True
        alert.processed_at = datetime.utcnow()
        alert.processed_by = current_user.id
        
        db.session.commit()
        logger.info(f'用户 {current_user.username} 处理了预警: {alert.title}')
        
        return jsonify({
            'status': 'success',
            'message': '预警已处理'
        })
        
    except Exception as e:
        logger.error(f'处理预警失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules/export', methods=['GET'])
@login_required
def export_alert_rules():
    try:
        # 获取用户的所有预警规则
        rules = AlertRule.query.filter_by(user_id=current_user.id).all()
        
        # 确定导出格式
        export_format = request.args.get('format', 'json')
        
        if export_format == 'json':
            # 导出为JSON
            data = [{
                'name': rule.name,
                'description': rule.description,
                'symbol': rule.symbol,
                'type': rule.type,
                'condition': rule.condition,
                'threshold': rule.threshold,
                'threshold_secondary': rule.threshold_secondary,
                'timeframe': rule.timeframe,
                'is_active': rule.is_active,
                'notify_email': rule.notify_email,
                'notify_telegram': rule.notify_telegram
            } for rule in rules]
            
            # 创建内存文件
            output = io.StringIO()
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.seek(0)
            
            # 生成文件名
            filename = f'alert_rules_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=filename
            )
            
        elif export_format == 'csv':
            # 导出为CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                'name', 'description', 'symbol', 'type', 'condition',
                'threshold', 'threshold_secondary', 'timeframe',
                'is_active', 'notify_email', 'notify_telegram'
            ])
            
            # 写入数据
            for rule in rules:
                writer.writerow([
                    rule.name,
                    rule.description,
                    rule.symbol,
                    rule.type,
                    rule.condition,
                    rule.threshold,
                    rule.threshold_secondary,
                    rule.timeframe,
                    rule.is_active,
                    rule.notify_email,
                    rule.notify_telegram
                ])
            
            output.seek(0)
            
            # 生成文件名
            filename = f'alert_rules_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        
        else:
            return jsonify({
                'status': 'error',
                'message': '不支持的导出格式'
            }), 400
            
    except Exception as e:
        logger.error(f'导出预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@risk.route('/api/risk/alert-rules/import', methods=['POST'])
@login_required
def import_alert_rules():
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '未上传文件'
            }), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'status': 'error',
                'message': '未选择文件'
            }), 400
            
        # 检查文件类型
        if not (file.filename.endswith('.json') or file.filename.endswith('.csv')):
            return jsonify({
                'status': 'error',
                'message': '仅支持JSON或CSV文件'
            }), 400
            
        # 读取文件内容
        content = file.read().decode('utf-8')
        rules_data = []
        
        if file.filename.endswith('.json'):
            # 解析JSON文件
            rules_data = json.loads(content)
            if not isinstance(rules_data, list):
                rules_data = [rules_data]
                
        else:  # CSV文件
            # 解析CSV文件
            reader = csv.DictReader(io.StringIO(content))
            rules_data = list(reader)
        
        # 导入规则
        imported_count = 0
        for data in rules_data:
            try:
                # 创建新规则
                rule = AlertRule(
                    user_id=current_user.id,
                    name=data['name'],
                    description=data.get('description', ''),
                    symbol=data.get('symbol'),
                    type=data['type'],
                    condition=data['condition'],
                    threshold=float(data['threshold']),
                    threshold_secondary=float(data['threshold_secondary']) if data.get('threshold_secondary') else None,
                    timeframe=data.get('timeframe'),
                    is_active=bool(data.get('is_active', True)),
                    notify_email=bool(data.get('notify_email', True)),
                    notify_telegram=bool(data.get('notify_telegram', False))
                )
                
                db.session.add(rule)
                imported_count += 1
                
            except Exception as e:
                logger.warning(f'导入规则失败: {str(e)}')
                continue
        
        db.session.commit()
        logger.info(f'用户 {current_user.username} 导入了 {imported_count} 条预警规则')
        
        return jsonify({
            'status': 'success',
            'message': f'成功导入 {imported_count} 条预警规则',
            'data': {
                'imported_count': imported_count
            }
        })
        
    except Exception as e:
        logger.error(f'导入预警规则失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 