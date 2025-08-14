"""
AnalysisDataManager - 分析页面数据管理模块

负责分析页面的股票数据获取、历史数据处理、技术指标计算和实时数据更新
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from base.monitor import StockData, MarketStatus, ConnectionStatus
from base.futu_class import KLineData, OrderBookData, BrokerQueueData
from modules.futu_market import FutuMarket
from utils.logger import get_logger
from utils.global_vars import PATH_DATA

# 时间周期常量
TIME_PERIODS = {
    'D': 'K_DAY',      # 日线
    'W': 'K_WEEK',     # 周线  
    'M': 'K_MON'       # 月线
}

# 数据缓存配置
KLINE_CACHE_DAYS = 90      # K线数据缓存天数
ORDERBOOK_REFRESH_SEC = 3   # 五档数据刷新间隔(秒)
TICK_REFRESH_SEC = 1        # 逐笔数据刷新间隔(秒)


@dataclass
class AnalysisDataSet:
    """分析页面数据集"""
    stock_code: str
    stock_name: str
    basic_info: Dict[str, Any]          # 基础信息
    realtime_quote: Dict[str, Any]      # 实时报价
    kline_data: List[KLineData]         # K线数据
    orderbook_data: Optional[OrderBookData]  # 五档数据
    tick_data: List[Dict[str, Any]]     # 逐笔数据
    broker_queue: Optional[BrokerQueueData]  # 经纪队列
    capital_flow: Dict[str, Any]        # 资金流向数据
    technical_indicators: Dict[str, Any] # 技术指标
    last_update: datetime


class AnalysisDataManager:
    """
    分析数据管理器
    负责分析页面的所有数据获取和处理
    """
    
    def __init__(self, app_core, futu_market: FutuMarket):
        """初始化分析数据管理器"""
        self.app_core = app_core
        self.futu_market = futu_market
        self.logger = get_logger(__name__)
        
        # 当前分析的股票（主要用于UI显示，可能有多个标签页打开不同股票）
        self.current_stock_code: Optional[str] = None
        self.current_time_period: str = 'D'  # 默认日线
        
        # 数据缓存
        self.analysis_data_cache: Dict[str, AnalysisDataSet] = {}
        self.kline_cache: Dict[str, Dict[str, List[KLineData]]] = {}  # {stock_code: {period: data}}
        
        # 按股票代码管理的实时更新任务
        self.stock_tasks: Dict[str, Dict[str, Optional[asyncio.Task]]] = {}  
        # 结构: {stock_code: {'realtime': task, 'orderbook': task, 'tick': task}}
        
        # 活跃股票集合（有标签页打开的股票）
        self.active_stocks: set = set()
        

        self.initialize_data_managers()
        self.logger.info("AnalysisDataManager 初始化完成")
    
    def initialize_data_managers(self) -> None:
        """初始化数据管理器"""
        try:
            connect_success = self.futu_market.check()
            if connect_success:
                self.logger.debug("富途API连接成功")
            else:
                self.logger.warning("富途API连接失败")
        except Exception as e:
            self.logger.error(f"富途API连接失败: {e}")

    def cleanup_futu_market(self) -> None:
        """清理富途市场连接"""
        try:
            if hasattr(self.futu_market, 'close'):
                self.futu_market.close()
                self.logger.info("富途市场连接已清理")
        except Exception as e:
            self.logger.warning(f"清理富途市场连接时出错: {e}")

    async def set_current_stock(self, stock_code: str) -> bool:
        """设置当前分析的股票并启动其实时更新任务"""
        try:
            self.current_stock_code = stock_code
            
            # 将股票加入活跃股票集合
            self.active_stocks.add(stock_code)
            
            self.logger.info(f"切换到股票分析: {stock_code}")
            
            # 加载股票分析数据
            await self.load_analysis_data(stock_code)
            
            # 启动该股票的实时更新任务（如果尚未启动）
            await self._start_stock_update_tasks(stock_code)
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置当前分析股票失败: {e}")
            return False
    
    async def load_analysis_data(self, stock_code: str) -> Optional[AnalysisDataSet]:
        """加载股票的完整分析数据"""
        try:
            _stock_code = stock_code.replace("_", ".") if "_" in stock_code else stock_code
            self.logger.info(f"开始加载股票 {stock_code} 的分析数据")
            
            # 检查缓存
            if stock_code in self.analysis_data_cache:
                cache_data = self.analysis_data_cache[stock_code]
                # 如果缓存数据不超过1分钟，直接返回
                if (datetime.now() - cache_data.last_update).seconds < 60:
                    self.logger.debug(f"使用缓存的分析数据: {stock_code}")
                    return cache_data
            
            # 并行获取各种数据
            loop = asyncio.get_event_loop()
            
            # 1. 获取基础信息
            basic_info_task = loop.run_in_executor(
                None, self._get_stock_basic_info, _stock_code
            )
            
            # 2. 获取实时报价
            realtime_quote_task = loop.run_in_executor(
                None, self._get_realtime_quote, _stock_code
            )
            
            # 3. 获取K线数据
            kline_data_task = loop.run_in_executor(
                None, self._get_kline_data, _stock_code, self.current_time_period
            )
            
            # 4. 获取五档数据
            orderbook_data_task = loop.run_in_executor(
                None, self._get_orderbook_data, _stock_code
            )
            
            # 5. 获取逐笔数据
            tick_data_task = loop.run_in_executor(
                None, self._get_tick_data, _stock_code
            )
            
            # 6. 获取经纪队列数据
            broker_queue_task = loop.run_in_executor(
                None, self._get_broker_queue_data, _stock_code
            )
            
            # 等待所有任务完成
            results = await asyncio.gather(
                basic_info_task,
                realtime_quote_task,
                kline_data_task,
                orderbook_data_task,
                tick_data_task,
                broker_queue_task,
                return_exceptions=True
            )
            
            basic_info, realtime_quote, kline_data, orderbook_data, tick_data, broker_queue = results
            
            # 处理异常结果
            if isinstance(basic_info, Exception):
                self.logger.error(f"获取基础信息失败: {basic_info}")
                basic_info = {}
            if isinstance(realtime_quote, Exception):
                self.logger.error(f"获取实时报价失败: {realtime_quote}")
                realtime_quote = {}
            if isinstance(kline_data, Exception):
                self.logger.error(f"获取K线数据失败: {kline_data}")
                kline_data = []
            if isinstance(orderbook_data, Exception):
                self.logger.error(f"获取五档数据失败: {orderbook_data}")
                orderbook_data = None
            if isinstance(tick_data, Exception):
                self.logger.error(f"获取逐笔数据失败: {tick_data}")
                tick_data = []
            if isinstance(broker_queue, Exception):
                self.logger.error(f"获取经纪队列失败: {broker_queue}")
                broker_queue = None
            
            # 计算技术指标
            technical_indicators = await self._calculate_technical_indicators(kline_data)
            
            # 获取资金流向数据（暂时用空字典）
            capital_flow = {}
            
            # 创建分析数据集
            analysis_data = AnalysisDataSet(
                stock_code=stock_code,
                stock_name=basic_info.get('name', stock_code),
                basic_info=basic_info,
                realtime_quote=realtime_quote,
                kline_data=kline_data,
                orderbook_data=orderbook_data,
                tick_data=tick_data,
                broker_queue=broker_queue,
                capital_flow=capital_flow,
                technical_indicators=technical_indicators,
                last_update=datetime.now()
            )
            
            # 缓存数据
            self.analysis_data_cache[stock_code] = analysis_data
            
            self.logger.info(f"股票 {stock_code} 分析数据加载完成")
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"加载分析数据失败: {e}")
            return None
    
    def _get_stock_basic_info(self, stock_code: str) -> Dict[str, Any]:
        """获取股票基础信息"""
        try:
            # 从app_core缓存获取基础信息，优先获取股票名称
            cached_info = self.app_core.stock_basicinfo_cache.get(stock_code, {})
            stock_name = cached_info.get('name', stock_code)
            
            # 使用get_market_snapshot获取市场快照数据
            snapshots = self.futu_market.get_market_snapshot([stock_code])
            self.logger.debug(f"获取股票 {stock_code} 的市场快照数据: {snapshots}")
            if snapshots and len(snapshots) > 0:
                snapshot = snapshots[0]
                
                # 从快照数据构建基础信息
                basic_info = {
                    'code': getattr(snapshot, 'code', stock_code),
                    'name': stock_name,  # 使用缓存的股票名称
                    'last_price': getattr(snapshot, 'last_price', 0.0),
                    'prev_close_price': getattr(snapshot, 'prev_close_price', 0.0),
                    'update_time': getattr(snapshot, 'update_time', ''),
                    'volume': getattr(snapshot, 'volume', 0),
                    'turnover': getattr(snapshot, 'turnover', 0.0),
                    'turnover_rate': getattr(snapshot, 'turnover_rate', 0.0),
                    'amplitude': getattr(snapshot, 'amplitude', 0.0)
                }
                
                # 如果有缓存的详细信息，添加到基础信息中
                if cached_info:
                    basic_info.update({
                        'lot_size': cached_info.get('lot_size', 0),
                        'stock_type': cached_info.get('stock_type', ''),
                        'listing_date': cached_info.get('listing_date', None),
                    })
                
                return basic_info
            
            # 如果获取快照失败，返回基础信息
            return {
                'code': stock_code, 
                'name': stock_name,
                'last_price': 0.0,
                'prev_close_price': 0.0,
                'update_time': '',
                'volume': 0,
                'turnover': 0.0,
                'turnover_rate': 0.0,
                'amplitude': 0.0
            }
            
        except Exception as e:
            self.logger.error(f"获取股票基础信息失败: {e}")
            return {
                'code': stock_code, 
                'name': stock_code,
                'last_price': 0.0,
                'prev_close_price': 0.0,
                'update_time': '',
                'volume': 0,
                'turnover': 0.0,
                'turnover_rate': 0.0,
                'amplitude': 0.0
            }
    
    def _get_realtime_quote(self, stock_code: str) -> Dict[str, Any]:
        """获取实时报价数据"""
        try:
            quotes = self.futu_market.get_stock_quote([stock_code])
            if quotes and len(quotes) > 0:
                quote = quotes[0]
                return {
                    'code': quote.code,
                    'cur_price': getattr(quote, 'cur_price', 0),
                    'prev_close_price': getattr(quote, 'prev_close_price', 0),
                    'open_price': getattr(quote, 'open_price', 0),
                    'high_price': getattr(quote, 'high_price', 0),
                    'low_price': getattr(quote, 'low_price', 0),
                    'volume': getattr(quote, 'volume', 0),
                    'turnover': getattr(quote, 'turnover', 0),
                    'change_rate': getattr(quote, 'change_rate', 0),
                    'change_val': getattr(quote, 'change_val', 0),
                    'amplitude': getattr(quote, 'amplitude', 0),
                    'turnover_rate': getattr(quote, 'turnover_rate', 0),
                }
            return {}
            
        except Exception as e:
            self.logger.error(f"获取实时报价失败: {e}")
            return {}

    def _get_kline_data(self, stock_code: str, period: str, num: int = 100) -> List[KLineData]:
        """获取K线数据"""
        try:
            # 检查缓存
            if stock_code in self.kline_cache and period in self.kline_cache[stock_code]:
                cached_data = self.kline_cache[stock_code][period]
                # 如果缓存数据足够新（1小时内），直接返回
                if cached_data and len(cached_data) > 0:
                    # 简单检查：如果缓存有数据就返回，实际项目中应该检查时间
                    return cached_data
            
            # 从API获取K线数据
            kline_type = TIME_PERIODS.get(period, 'K_DAY')
            kline_data = self.futu_market.get_cur_kline(
                [stock_code], num=num, ktype=kline_type
            )
            
            if kline_data:
                # 缓存数据
                if stock_code not in self.kline_cache:
                    self.kline_cache[stock_code] = {}
                self.kline_cache[stock_code][period] = kline_data
                
                return kline_data
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            return []
    
    def _get_orderbook_data(self, stock_code: str) -> Optional[OrderBookData]:
        """获取五档买卖盘数据"""
        try:
            orderbook = self.futu_market.get_order_book(stock_code)
            return orderbook
            
        except Exception as e:
            self.logger.error(f"获取五档数据失败: {e}")
            return None
    
    def _get_tick_data(self, stock_code: str, num: int = 50) -> List[Dict[str, Any]]:
        """获取逐笔交易数据"""
        try:
            tick_data = self.futu_market.get_rt_ticker(stock_code)
            if tick_data is not None and not tick_data.empty:
                # 转换为字典格式
                return tick_data.to_dict('records')
            return []
            
        except Exception as e:
            self.logger.error(f"获取逐笔数据失败: {e}")
            return []
    
    def _get_broker_queue_data(self, stock_code: str) -> Optional[BrokerQueueData]:
        """获取经纪队列数据"""
        try:
            broker_queue = self.futu_market.get_broker_queue(stock_code)
            return broker_queue
            
        except Exception as e:
            self.logger.error(f"获取经纪队列失败: {e}")
            return None
    
    async def _calculate_technical_indicators(self, kline_data: List[KLineData]) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            if not kline_data or len(kline_data) < 20:
                return {}
            
            # 提取价格数据
            closes = [k.close for k in kline_data]
            highs = [k.high for k in kline_data]
            lows = [k.low for k in kline_data]
            volumes = [k.volume for k in kline_data]
            
            # 计算移动平均线
            ma5 = self._calculate_ma(closes, 5)
            ma10 = self._calculate_ma(closes, 10)
            ma20 = self._calculate_ma(closes, 20)
            ma60 = self._calculate_ma(closes, 60)
            
            # 计算RSI
            rsi = self._calculate_rsi(closes, 14)
            
            # 计算MACD
            macd_data = self._calculate_macd(closes)
            
            return {
                'ma5': ma5[-1] if ma5 else 0,
                'ma10': ma10[-1] if ma10 else 0,
                'ma20': ma20[-1] if ma20 else 0,
                'ma60': ma60[-1] if ma60 else 0,
                'rsi': rsi[-1] if rsi else 0,
                'macd': macd_data,
                'price_trend': self._analyze_price_trend(closes, ma20),
                'volume_trend': self._analyze_volume_trend(volumes),
            }
            
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {e}")
            return {}
    
    def _calculate_ma(self, prices: List[float], period: int) -> List[float]:
        """计算移动平均线"""
        if len(prices) < period:
            return []
        
        ma_values = []
        for i in range(period - 1, len(prices)):
            ma = sum(prices[i - period + 1:i + 1]) / period
            ma_values.append(ma)
        
        return ma_values
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return []
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        rsi_values = []
        for i in range(period - 1, len(gains)):
            avg_gain = sum(gains[i - period + 1:i + 1]) / period
            avg_loss = sum(losses[i - period + 1:i + 1]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, Any]:
        """计算MACD指标"""
        if len(prices) < 26:
            return {'dif': 0, 'dea': 0, 'histogram': 0}
        
        # 计算EMA
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)
        
        if not ema12 or not ema26:
            return {'dif': 0, 'dea': 0, 'histogram': 0}
        
        # 计算DIF
        dif = [ema12[i] - ema26[i] for i in range(len(ema26))]
        
        # 计算DEA (DIF的9日EMA)
        dea = self._calculate_ema(dif, 9)
        
        if not dea:
            return {'dif': dif[-1] if dif else 0, 'dea': 0, 'histogram': 0}
        
        # 计算MACD柱状图
        histogram = dif[-1] - dea[-1] if dea else 0
        
        return {
            'dif': dif[-1] if dif else 0,
            'dea': dea[-1] if dea else 0,
            'histogram': histogram
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算指数移动平均线"""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = [prices[0]]  # 第一个EMA值等于第一个价格
        
        for i in range(1, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    def _analyze_price_trend(self, prices: List[float], ma20: List[float]) -> str:
        """分析价格趋势"""
        if not prices or not ma20 or len(prices) < 5:
            return "无明确趋势"
        
        current_price = prices[-1]
        current_ma20 = ma20[-1] if ma20 else current_price
        
        # 价格与均线比较
        if current_price > current_ma20 * 1.02:
            return "强势上涨"
        elif current_price > current_ma20:
            return "温和上涨"
        elif current_price < current_ma20 * 0.98:
            return "弱势下跌"
        else:
            return "震荡整理"
    
    def _analyze_volume_trend(self, volumes: List[int]) -> str:
        """分析成交量趋势"""
        if not volumes or len(volumes) < 5:
            return "成交量不足"
        
        recent_avg = sum(volumes[-5:]) / 5
        historical_avg = sum(volumes[:-5]) / max(1, len(volumes) - 5)
        
        if recent_avg > historical_avg * 1.5:
            return "放量"
        elif recent_avg < historical_avg * 0.7:
            return "缩量"
        else:
            return "量能平稳"
    
    async def change_time_period(self, period: str) -> bool:
        """切换时间周期"""
        try:
            if period not in TIME_PERIODS:
                self.logger.error(f"不支持的时间周期: {period}")
                return False
            
            if period == self.current_time_period:
                return True
            
            self.current_time_period = period
            self.logger.info(f"切换到时间周期: {period}")
            
            # 重新加载当前股票的K线数据
            if self.current_stock_code:
                await self.load_analysis_data(self.current_stock_code)
            
            return True
            
        except Exception as e:
            self.logger.error(f"切换时间周期失败: {e}")
            return False
    
    async def _start_stock_update_tasks(self, stock_code: str):
        """启动指定股票的实时更新任务"""
        try:
            # 如果该股票的任务已经在运行，跳过
            if stock_code in self.stock_tasks:
                running_tasks = [task for task in self.stock_tasks[stock_code].values() 
                               if task and not task.done()]
                if running_tasks:
                    self.logger.info(f"股票 {stock_code} 的实时更新任务已在运行")
                    return
            
            # 初始化该股票的任务字典
            if stock_code not in self.stock_tasks:
                self.stock_tasks[stock_code] = {'realtime': None, 'orderbook': None, 'tick': None}
            
            # 启动五档数据更新任务
            self.stock_tasks[stock_code]['orderbook'] = asyncio.create_task(
                self._orderbook_update_loop(stock_code)
            )
            
            # 启动逐笔数据更新任务
            self.stock_tasks[stock_code]['tick'] = asyncio.create_task(
                self._tick_update_loop(stock_code)
            )
            
            self.logger.info(f"股票 {stock_code} 的实时更新任务启动")
            
        except Exception as e:
            self.logger.error(f"启动股票 {stock_code} 更新任务失败: {e}")
    
    async def _stop_stock_update_tasks(self, stock_code: str):
        """停止指定股票的实时更新任务"""
        try:
            if stock_code not in self.stock_tasks:
                return
            
            tasks = list(self.stock_tasks[stock_code].values())
            
            for task in tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 清空该股票的任务
            del self.stock_tasks[stock_code]
            
            self.logger.info(f"股票 {stock_code} 的实时更新任务停止")
        
        except Exception as e:
            self.logger.error(f"停止股票 {stock_code} 更新任务失败: {e}")
    
    async def _stop_update_tasks(self):
        """停止所有实时更新任务"""
        try:
            for stock_code in list(self.stock_tasks.keys()):
                await self._stop_stock_update_tasks(stock_code)
            
            self.logger.info("所有分析页面更新任务已停止")
            
        except Exception as e:
            self.logger.error(f"停止更新任务失败: {e}")
    
    async def _orderbook_update_loop(self, stock_code: str):
        """五档数据更新循环"""
        while True:
            try:
                # 检查股票是否仍在活跃集合中
                if stock_code not in self.active_stocks:
                    self.logger.info(f"股票 {stock_code} 已不再活跃，停止五档数据更新")
                    break
                    
                loop = asyncio.get_event_loop()
                orderbook_data = await loop.run_in_executor(
                    None, self._get_orderbook_data, stock_code
                )
                    
                # 更新缓存
                if stock_code in self.analysis_data_cache:
                    self.analysis_data_cache[stock_code].orderbook_data = orderbook_data
                    self.analysis_data_cache[stock_code].last_update = datetime.now()
                
                await asyncio.sleep(ORDERBOOK_REFRESH_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"五档数据更新错误: {e}")
                await asyncio.sleep(ORDERBOOK_REFRESH_SEC)
    
    async def _tick_update_loop(self, stock_code: str):
        """逐笔数据更新循环"""
        while True:
            try:
                # 检查股票是否仍在活跃集合中
                if stock_code not in self.active_stocks:
                    self.logger.info(f"股票 {stock_code} 已不再活跃，停止逐笔数据更新")
                    break
                    
                loop = asyncio.get_event_loop()
                tick_data = await loop.run_in_executor(
                    None, self._get_tick_data, stock_code, 20
                )
                    
                # 更新缓存
                if stock_code in self.analysis_data_cache:
                    self.analysis_data_cache[stock_code].tick_data = tick_data
                    self.analysis_data_cache[stock_code].last_update = datetime.now()
                
                await asyncio.sleep(TICK_REFRESH_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"逐笔数据更新错误: {e}")
                await asyncio.sleep(TICK_REFRESH_SEC)
    
    def get_current_analysis_data(self) -> Optional[AnalysisDataSet]:
        """获取当前分析数据"""
        if self.current_stock_code and self.current_stock_code in self.analysis_data_cache:
            return self.analysis_data_cache[self.current_stock_code]
        return None
    
    async def cleanup_stock_data(self, stock_code: str):
        """清理指定股票的分析数据和停止其实时更新任务"""
        try:
            # 从活跃股票集合中移除
            self.active_stocks.discard(stock_code)
            
            # 停止该股票的实时更新任务
            await self._stop_stock_update_tasks(stock_code)
            
            # 如果是当前分析的股票，清空当前股票标记
            if self.current_stock_code == stock_code:
                self.current_stock_code = None
                self.logger.info(f"已清空当前分析股票标记: {stock_code}")
            
            # 从缓存中删除该股票的数据
            if stock_code in self.analysis_data_cache:
                del self.analysis_data_cache[stock_code]
                self.logger.debug(f"已从缓存中删除股票 {stock_code} 的分析数据")
            
            # 从K线缓存中删除该股票的数据
            if stock_code in self.kline_cache:
                del self.kline_cache[stock_code]
                self.logger.debug(f"已从K线缓存中删除股票 {stock_code} 的数据")
            
            self.logger.info(f"股票 {stock_code} 的分析数据和任务清理完成")
            
        except Exception as e:
            self.logger.error(f"清理股票 {stock_code} 分析数据失败: {e}")
    
    async def cleanup(self):
        """清理分析数据管理器"""
        try:
            await self._stop_update_tasks()
            self.analysis_data_cache.clear()
            self.kline_cache.clear()
            self.current_stock_code = None
            self.logger.info("AnalysisDataManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"AnalysisDataManager 清理失败: {e}")
    
