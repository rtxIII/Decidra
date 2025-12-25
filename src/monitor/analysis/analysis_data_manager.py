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
from textual import work
from base.monitor import StockData, MarketStatus, ConnectionStatus
from base.futu_class import KLineData, OrderBookData, BrokerQueueData
from modules.futu_market import FutuMarket
from utils.global_vars import get_logger
from utils.global_vars import PATH_DATA

# 时间周期常量
TIME_PERIODS = {
    'D': 'K_DAY',      # 日线
    'W': 'K_WEEK',     # 周线  
    'M': 'K_MON'       # 月线
}

# 数据缓存配置
KLINE_CACHE_DAYS = 90      # K线数据缓存天数
KLINE_REFRESH_SEC = 60     # K线数据刷新间隔(秒) - 1分钟更新一次
ORDERBOOK_REFRESH_SEC = 3   # 五档数据刷新间隔(秒)
TICK_REFRESH_SEC = 1        # 逐笔数据刷新间隔(秒)
BASIC_INFO_REFRESH_SEC = 1  # 基础信息刷新间隔(秒)


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
        
        # 按股票代码管理的实时更新任务
        self.stock_tasks: Dict[str, Dict[str, Optional[asyncio.Task]]] = {}  
        # 结构: {stock_code: {'realtime': task, 'orderbook': task, 'tick': task}}
        
        # 活跃股票集合（有标签页打开的股票）
        self.active_stocks: set = set()
        
        # 缓存上次的格式化数据值，用于检测变化并实现闪烁效果
        self.last_formatted_values: Dict[str, Dict[str, str]] = {}  # {stock_code: {data_type: formatted_value}}

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

            # 获取资金流向数据
            capital_flow = await self._get_capital_flow_data(_stock_code)

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
            # 直接从API获取K线数据，不使用缓存
            kline_type = TIME_PERIODS.get(period, 'K_DAY')
            self.logger.debug(f"获取K线数据: stock={stock_code}, period={kline_type}, num={num}")

            # 首先尝试获取当前K线数据
            kline_data = self.futu_market.get_cur_kline(
                [stock_code], num=num, ktype=kline_type
            )

            if kline_data and len(kline_data) > 0:
                self.logger.debug(f"通过get_cur_kline成功获取{len(kline_data)}条K线数据")
                return kline_data
            else:
                # get_cur_kline返回空数据，尝试使用历史K线数据作为回退
                self.logger.warning(f"get_cur_kline返回空数据，尝试使用历史K线数据: {stock_code}")
                return self._get_history_kline_fallback(stock_code, kline_type, num)

        except Exception as e:
            self.logger.error(f"获取K线数据失败: stock={stock_code}, period={period}, error={e}")
            # 异常情况下也尝试使用历史数据
            try:
                return self._get_history_kline_fallback(stock_code, TIME_PERIODS.get(period, 'K_DAY'), num)
            except Exception as fallback_e:
                self.logger.error(f"历史K线数据回退也失败: {fallback_e}")
                return []

    def _get_history_kline_fallback(self, stock_code: str, kline_type: str, num: int = 100) -> List[KLineData]:
        """使用历史K线数据作为回退方案"""
        try:
            from datetime import datetime, timedelta

            # 计算日期范围：从今天往前推num天
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=num + 30)).strftime('%Y-%m-%d')  # 多取30天确保有足够数据

            self.logger.debug(f"尝试获取历史K线数据: {stock_code}, {start_date} ~ {end_date}, type={kline_type}")

            # 调用富途API的历史K线接口
            history_klines = self.futu_market.client.quote.get_history_kline(
                stock_code, start_date, end_date, kline_type, autype="qfq"
            )

            if history_klines and len(history_klines) > 0:
                # 只取最近的num条数据
                recent_klines = history_klines[-num:] if len(history_klines) > num else history_klines
                self.logger.info(f"通过历史K线数据成功获取{len(recent_klines)}条数据（共{len(history_klines)}条）")
                return recent_klines
            else:
                self.logger.warning(f"历史K线数据也为空: {stock_code}")
                return []

        except Exception as e:
            self.logger.error(f"获取历史K线数据失败: {stock_code}, error={e}")
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

    async def _get_capital_flow_data(self, stock_code: str) -> Dict[str, Any]:
        """获取资金流向数据

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 资金流向数据字典，包含主力、超大单、大单、中单、小单等
        """
        try:
            loop = asyncio.get_event_loop()
            capital_flow_list = await loop.run_in_executor(
                None, self.futu_market.get_capital_flow, stock_code, "INTRADAY"
            )

            if not capital_flow_list or len(capital_flow_list) == 0:
                self.logger.debug(f"股票 {stock_code} 无资金流向数据")
                return {}

            # 获取最新的资金流向数据（列表中的最后一条）
            latest_flow = capital_flow_list[-1]

            capital_flow = {
                'main_in_flow': getattr(latest_flow, 'main_in_flow', 0),
                'super_in_flow': getattr(latest_flow, 'super_in_flow', 0),
                'big_in_flow': getattr(latest_flow, 'big_in_flow', 0),
                'mid_in_flow': getattr(latest_flow, 'mid_in_flow', 0),
                'sml_in_flow': getattr(latest_flow, 'sml_in_flow', 0),
                'capital_flow_item_time': getattr(latest_flow, 'capital_flow_item_time', ''),
                'last_valid_time': getattr(latest_flow, 'last_valid_time', '')
            }

            self.logger.info(f"✓ 成功获取股票 {stock_code} 资金流向: 主力净流入={capital_flow['main_in_flow']:.2f}")
            return capital_flow

        except Exception as e:
            self.logger.error(f"获取资金流向数据失败: {e}")
            return {}

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
        """启动指定股票的实时更新任务（仅在交易时间内启动）"""
        try:
            # 如果该股票的任务已经在运行，跳过
            if stock_code in self.stock_tasks:
                running_tasks = [task for task in self.stock_tasks[stock_code].values() 
                               if task and not task.done()]
                if running_tasks:
                    self.logger.info(f"股票 {stock_code} 的实时更新任务已在运行")
                    return
            
            # 检查市场状态，只有在交易时间内才启动实时更新任务
            is_trading_time = await self._check_market_trading_status(stock_code)
            if not is_trading_time:
                self.logger.info(f"股票 {stock_code} 不在交易时间内，跳过启动实时更新任务")
                return
            
            # 初始化该股票的任务字典
            if stock_code not in self.stock_tasks:
                self.stock_tasks[stock_code] = {'realtime': None, 'orderbook': None, 'tick': None, 'basic_info': None, 'kline': None}
            
            # 启动K线数据更新任务
            self.stock_tasks[stock_code]['kline'] = asyncio.create_task(
                self._kline_update_loop(stock_code)
            )
            
            # 启动五档数据更新任务
            self.stock_tasks[stock_code]['orderbook'] = asyncio.create_task(
                self._orderbook_update_loop(stock_code)
            )
            
            # 启动逐笔数据更新任务
            self.stock_tasks[stock_code]['tick'] = asyncio.create_task(
                self._tick_update_loop(stock_code)
            )
            
            # 启动基础信息数据更新任务
            self.stock_tasks[stock_code]['basic_info'] = asyncio.create_task(
                self._basic_info_update_loop(stock_code)
            )
            
            self.logger.info(f"股票 {stock_code} 的实时更新任务启动（交易时间内）")
            
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

    async def _basic_info_update_loop(self, stock_code: str):
        """基础信息数据更新循环"""
        while True:
            try:
                # 检查股票是否仍在活跃集合中
                if stock_code not in self.active_stocks:
                    self.logger.info(f"股票 {stock_code} 已不再活跃，停止基础信息数据更新")
                    break
                    
                loop = asyncio.get_event_loop()
                basic_info = await loop.run_in_executor(
                    None, self._get_stock_basic_info, stock_code
                )
                    
                # 更新缓存
                if stock_code in self.analysis_data_cache:
                    self.analysis_data_cache[stock_code].basic_info = basic_info
                    self.analysis_data_cache[stock_code].last_update = datetime.now()
                
                await asyncio.sleep(BASIC_INFO_REFRESH_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"基础信息数据更新错误: {e}")
                await asyncio.sleep(BASIC_INFO_REFRESH_SEC)

    async def _kline_update_loop(self, stock_code: str):
        """K线数据更新循环"""
        while True:
            try:
                # 检查股票是否仍在活跃集合中
                if stock_code not in self.active_stocks:
                    self.logger.info(f"股票 {stock_code} 已不再活跃，停止K线数据更新")
                    break
                    
                loop = asyncio.get_event_loop()
                kline_data = await loop.run_in_executor(
                    None, self._get_kline_data, stock_code, self.current_time_period, 100
                )
                    
                # 更新缓存和重新计算技术指标
                if stock_code in self.analysis_data_cache:
                    self.analysis_data_cache[stock_code].kline_data = kline_data
                    
                    # 重新计算技术指标
                    technical_indicators = await self._calculate_technical_indicators(kline_data)
                    self.analysis_data_cache[stock_code].technical_indicators = technical_indicators
                    
                    self.analysis_data_cache[stock_code].last_update = datetime.now()
                    self.logger.debug(f"K线数据已更新: {stock_code}, 数据量: {len(kline_data)}")
                
                await asyncio.sleep(KLINE_REFRESH_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"K线数据更新错误: {e}")
                await asyncio.sleep(KLINE_REFRESH_SEC)
    
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
            
            
            self.logger.info(f"股票 {stock_code} 的分析数据和任务清理完成")
            
        except Exception as e:
            self.logger.error(f"清理股票 {stock_code} 分析数据失败: {e}")
    
    async def cleanup(self):
        """清理分析数据管理器"""
        try:
            await self._stop_update_tasks()
            self.analysis_data_cache.clear()
            self.last_formatted_values.clear()
            self.current_stock_code = None
            self.logger.info("AnalysisDataManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"AnalysisDataManager 清理失败: {e}")
    
    # ==================== 数据格式化方法 ====================
    
    def format_basic_info(self, analysis_data=None) -> str:
        """格式化基础信息显示文本"""
        if not analysis_data:
            return "等待股票数据加载..."
            
        basic_info = analysis_data.basic_info
        realtime_quote = analysis_data.realtime_quote
        
        # 提取基础信息
        stock_code = basic_info.get('code', '未知')
        stock_name = basic_info.get('name', '未知')
        last_price = basic_info.get('last_price', '未知')
        prev_close_price = basic_info.get('prev_close_price', '未知')
        volume = basic_info.get('volume', '未知')
        turnover = basic_info.get('turnover', '未知')
        turnover_rate = basic_info.get('turnover_rate', '未知')
        amplitude = basic_info.get('amplitude', '未知')
        listing_date = basic_info.get('listing_date', '未知')

        # 提取实时数据用于计算市值等
        current_price = realtime_quote.get('cur_price', 0)
        volume = realtime_quote.get('volume', 0)
        
        # 判断市场
        market_map = {
            'HK': '港交所',
            'US': '纳斯达克/纽交所', 
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所'
        }
        market = stock_code.split('.')[0] if '.' in stock_code else 'Unknown'
        market_name = market_map.get(market, '未知市场')
        
        # 格式化显示文本
        info_text = (
            f"股票代码: {stock_code}    "
            f"名称: {stock_name}    "
            f"最新价格: {last_price}    "
            f"昨收盘价格: {prev_close_price}    "
            f"成交金额: {turnover}    "
            f"换手率: {turnover_rate}   "
            f"振幅: {amplitude}    "
        )
        
        if current_price > 0:
            market_cap = current_price * volume if volume > 0 else 0
            if market_cap > 100000000:  # 大于1亿
                market_cap_text = f"{market_cap/100000000:.1f}亿"
            else:
                market_cap_text = f"{market_cap/10000:.1f}万" if market_cap > 10000 else f"{market_cap:.0f}"
            info_text += f"当前价: {current_price:.2f}    市值估算: {market_cap_text}    "
            
        if listing_date and listing_date != '未知':
            info_text += f"上市日期: {listing_date}    "
            
        info_text += f"更新时间: {analysis_data.last_update.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return info_text
    
    def format_realtime_quote(self, analysis_data=None) -> str:
        """格式化实时报价信息"""
        if not analysis_data or not analysis_data.realtime_quote:
            return "等待实时报价数据..."
        
        quote = analysis_data.realtime_quote
        
        # 提取报价数据
        cur_price = quote.get('cur_price', 0)
        prev_close = quote.get('prev_close_price', 0)
        open_price = quote.get('open_price', 0)
        high_price = quote.get('high_price', 0)
        low_price = quote.get('low_price', 0)
        volume = quote.get('volume', 0)
        turnover = quote.get('turnover', 0)
        change_rate = quote.get('change_rate', 0)
        change_val = quote.get('change_val', 0)
        amplitude = quote.get('amplitude', 0)
        turnover_rate = quote.get('turnover_rate', 0)
        
        # 格式化涨跌显示
        change_color = "green" if change_val >= 0 else "red"
        change_symbol = "↑" if change_val >= 0 else "↓"
        
        # 格式化成交量显示
        if volume > 100000000:
            volume_str = f"{volume/100000000:.1f}亿手"
        elif volume > 10000:
            volume_str = f"{volume/10000:.1f}万手"
        else:
            volume_str = f"{volume}手"
        
        # 格式化成交额显示
        if turnover > 100000000:
            turnover_str = f"{turnover/100000000:.1f}亿"
        elif turnover > 10000:
            turnover_str = f"{turnover/10000:.1f}万"
        else:
            turnover_str = f"{turnover:.0f}"
        
        quote_text = (
            f"最新价: [{change_color}]{cur_price:.2f}[/{change_color}] {change_symbol}    "
            f"涨跌幅: [{change_color}]{change_rate:+.2f}%[/{change_color}]    "
            f"涨跌额: [{change_color}]{change_val:+.2f}[/{change_color}]    "
            f"开盘: {open_price:.2f}    "
            f"最高: {high_price:.2f}    "
            f"最低: {low_price:.2f}    "
            f"成交量: {volume_str}    "
            f"成交额: {turnover_str}    "
            f"换手率: {turnover_rate:.2f}%    "
            f"振幅: {amplitude:.2f}%"
        )
        
        return quote_text
    
    def format_orderbook_data(self, analysis_data=None) -> str:
        """格式化五档买卖盘数据"""
        if not analysis_data or not analysis_data.orderbook_data:
            return "等待五档数据..."
        
        orderbook = analysis_data.orderbook_data
        
        # 构建五档显示（简化为三档）
        orderbook_text = ""
        
        # 卖盘买盘（从上到下）
        if hasattr(orderbook, 'ask_price_1') and orderbook.ask_price_1 > 0:
            orderbook_text += f"[bold red]卖一: {orderbook.ask_price_1:.2f}  {orderbook.ask_volume_1}手[/bold red]    "
        if hasattr(orderbook, 'bid_price_1') and orderbook.bid_price_1 > 0:
            orderbook_text += f"[bold green]买一: {orderbook.bid_price_1:.2f}  {orderbook.bid_volume_1}手[/bold green]\n"

        if hasattr(orderbook, 'ask_price_2') and orderbook.ask_price_2 > 0:
            orderbook_text += f"[bold red]卖二: {orderbook.ask_price_2:.2f}  {orderbook.ask_volume_2}手[/bold red]    "
        if hasattr(orderbook, 'bid_price_2') and orderbook.bid_price_2 > 0:
            orderbook_text += f"[bold green]买二: {orderbook.bid_price_2:.2f}  {orderbook.bid_volume_2}手[/bold green]\n"

        if hasattr(orderbook, 'ask_price_3') and orderbook.ask_price_3 > 0:
            orderbook_text += f"[bold red]卖三: {orderbook.ask_price_3:.2f}  {orderbook.ask_volume_3}手[/bold red]    "
        if hasattr(orderbook, 'bid_price_3') and orderbook.bid_price_3 > 0:
            orderbook_text += f"[bold green]买三: {orderbook.bid_price_3:.2f}  {orderbook.bid_volume_3}手[/bold green]\n"

        if hasattr(orderbook, 'ask_price_4') and orderbook.ask_price_4 > 0:
            orderbook_text += f"[bold red]卖四: {orderbook.ask_price_4:.2f}  {orderbook.ask_volume_4}手[/bold red]    "
        if hasattr(orderbook, 'bid_price_4') and orderbook.bid_price_4 > 0:
            orderbook_text += f"[bold green]买四: {orderbook.bid_price_4:.2f}  {orderbook.bid_volume_4}手[/bold green]\n"

        if hasattr(orderbook, 'ask_price_5') and orderbook.ask_price_5 > 0:
            orderbook_text += f"[bold red]卖五: {orderbook.ask_price_5:.2f}  {orderbook.ask_volume_5}手[/bold red]    "
        if hasattr(orderbook, 'bid_price_5') and orderbook.bid_price_5 > 0:
            orderbook_text += f"[bold green]买五: {orderbook.bid_price_5:.2f}  {orderbook.bid_volume_5}手[/bold green]\n"

        #orderbook_text += "──────────────────\n"
        
        
        # 计算委比和委差
        total_bid_vol = (getattr(orderbook, 'bid_volume_1', 0) + 
                        getattr(orderbook, 'bid_volume_2', 0) + 
                        getattr(orderbook, 'bid_volume_3', 0) +
                        getattr(orderbook, 'bid_volume_4', 0) +
                        getattr(orderbook, 'bid_volume_5', 0) +
                        getattr(orderbook, 'bid_volume_6', 0) +
                        getattr(orderbook, 'bid_volume_7', 0) +
                        getattr(orderbook, 'bid_volume_8', 0) +
                        getattr(orderbook, 'bid_volume_9', 0) +
                        getattr(orderbook, 'bid_volume_10', 0)
                        )
        total_ask_vol = (getattr(orderbook, 'ask_volume_1', 0) + 
                        getattr(orderbook, 'ask_volume_2', 0) + 
                        getattr(orderbook, 'ask_volume_3', 0) +
                        getattr(orderbook, 'ask_volume_4', 0) +
                        getattr(orderbook, 'ask_volume_5', 0) +
                        getattr(orderbook, 'ask_volume_6', 0) +
                        getattr(orderbook, 'ask_volume_7', 0) +
                        getattr(orderbook, 'ask_volume_8', 0) +
                        getattr(orderbook, 'ask_volume_9', 0) +
                        getattr(orderbook, 'ask_volume_10', 0)
                        ) 
        
        if (total_bid_vol + total_ask_vol) > 0:
            wei_bi = ((total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)) * 100
            wei_cha = total_bid_vol - total_ask_vol
            
            if wei_cha > 10000:
                wei_cha_str = f"{wei_cha/10000:.1f}万手"
            else:
                wei_cha_str = f"{wei_cha}手"
            
            orderbook_text += f"📈 委比: {wei_bi:+.1f}%    "
            orderbook_text += f"📊 委差: {wei_cha_str}"
        
        return orderbook_text
    
    def format_tick_data(self, analysis_data=None) -> str:
        """格式化逐笔交易数据"""
        if not analysis_data or not analysis_data.tick_data:
            return "等待逐笔数据..."
        
        tick_data = analysis_data.tick_data
        
        if not tick_data or len(tick_data) == 0:
            return "暂无逐笔数据"
        
        tick_text = "[bold yellow]逐笔数据[/bold yellow]\n"
        
        # 显示最新的4-5笔交易
        recent_ticks = tick_data[:5] if len(tick_data) >= 5 else tick_data
        
        for tick in recent_ticks:
            time_str = tick.get('time', '')[:8]  # 只显示时分秒
            price = tick.get('price', 0)
            volume = tick.get('volume', 0)
            direction = tick.get('ticker_direction', '')
            
            # 根据买卖方向显示箭头和颜色
            if direction == 'BUY':
                direction_symbol = "[green]↑[/green]"
            elif direction == 'SELL':
                direction_symbol = "[red]↓[/red]"
            else:
                direction_symbol = "─"
            
            tick_text += f"{time_str}  {price:.2f}{direction_symbol}  {volume}手\n"
        
        return tick_text.rstrip('\n')
    
    def format_broker_queue(self, analysis_data=None) -> str:
        """格式化经纪队列数据"""
        if not analysis_data or not analysis_data.broker_queue:
            return "等待经纪队列数据..."
        
        broker = analysis_data.broker_queue
        
        # 检查是否为字典格式且包含必要的字段
        if not isinstance(broker, dict) or 'bid_frame_table' not in broker or 'ask_frame_table' not in broker:
            return "经纪队列数据格式异常"
        
        broker_text = "[bold cyan]经纪队列[/bold cyan]\n"
        
        # 处理买方队列
        bid_table = broker.get('bid_frame_table', {})
        if bid_table and 'bid_broker_pos' in bid_table and 'bid_broker_name' in bid_table:
            broker_text += "[green]买方队列:[/green]\n"
            bid_positions = self._group_brokers_by_position(
                bid_table.get('bid_broker_pos', {}),
                bid_table.get('bid_broker_name', {})
            )
            for pos in sorted(bid_positions.keys()):
                brokers = ', '.join(bid_positions[pos][:3])  # 最多显示3个经纪商
                broker_text += f"  {pos}档: {brokers}\n"
        else:
            broker_text += "[green]买方队列:[/green] 暂无数据\n"
        
        # 处理卖方队列
        ask_table = broker.get('ask_frame_table', {})
        if ask_table and 'ask_broker_pos' in ask_table and 'ask_broker_name' in ask_table:
            broker_text += "[red]卖方队列:[/red]\n"
            ask_positions = self._group_brokers_by_position(
                ask_table.get('ask_broker_pos', {}),
                ask_table.get('ask_broker_name', {})
            )
            for pos in sorted(ask_positions.keys()):
                brokers = ', '.join(ask_positions[pos][:3])  # 最多显示3个经纪商
                broker_text += f"  {pos}档: {brokers}"
                if pos < max(ask_positions.keys()):
                    broker_text += "\n"
        else:
            broker_text += "[red]卖方队列:[/red] 暂无数据"
        
        return broker_text
    
    def _group_brokers_by_position(self, positions, names):
        """按档位分组经纪商"""
        grouped = {}
        for idx, pos in positions.items():
            if pos not in grouped:
                grouped[pos] = set()
            if idx in names:
                broker_name = names[idx]
                # 简化经纪商名称显示
                simplified_name = self._simplify_broker_name(broker_name)
                grouped[pos].add(simplified_name)
        
        # 转换为列表并去重
        for pos in grouped:
            grouped[pos] = list(grouped[pos])
        
        return grouped
    
    def _simplify_broker_name(self, full_name):
        """简化经纪商名称以便显示"""
        # 移除常见后缀
        name = full_name.replace('有限公司', '').replace('(香港)', '').replace('证券', '')
        # 如果名称太长，截取前8个字符
        if len(name) > 8:
            name = name[:8] + '...'
        return name
    
    async def format_capital_flow(self, analysis_data=None) -> str:
        """格式化资金流向数据"""
        if not analysis_data or not analysis_data.capital_flow:
            # 如果没有资金流向数据，调用真实API获取资金流向信息
            return await self._generate_estimated_capital_flow(analysis_data)
        
        capital = analysis_data.capital_flow
        
        # 这里应该根据实际的资金流向数据结构进行格式化
        # 由于当前capital_flow为空字典，我们调用真实API获取数据
        return await self._generate_estimated_capital_flow(analysis_data)
    
    async def _generate_estimated_capital_flow(self, analysis_data=None) -> str:
        """调用get_capital_flow API获取真实的资金流向信息"""
        if not analysis_data or not analysis_data.realtime_quote:
            return "等待资金流向数据..."
        
        stock_code = self.current_stock_code
        if not stock_code:
            return "等待股票代码..."
        
        try:
            # 调用真实的资金流向API
            loop = asyncio.get_event_loop()
            capital_flow_list = await loop.run_in_executor(
                None, self.futu_market.get_capital_flow, stock_code, "INTRADAY"
            )
            
            if not capital_flow_list:
                # 如果API返回空数据，则回退到基于技术指标的估算
                return self._fallback_estimated_capital_flow(analysis_data)
            
            # 获取最新的资金流向数据（列表中的最后一条）
            latest_flow = capital_flow_list[-1]
            
            # 格式化资金流向数据
            main_flow = latest_flow.main_in_flow
            super_flow = latest_flow.super_in_flow
            big_flow = latest_flow.big_in_flow
            mid_flow = latest_flow.mid_in_flow
            sml_flow = latest_flow.sml_in_flow
            
            # 判断流入流出方向
            main_flow_direction = "流入" if main_flow > 0 else "流出"
            main_flow_color = "green" if main_flow > 0 else "red"
            
            # 格式化数值显示
            def format_capital(value):
                abs_value = abs(value)
                if abs_value > 100000000:
                    return f"{value/100000000:.1f}亿"
                elif abs_value > 10000:
                    return f"{value/10000:.1f}万"
                else:
                    return f"{value:.0f}"
            
            main_flow_str = format_capital(main_flow)
            super_flow_str = format_capital(super_flow)
            big_flow_str = format_capital(big_flow)
            mid_flow_str = format_capital(mid_flow)
            sml_flow_str = format_capital(sml_flow)
            
            # 计算各类资金占比
            total_flow = abs(super_flow) + abs(big_flow) + abs(mid_flow) + abs(sml_flow)
            if total_flow > 0:
                super_pct = abs(super_flow) / total_flow * 100
                big_pct = abs(big_flow) / total_flow * 100
                mid_pct = abs(mid_flow) / total_flow * 100
                sml_pct = abs(sml_flow) / total_flow * 100
            else:
                super_pct = big_pct = mid_pct = sml_pct = 0
            
            # 活跃度评估（基于总流入流出金额）
            quote = analysis_data.realtime_quote
            turnover_rate = quote.get('turnover_rate', 0)
            
            if turnover_rate > 5:
                activity = "高"
                activity_stars = "★★★★★"
            elif turnover_rate > 3:
                activity = "中高"
                activity_stars = "★★★★☆"
            elif turnover_rate > 1:
                activity = "中等"
                activity_stars = "★★★☆☆"
            elif turnover_rate > 0.5:
                activity = "中低"
                activity_stars = "★★☆☆☆"
            else:
                activity = "低"
                activity_stars = "★☆☆☆☆"
            
            # 格式化时间信息
            time_info = ""
            if latest_flow.capital_flow_item_time:
                time_info = f"数据时间: {latest_flow.capital_flow_item_time}"
            elif latest_flow.last_valid_time:
                time_info = f"更新时间: {latest_flow.last_valid_time}"
            
            # 构建显示文本
            capital_text = (
                f"主力净{main_flow_direction}: [{main_flow_color}]{main_flow_str}[/{main_flow_color}]    "
                f"超大单: {super_flow_str}({super_pct:.1f}%)    大单: {big_flow_str}({big_pct:.1f}%)    "
                f"中单: {mid_flow_str}({mid_pct:.1f}%)    小单: {sml_flow_str}({sml_pct:.1f}%)    │    "
                f"活跃度: {activity}    热度: {activity_stars}"
            )
            
            if time_info:
                capital_text += f"    {time_info}"
            
            # 添加技术指标信息
            tech_text = self._format_technical_indicators_for_money_flow(analysis_data)
            if tech_text:
                capital_text += f"\n{tech_text}"
            
            return capital_text
            
        except Exception as e:
            self.logger.error(f"获取资金流向数据失败: {e}")
            # 发生异常时回退到估算方法
            return self._fallback_estimated_capital_flow(analysis_data)
    
    def _fallback_estimated_capital_flow(self, analysis_data) -> str:
        """回退的估算资金流向方法"""
        quote = analysis_data.realtime_quote
        change_rate = quote.get('change_rate', 0)
        turnover = quote.get('turnover', 0)
        turnover_rate = quote.get('turnover_rate', 0)
        
        # 基于涨跌幅和成交量估算资金流向
        if change_rate > 0:
            main_flow_direction = "流入"
            main_flow_color = "green"
        else:
            main_flow_direction = "流出"
            main_flow_color = "red"
        
        # 估算主力资金（基于成交额的一定比例）
        estimated_main_flow = turnover * 0.3  # 假设主力资金占30%
        
        if estimated_main_flow > 100000000:
            main_flow_str = f"{estimated_main_flow/100000000:.1f}亿"
        elif estimated_main_flow > 10000:
            main_flow_str = f"{estimated_main_flow/10000:.1f}万"
        else:
            main_flow_str = f"{estimated_main_flow:.0f}"
        
        # 活跃度评估
        if turnover_rate > 5:
            activity = "高"
            activity_stars = "★★★★★"
        elif turnover_rate > 3:
            activity = "中高"
            activity_stars = "★★★★☆"
        elif turnover_rate > 1:
            activity = "中等"
            activity_stars = "★★★☆☆"
        elif turnover_rate > 0.5:
            activity = "中低"
            activity_stars = "★★☆☆☆"
        else:
            activity = "低"
            activity_stars = "★☆☆☆☆"
        
        capital_text = (
            f"主力净{main_flow_direction}: [{main_flow_color}]{main_flow_str}[/{main_flow_color}](估算)    "
            f"超大单: 估算中    大单: 估算中    中单: 估算中    小单: 估算中    │    "
            f"活跃度: {activity}    热度: {activity_stars}"
        )
        
        # 添加技术指标信息
        tech_text = self._format_technical_indicators_for_money_flow(analysis_data)
        if tech_text:
            capital_text += f"\n{tech_text}"
        
        return capital_text
    
    def _format_technical_indicators_for_money_flow(self, analysis_data) -> str:
        """格式化技术指标信息用于资金流向区域显示"""
        if not analysis_data or not hasattr(analysis_data, 'technical_indicators') or not analysis_data.technical_indicators:
            return ""
        
        tech_indicators = analysis_data.technical_indicators
        tech_text = "📊 技术指标: "
        
        # MA移动平均线
        ma_parts = []
        for ma_period in ['ma5', 'ma10', 'ma20', 'ma60']:
            if tech_indicators.get(ma_period):
                ma_parts.append(f"{ma_period.upper()}: {tech_indicators[ma_period]:.2f}")
        
        if ma_parts:
            tech_text += "  ".join(ma_parts) + "    "
        
        # RSI指标
        if tech_indicators.get('rsi'):
            rsi_value = tech_indicators['rsi']
            if rsi_value > 70:
                rsi_status = "[red]超买[/red]"
            elif rsi_value < 30:
                rsi_status = "[green]超卖[/green]"
            else:
                rsi_status = "正常"
            tech_text += f"RSI(14): {rsi_value:.1f}({rsi_status})    "
        
        # MACD指标
        if tech_indicators.get('macd') and isinstance(tech_indicators['macd'], dict):
            macd_data = tech_indicators['macd']
            dif = macd_data.get('dif', 0)
            dea = macd_data.get('dea', 0)
            histogram = macd_data.get('histogram', 0)
            
            # 判断金叉死叉
            if dif > dea:
                macd_trend = "[green]金叉[/green]" if histogram > 0 else "[yellow]转强[/yellow]"
            else:
                macd_trend = "[red]死叉[/red]" if histogram < 0 else "[yellow]转弱[/yellow]"
            
            tech_text += f"MACD: DIF({dif:.3f}) DEA({dea:.3f}) 柱({histogram:.3f}) {macd_trend}    "
        
        # 趋势分析
        trend_parts = []
        if tech_indicators.get('price_trend'):
            price_trend = tech_indicators['price_trend']
            if "上升" in price_trend or "上涨" in price_trend:
                trend_parts.append(f"价格: [green]{price_trend}[/green]")
            elif "下降" in price_trend or "下跌" in price_trend:
                trend_parts.append(f"价格: [red]{price_trend}[/red]")
            else:
                trend_parts.append(f"价格: {price_trend}")
        
        if tech_indicators.get('volume_trend'):
            volume_trend = tech_indicators['volume_trend']
            if "放量" in volume_trend or "增加" in volume_trend:
                trend_parts.append(f"成交量: [blue]{volume_trend}[/blue]")
            elif "缩量" in volume_trend or "减少" in volume_trend:
                trend_parts.append(f"成交量: [dim]{volume_trend}[/dim]")
            else:
                trend_parts.append(f"成交量: {volume_trend}")
        
        if trend_parts:
            tech_text += "    ".join(trend_parts)
        
        return tech_text
    
    # ==================== 市场状态检查方法 ====================
    
    async def _check_market_trading_status(self, stock_code: str) -> bool:
        """
        检查股票所在市场是否处于交易时间
        
        Args:
            stock_code: 股票代码 (如 HK.00700, US.AAPL)
            
        Returns:
            bool: True表示处于交易时间，False表示非交易时间
        """
        try:
            # 获取市场状态
            loop = asyncio.get_event_loop()
            market_states = await loop.run_in_executor(
                None, self.futu_market.get_market_state, [stock_code]
            )
            
            if not market_states or len(market_states) == 0:
                self.logger.warning(f"未能获取股票 {stock_code} 的市场状态，默认为非交易时间")
                return False
            
            market_state = market_states[0].market_state
            
            # 定义交易时间的市场状态
            trading_states = {
                'OPEN',           # 开盘
                'TRADING',        # 交易中
                'MORNING',        # 上午时段
                'AFTERNOON',      # 下午时段
                'PRE_MARKET_BEGIN', # 盘前开始
                'AUCTION',        # 集合竞价
                'UNKNOWN_STATUS'  # 未知状态（保守判断为开盘）
            }
            
            # 检查是否处于交易时间
            is_trading = market_state in trading_states
            
            self.logger.info(f"股票 {stock_code} 市场状态: {market_state}, 是否交易时间: {is_trading}")
            
            return is_trading
            
        except Exception as e:
            self.logger.error(f"检查股票 {stock_code} 市场状态失败: {e}")
            # 出错时保守地返回False，避免在非交易时间启动实时更新
            return False
    
    # ==================== 闪烁效果支持方法 ====================
    
    def get_formatted_data_with_flash(self, stock_code: str, data_type: str, formatted_value: str) -> Tuple[str, bool]:
        """
        检测数据变化并返回是否需要闪烁效果
        
        Args:
            stock_code: 股票代码
            data_type: 数据类型 (quote/orderbook/tick/capital)
            formatted_value: 格式化后的值
            
        Returns:
            (最终显示值, 是否需要闪烁)
        """
        try:
            # 创建缓存键
            if stock_code not in self.last_formatted_values:
                self.last_formatted_values[stock_code] = {}
            
            # 检查是否有变化
            last_value = self.last_formatted_values[stock_code].get(data_type)
            has_changed = last_value != formatted_value
            
            # 更新缓存
            self.last_formatted_values[stock_code][data_type] = formatted_value
            
            if has_changed and last_value is not None:
                self.logger.debug(f"数据变化检测: {stock_code}:{data_type} '{last_value[:50]}...' -> '{formatted_value[:50]}...'")
                # 数据有变化，需要闪烁
                flash_value = self._apply_flash_style(formatted_value, data_type)
                return flash_value, True
            else:
                # 数据无变化或首次设置，不闪烁
                return formatted_value, False
                
        except Exception as e:
            self.logger.error(f"检测数据变化失败: {e}")
            return formatted_value, False
    
    def _apply_flash_style(self, value: str, data_type: str) -> str:
        """
        应用闪烁样式
        
        Args:
            value: 原始值
            data_type: 数据类型
            
        Returns:
            应用了闪烁样式的值
        """
        try:
            # 根据数据类型选择不同的闪烁颜色
            if data_type == 'quote':
                # 报价数据使用黄色背景
                return f"[bold yellow on blue]{value}[/bold yellow on blue]"
            elif data_type == 'orderbook':
                # 五档数据使用蓝色背景
                return f"[bold white on blue]{value}[/bold white on blue]"
            elif data_type == 'tick':
                # 逐笔数据使用绿色背景
                return f"[bold white on green]{value}[/bold white on green]"
            elif data_type == 'capital':
                # 资金流向使用紫色背景
                return f"[bold white on magenta]{value}[/bold white on magenta]"
            else:
                # 默认使用蓝色背景
                return f"[bold white on blue]{value}[/bold white on blue]"
                
        except Exception as e:
            self.logger.error(f"应用闪烁样式失败: {e}")
            return value
    
    async def create_flash_restore_task(self, widget, original_value: str, delay: float = 0.5):
        """
        创建闪烁恢复任务
        
        Args:
            widget: 需要恢复的UI组件
            original_value: 原始值
            delay: 延迟时间（秒）
        """
        try:
            # 创建异步任务来恢复正常样式
            asyncio.create_task(self._restore_widget_normal_style(widget, original_value, delay))
            
        except Exception as e:
            self.logger.error(f"创建闪烁恢复任务失败: {e}")
    
    async def _restore_widget_normal_style(self, widget, original_value: str, delay: float):
        """
        恢复组件的正常样式
        
        Args:
            widget: UI组件
            original_value: 原始值
            delay: 延迟时间
        """
        try:
            # 等待指定时间
            await asyncio.sleep(delay)
            
            # 恢复正常样式
            if widget and hasattr(widget, 'update'):
                widget.update(original_value)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"恢复组件正常样式失败: {e}")
    
