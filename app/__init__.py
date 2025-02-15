from flask import Flask
from .extensions import db, login_manager

def create_app(config=None):
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object('config')
    if config:
        app.config.update(config)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    
    # 注册蓝图
    from .controllers.auth import auth
    from .controllers.dashboard import dashboard
    from .controllers.trading import trading
    from .controllers.strategy import strategy
    from .controllers.risk import risk
    
    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(trading)
    app.register_blueprint(strategy)
    app.register_blueprint(risk)
    
    # 初始化任务调度器
    with app.app_context():
        from .tasks.scheduler import init_scheduler
        init_scheduler(app)
    
    return app 