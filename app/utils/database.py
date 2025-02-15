import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from ..models import db

logger = logging.getLogger(__name__)

def with_db_session(func):
    """数据库会话装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'数据库操作失败: {str(e)}')
            raise
        finally:
            db.session.close()
    return wrapper

def retry_on_db_error(max_retries=3):
    """数据库操作重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    last_error = e
                    logger.warning(f'数据库操作失败，尝试重试 ({attempt + 1}/{max_retries}): {str(e)}')
                    if attempt < max_retries - 1:
                        db.session.rollback()
                        continue
            logger.error(f'数据库操作失败，已达到最大重试次数: {str(last_error)}')
            raise last_error
        return wrapper
    return decorator 