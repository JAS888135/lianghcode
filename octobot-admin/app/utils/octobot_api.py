import os
import requests
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class OctoBotAPI:
    def __init__(self):
        self.base_url = os.getenv('OCTOBOT_URL', 'http://localhost:5001')
        self.api_base = urljoin(self.base_url, '/api/v1/')

    def _get_url(self, endpoint):
        return urljoin(self.api_base, endpoint)

    def _make_request(self, method, endpoint, data=None, params=None):
        url = self._get_url(endpoint)
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"OctoBot API请求失败: {str(e)}")
            return None

    def get_status(self):
        """获取OctoBot状态"""
        return self._make_request('GET', 'status')

    def get_portfolio(self):
        """获取投资组合信息"""
        return self._make_request('GET', 'portfolio')

    def get_trades(self, symbol=None):
        """获取交易历史"""
        params = {'symbol': symbol} if symbol else None
        return self._make_request('GET', 'trades', params=params)

    def get_orders(self, symbol=None):
        """获取订单信息"""
        params = {'symbol': symbol} if symbol else None
        return self._make_request('GET', 'orders', params=params)

    def place_order(self, order_data):
        """下单"""
        return self._make_request('POST', 'orders', data=order_data)

    def cancel_order(self, order_id):
        """取消订单"""
        return self._make_request('DELETE', f'orders/{order_id}')

    def get_price(self, symbol):
        """获取价格信息"""
        return self._make_request('GET', f'prices/{symbol}')

    def get_symbols(self):
        """获取支持的交易对"""
        return self._make_request('GET', 'symbols')

    def get_exchange_status(self, exchange_id):
        """获取交易所状态"""
        return self._make_request('GET', f'exchanges/{exchange_id}/status')

    def start_strategy(self, strategy_data):
        """启动策略"""
        return self._make_request('POST', 'strategies/start', data=strategy_data)

    def stop_strategy(self, strategy_id):
        """停止策略"""
        return self._make_request('POST', f'strategies/{strategy_id}/stop')

    def get_strategy_status(self, strategy_id):
        """获取策略状态"""
        return self._make_request('GET', f'strategies/{strategy_id}/status')

    def get_backtesting_status(self, backtesting_id):
        """获取回测状态"""
        return self._make_request('GET', f'backtesting/{backtesting_id}/status')

    def start_backtesting(self, config):
        """启动回测"""
        return self._make_request('POST', 'backtesting/start', data=config)

    def get_risk_status(self):
        """获取风险状态"""
        return self._make_request('GET', 'risk/status')

    def update_risk_settings(self, settings):
        """更新风险设置"""
        return self._make_request('POST', 'risk/settings', data=settings)

    def get_performance(self, timeframe='1d'):
        """获取性能数据"""
        params = {'timeframe': timeframe}
        return self._make_request('GET', 'performance', params=params)

    def get_logs(self, level='INFO'):
        """获取日志"""
        params = {'level': level}
        return self._make_request('GET', 'logs', params=params) 