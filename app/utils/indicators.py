import numpy as np
import pandas as pd
from typing import Tuple, Union

def calculate_rsi(prices: Union[pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
    """
    计算相对强弱指标(RSI)
    
    参数:
        prices: 价格序列
        period: RSI周期，默认14
        
    返回:
        RSI值数组
    """
    # 确保输入是numpy数组
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    # 计算价格变化
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    
    # 分别计算上涨和下跌
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    
    if down != 0:
        rs = up/down
    else:
        rs = 0
    
    rsi = np.zeros_like(prices)
    rsi[period] = 100. - 100./(1. + rs)
    
    # 使用Wilder平滑计算RSI
    for i in range(period + 1, len(prices)):
        delta = deltas[i - 1]
        
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        
        if down != 0:
            rs = up/down
        else:
            rs = 0
            
        rsi[i] = 100. - 100./(1. + rs)
        
    return rsi

def calculate_macd(prices: Union[pd.Series, np.ndarray], 
                  fast_period: int = 12,
                  slow_period: int = 26,
                  signal_period: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    计算移动平均收敛散度(MACD)
    
    参数:
        prices: 价格序列
        fast_period: 快速EMA周期，默认12
        slow_period: 慢速EMA周期，默认26
        signal_period: 信号线周期，默认9
        
    返回:
        (macd, signal, histogram)元组
    """
    # 确保输入是numpy数组
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    # 计算快速和慢速EMA
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    
    # 计算MACD线
    macd = ema_fast - ema_slow
    
    # 计算信号线
    signal = calculate_ema(macd, signal_period)
    
    # 计算MACD柱状图
    histogram = macd - signal
    
    return macd, signal, histogram

def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """
    计算指数移动平均线(EMA)
    
    参数:
        prices: 价格序列
        period: EMA周期
        
    返回:
        EMA值数组
    """
    ema = np.zeros_like(prices)
    multiplier = 2 / (period + 1)
    
    # 初始化EMA
    ema[period-1] = np.mean(prices[:period])
    
    # 计算EMA
    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
    return ema

def calculate_volatility(prices: Union[pd.Series, np.ndarray], period: int = 20) -> float:
    """
    计算波动率
    
    参数:
        prices: 价格序列
        period: 计算周期，默认20
        
    返回:
        波动率值
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    # 计算对数收益率
    returns = np.log(prices[1:] / prices[:-1])
    
    # 计算标准差
    volatility = np.std(returns[-period:])
    
    # 年化波动率（假设数据是日线）
    annualized_volatility = volatility * np.sqrt(252)
    
    return annualized_volatility

def calculate_drawdown(prices: Union[pd.Series, np.ndarray], window: int = 20) -> float:
    """
    计算回撤
    
    参数:
        prices: 价格序列
        window: 回撤计算窗口，默认20
        
    返回:
        回撤百分比
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    # 计算窗口内的最高价
    rolling_max = np.maximum.accumulate(prices[-window:])
    
    # 计算当前价格与最高价的回撤
    drawdown = (rolling_max - prices[-1]) / rolling_max * 100
    
    return drawdown[-1] if isinstance(drawdown, np.ndarray) else drawdown 