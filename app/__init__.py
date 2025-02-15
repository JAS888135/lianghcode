from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import logging
import os
from logging.handlers import RotatingFileHandler
from config.config import config
from .models import db, User
from .utils.octobot_api import OctoBotAPI

login_manager = LoginManager()
octobot_api = OctoBotAPI()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 配置日志
    formatter = logging.Formatter(app.config['LOG_FORMAT'])
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(app.config['LOG_LEVEL'])
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from .controllers.auth import auth as auth_blueprint
    from .controllers.dashboard import dashboard as dashboard_blueprint
    from .controllers.trading import trading as trading_blueprint
    from .controllers.strategy import strategy as strategy_blueprint
    from .controllers.settings import settings as settings_blueprint
    from .controllers.risk import risk as risk_blueprint
    from .controllers.telegram import telegram
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(dashboard_blueprint)
    app.register_blueprint(trading_blueprint)
    app.register_blueprint(strategy_blueprint)
    app.register_blueprint(settings_blueprint)
    app.register_blueprint(risk_blueprint)
    app.register_blueprint(telegram)
    
    # 初始化任务调度器
    from .tasks.scheduler import init_scheduler
    init_scheduler(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员账户
        if not User.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin',
                password=generate_password_hash('admin'),
                email='admin@example.com',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
    
    @app.before_request
    def before_request():
        """请求预处理"""
        pass
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 添加安全相关的响应头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    @app.errorhandler(404)
    def page_not_found(e):
        """404错误处理"""
        return {'error': '页面未找到'}, 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """500错误处理"""
        app.logger.error(f'服务器错误: {str(e)}')
        return {'error': '服务器内部错误'}, 500
    
    return app 