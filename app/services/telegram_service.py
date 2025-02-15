from datetime import datetime
import logging
from telegram import Bot, ParseMode
from telegram.error import TelegramError
from flask import current_app
from ..models import db, TelegramConfig
from ..utils.notification import rate_limit, retry

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot = None
        self._init_bot()

    def _init_bot(self):
        """初始化 Telegram Bot"""
        try:
            token = current_app.config['TELEGRAM_BOT_TOKEN']
            self.bot = Bot(token=token)
        except Exception as e:
            logger.error(f'初始化 Telegram Bot 失败: {str(e)}')
            self.bot = None

    @retry(max_retries=3, delay=1)
    @rate_limit(max_count=20, period=60)  # 每分钟最多20条消息
    async def send_message(self, chat_id: str, message: str, parse_mode: str = ParseMode.MARKDOWN) -> bool:
        """
        发送 Telegram 消息
        
        参数:
            chat_id: Telegram 聊天 ID
            message: 消息内容
            parse_mode: 消息解析模式
            
        返回:
            是否发送成功
        """
        try:
            if not self.bot:
                self._init_bot()
                if not self.bot:
                    raise Exception('Telegram Bot 未初始化')

            # 检查是否在安静时间
            config = TelegramConfig.query.filter_by(chat_id=chat_id, is_active=True).first()
            if config and self._is_quiet_hours(config):
                logger.info(f'当前是安静时间，消息将不会发送到 {chat_id}')
                return False

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True

        except TelegramError as e:
            logger.error(f'发送 Telegram 消息失败: {str(e)}')
            raise

    def _is_quiet_hours(self, config: TelegramConfig) -> bool:
        """检查当前是否是安静时间"""
        if not config.quiet_hours_start or not config.quiet_hours_end:
            return False

        current_hour = datetime.now().hour
        start = config.quiet_hours_start
        end = config.quiet_hours_end

        if start <= end:
            return start <= current_hour < end
        else:  # 跨天的情况
            return current_hour >= start or current_hour < end

    async def verify_chat_id(self, chat_id: str) -> bool:
        """验证 chat_id 是否有效"""
        try:
            if not self.bot:
                self._init_bot()
                if not self.bot:
                    raise Exception('Telegram Bot 未初始化')

            await self.bot.get_chat(chat_id)
            return True

        except TelegramError:
            return False

    def format_trade_message(self, trade) -> str:
        """格式化交易消息"""
        return f"""
*交易通知*
交易对: {trade.symbol}
类型: {trade.type}
方向: {trade.side}
数量: {trade.amount}
价格: {trade.price}
状态: {trade.status}
时间: {trade.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_alert_message(self, alert) -> str:
        """格式化预警消息"""
        return f"""
*{alert.title}*
级别: {alert.level}
类型: {alert.type}
交易对: {alert.symbol}
触发值: {alert.value}
消息: {alert.message}
时间: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_system_message(self, title: str, message: str) -> str:
        """格式化系统消息"""
        return f"""
*系统通知 - {title}*
{message}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_performance_message(self, data: dict) -> str:
        """格式化性能报告消息"""
        return f"""
*性能报告*
总收益率: {data['total_return']}%
今日收益: {data['daily_return']}%
胜率: {data['win_rate']}%
最大回撤: {data['max_drawdown']}%
夏普比率: {data['sharpe_ratio']}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""" 