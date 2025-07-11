"""
技术指标计算模块
提供股票技术指标的计算和管理功能
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import logging
import numpy as np

from base.monitor import TechnicalIndicators, SignalType
from modules.futu_market import FutuMarket

logger = logging.getLogger(__name__)


class IndicatorsCalculator:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> Optional[float]:
        """
        计算移动平均线
        
        输入数据: prices=[100, 101, 102, 103, 104], period=5
        输出数据: 102.0 (平均值)
        """
        try:
            if len(prices) < period:
                return None
            return sum(prices[-period:]) / period
        except Exception as e:
            logger.error(f"MA计算失败: {e}")
            return None
        
    @staticmethod 
    def calculate_rsi(prices: List[float], period: int = 14) -> Tuple[Optional[float], SignalType]:
        """
        计算RSI指标
        
        输入数据: prices=历史收盘价列表, period=14
        输出数据: (rsi_value, signal)
        - rsi_value: RSI数值 (0-100)
        - signal: SignalType.BUY (RSI<30), SignalType.SELL (RSI>70), SignalType.HOLD (30-70)
        """
        try:
            if len(prices) < period + 1:
                return None, SignalType.HOLD
                
            # 计算价格变化
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # 分离上升和下跌
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # 计算平均增益和损失
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0, SignalType.SELL
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # 生成信号
            if rsi < 30:
                signal = SignalType.BUY
            elif rsi > 70:
                signal = SignalType.SELL
            else:
                signal = SignalType.HOLD
                
            return rsi, signal
        except Exception as e:
            logger.error(f"RSI计算失败: {e}")
            return None, SignalType.HOLD
        
    @staticmethod
    def calculate_macd(prices: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float], SignalType]:
        """
        计算MACD指标
        
        输入数据: prices=历史收盘价列表
        输出数据: (macd_line, signal_line, histogram, signal)
        - macd_line: MACD线值
        - signal_line: 信号线值  
        - histogram: 柱状图值
        - signal: SignalType enum
        """
        try:
            if len(prices) < 26:  # MACD需要至少26天数据
                return None, None, None, SignalType.HOLD
                
            # 计算EMA
            def calculate_ema(data, period):
                multiplier = 2 / (period + 1)
                ema = [sum(data[:period]) / period]  # 第一个值用SMA
                for i in range(period, len(data)):
                    ema.append((data[i] * multiplier) + (ema[-1] * (1 - multiplier)))
                return ema
            
            # 计算EMA12和EMA26
            ema12 = calculate_ema(prices, 12)
            ema26 = calculate_ema(prices, 26)
            
            # 计算MACD线
            macd_line = ema12[-1] - ema26[-1]
            
            # 计算信号线 (MACD的EMA9)
            if len(prices) >= 34:  # 26 + 9 - 1
                macd_values = [ema12[i] - ema26[i] for i in range(len(ema26))]
                signal_ema = calculate_ema(macd_values, 9)
                signal_line = signal_ema[-1]
                histogram = macd_line - signal_line
                
                # 生成信号
                if histogram > 0 and len(signal_ema) > 1:
                    prev_histogram = macd_values[-2] - signal_ema[-2]
                    if histogram > prev_histogram:
                        signal = SignalType.BUY
                    else:
                        signal = SignalType.HOLD
                elif histogram < 0:
                    signal = SignalType.SELL
                else:
                    signal = SignalType.HOLD
                    
                return macd_line, signal_line, histogram, signal
            else:
                return macd_line, None, None, SignalType.HOLD
                
        except Exception as e:
            logger.error(f"MACD计算失败: {e}")
            return None, None, None, SignalType.HOLD


class IndicatorsManager:
    """技术指标管理器"""
    
    def __init__(self):
        self.futu_market = FutuMarket()
        self.calculator = IndicatorsCalculator()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def update_all_indicators(self, stock_codes: List[str]) -> Dict[str, TechnicalIndicators]:
        """
        更新所有股票的技术指标
        
        输入数据: stock_codes = ["HK.00700", "HK.09988"]
        输出数据: {
            "HK.00700": TechnicalIndicators(...),
            "HK.09988": TechnicalIndicators(...)
        }
        
        处理流程:
        1. 获取历史K线数据 -> get_historical_klines()
        2. 计算各项技术指标 -> calculate_ma/rsi/macd()
        3. 生成买卖信号
        4. 返回指标对象
        """
        try:
            result = {}
            for code in stock_codes:
                # 获取历史数据
                import asyncio
                loop = asyncio.get_event_loop()
                kline_data = await loop.run_in_executor(
                    None,
                    self.futu_market.get_cur_kline,
                    [code],
                    60,  # 60天数据
                    "K_DAY",
                    "qfq"  # 前复权
                )
                if not kline_data or len(kline_data) == 0:
                    continue
                
                # 转换为DataFrame
                klines = self._convert_kline_to_dataframe(kline_data[0])
                if klines.empty:
                    continue
                    
                # 提取收盘价
                close_prices = klines['close'].tolist()
                
                # 计算技术指标
                ma5 = self.calculator.calculate_ma(close_prices, 5)
                ma10 = self.calculator.calculate_ma(close_prices, 10)
                ma20 = self.calculator.calculate_ma(close_prices, 20)
                
                rsi14, rsi_signal = self.calculator.calculate_rsi(close_prices, 14)
                
                macd_line, signal_line, histogram, macd_signal = self.calculator.calculate_macd(close_prices)
                
                # 创建指标对象
                indicators = TechnicalIndicators(
                    stock_code=code,
                    ma5=ma5,
                    ma10=ma10,
                    ma20=ma20,
                    rsi14=rsi14,
                    rsi_signal=rsi_signal,
                    macd_line=macd_line,
                    signal_line=signal_line,
                    histogram=histogram,
                    macd_signal=macd_signal
                )
                
                result[code] = indicators
                
            return result
        except Exception as e:
            self.logger.error(f"更新技术指标失败: {e}")
            return {}
    
    def _convert_kline_to_dataframe(self, kline_data: Dict) -> pd.DataFrame:
        """将富途K线数据转换为标准DataFrame格式"""
        try:
            # 提取K线数据
            klines = kline_data.get('kline_list', [])
            
            if not klines:
                return pd.DataFrame()
            
            # 转换为DataFrame
            data = []
            for kline in klines:
                data.append({
                    'time_key': kline.get('time_key', ''),
                    'open': float(kline.get('open', 0)),
                    'close': float(kline.get('close', 0)),
                    'high': float(kline.get('high', 0)),
                    'low': float(kline.get('low', 0)),
                    'volume': int(kline.get('volume', 0)),
                    'turnover': float(kline.get('turnover', 0))
                })
            
            df = pd.DataFrame(data)
            # 确保时间列为datetime类型
            if not df.empty:
                df['time_key'] = pd.to_datetime(df['time_key'])
                df = df.sort_values('time_key').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"转换K线数据时发生错误: {e}")
            return pd.DataFrame()