from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app
import logging
from .alert_checker import check_alerts

logger = logging.getLogger(__name__)

def init_scheduler(app):
    """
    初始化任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        
        # 添加预警检查任务
        scheduler.add_job(
            func=check_alerts,
            trigger=IntervalTrigger(
                seconds=app.config.get('ALERT_CHECK_INTERVAL', 60)
            ),
            id='alert_checker',
            name='预警检查任务',
            replace_existing=True
        )
        
        # 启动调度器
        scheduler.start()
        logger.info('任务调度器已启动')
        
        # 在应用关闭时停止调度器
        import atexit
        atexit.register(lambda: scheduler.shutdown())
        
    except Exception as e:
        logger.error(f'启动任务调度器失败: {str(e)}') 