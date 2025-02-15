import logging
import threading
import time
from functools import wraps
from flask import current_app

logger = logging.getLogger(__name__)

class TaskLock:
    _locks = {}
    _lock = threading.Lock()
    
    @classmethod
    def acquire(cls, task_name: str, timeout: int = 0) -> bool:
        """
        获取任务锁
        
        参数:
            task_name: 任务名称
            timeout: 超时时间（秒），0表示立即返回
            
        返回:
            是否获取到锁
        """
        with cls._lock:
            current_time = time.time()
            
            # 检查锁是否存在且未过期
            if task_name in cls._locks:
                lock_time, thread_id = cls._locks[task_name]
                # 如果是同一个线程，允许重入
                if thread_id == threading.get_ident():
                    return True
                # 检查锁是否过期
                if current_time - lock_time < timeout:
                    return False
            
            # 获取锁
            cls._locks[task_name] = (current_time, threading.get_ident())
            return True
    
    @classmethod
    def release(cls, task_name: str) -> None:
        """释放任务锁"""
        with cls._lock:
            if task_name in cls._locks:
                _, thread_id = cls._locks[task_name]
                if thread_id == threading.get_ident():
                    del cls._locks[task_name]

def task_lock(name: str, timeout: int = 3600):
    """任务锁装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not TaskLock.acquire(name, timeout):
                logger.warning(f'任务 {name} 已在运行中')
                return None
            try:
                return func(*args, **kwargs)
            finally:
                TaskLock.release(name)
        return wrapper
    return decorator 