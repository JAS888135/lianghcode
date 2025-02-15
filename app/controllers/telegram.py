from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from ..models import db, TelegramConfig
from ..services.telegram_service import TelegramService
import logging

logger = logging.getLogger(__name__)
telegram = Blueprint('telegram', __name__)
telegram_service = TelegramService()

@telegram.route('/telegram/settings', methods=['GET'])
@login_required
def settings():
    """Telegram 设置页面"""
    config = TelegramConfig.query.filter_by(user_id=current_user.id).first()
    return render_template('telegram/settings.html', config=config)

@telegram.route('/api/telegram/config', methods=['GET'])
@login_required
def get_config():
    """获取 Telegram 配置"""
    config = TelegramConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        return jsonify({
            'status': 'success',
            'data': None
        })
    
    return jsonify({
        'status': 'success',
        'data': {
            'chat_id': config.chat_id,
            'is_active': config.is_active,
            'notification_types': config.notification_types,
            'quiet_hours_start': config.quiet_hours_start,
            'quiet_hours_end': config.quiet_hours_end
        }
    })

@telegram.route('/api/telegram/config', methods=['POST'])
@login_required
async def update_config():
    """更新 Telegram 配置"""
    try:
        data = request.get_json()
        
        # 验证 chat_id
        chat_id = data.get('chat_id')
        if not chat_id:
            return jsonify({
                'status': 'error',
                'message': '请提供 Telegram Chat ID'
            }), 400
        
        # 验证 chat_id 是否有效
        if not await telegram_service.verify_chat_id(chat_id):
            return jsonify({
                'status': 'error',
                'message': '无效的 Telegram Chat ID'
            }), 400
        
        config = TelegramConfig.query.filter_by(user_id=current_user.id).first()
        if not config:
            config = TelegramConfig(user_id=current_user.id)
            db.session.add(config)
        
        config.chat_id = chat_id
        config.is_active = data.get('is_active', True)
        config.notification_types = data.get('notification_types', {
            'trade': True,
            'alert': True,
            'system': True,
            'performance': True
        })
        config.quiet_hours_start = data.get('quiet_hours_start')
        config.quiet_hours_end = data.get('quiet_hours_end')
        
        db.session.commit()
        
        # 发送测试消息
        test_message = """
*Telegram 通知测试*
您的 Telegram 通知已成功配置！
您将收到以下类型的通知：
{}
""".format('\n'.join([f"- {k}" for k, v in config.notification_types.items() if v]))
        
        await telegram_service.send_message(chat_id, test_message)
        
        return jsonify({
            'status': 'success',
            'message': 'Telegram 配置已更新'
        })
        
    except Exception as e:
        logger.error(f'更新 Telegram 配置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@telegram.route('/api/telegram/test', methods=['POST'])
@login_required
async def test_notification():
    """测试 Telegram 通知"""
    try:
        config = TelegramConfig.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not config:
            return jsonify({
                'status': 'error',
                'message': '请先配置 Telegram'
            }), 400
        
        test_message = """
*Telegram 测试消息*
这是一条测试消息，用于验证您的 Telegram 通知是否正常工作。

当前配置:
- 通知类型: {}
- 安静时间: {}
""".format(
            ', '.join([k for k, v in config.notification_types.items() if v]),
            f"{config.quiet_hours_start}:00 - {config.quiet_hours_end}:00" if config.quiet_hours_start is not None else "未设置"
        )
        
        success = await telegram_service.send_message(config.chat_id, test_message)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '测试消息已发送'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '发送测试消息失败'
            }), 500
            
    except Exception as e:
        logger.error(f'发送测试消息失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 