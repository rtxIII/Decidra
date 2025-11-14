"""
富途行情管理器模块

负责处理所有行情相关的API调用，包括股票报价、K线数据、
实时数据订阅等功能。
"""

import logging
import threading
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING
from collections import defaultdict
from utils.global_vars import get_logger

if TYPE_CHECKING:
    from .futu_client import FutuClient

from base.futu_class import (
    FutuException, FutuConnectException, FutuQuoteException,
    StockInfo, KLineData, StockQuote, MarketSnapshot, TickerData, 
    OrderBookData, RTData, AuTypeInfo, PlateInfo, PlateStock,
    MarketState, CapitalFlow, CapitalDistribution, OwnerPlate, BrokerQueueData
)

try:
    import futu as ft
except ImportError:
    raise ImportError(
        "futu-api is required. Install it with: pip install futu-api"
    )


class QuoteManager:
    """富途行情数据管理器"""
    
    def __init__(self, client: 'FutuClient'):
        """
        初始化行情管理器
        
        Args:
            client: 富途客户端实例
        """
        self.client = client
        #self.logger = logging.getLogger(f"{__name__}.QuoteManager")
        self.logger = get_logger(__name__)
        # 订阅管理
        self._subscriptions: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
        # 订阅类型映射
        self._sub_type_map = {
            'quote': ft.SubType.QUOTE,           # 基础报价
            'kline_1m': ft.SubType.K_1M,         # 1分钟K线
            'kline_5m': ft.SubType.K_5M,         # 5分钟K线
            'kline_15m': ft.SubType.K_15M,       # 15分钟K线
            'kline_30m': ft.SubType.K_30M,       # 30分钟K线
            'kline_60m': ft.SubType.K_60M,       # 60分钟K线
            'kline_day': ft.SubType.K_DAY,       # 日K线
            'kline_week': ft.SubType.K_WEEK,     # 周K线
            'kline_month': ft.SubType.K_MON,     # 月K线
            'ticker': ft.SubType.TICKER,         # 逐笔数据
            'order_book': ft.SubType.ORDER_BOOK, # 买卖盘
            'rt_data': ft.SubType.RT_DATA,       # 分时数据
            'broker': ft.SubType.BROKER,         # 经纪队列
        }
    
    def _get_quote_context(self):
        """获取行情上下文"""
        if not self.client.is_connected:
            raise FutuConnectException(-1, "Client not connected")
        
        if self.client._quote_ctx is None:
            raise FutuConnectException(-1, "Quote context not available")
        
        return self.client._quote_ctx
    
    def _handle_response(self, ret_code: int, ret_data: Any, operation: str = "操作"):
        """处理富途API响应"""
        if ret_code != ft.RET_OK:
            error_msg = f"{operation}失败: {ret_data}"
            self.logger.error(error_msg)
            raise FutuQuoteException(ret_code, ret_data)
        
        # 处理DataFrame格式数据
        try:
            import pandas as pd
            if isinstance(ret_data, pd.DataFrame):
                # 处理DataFrame中的特殊数据类型
                if not ret_data.empty:
                    # 替换NaN值为None
                    ret_data = ret_data.where(pd.notnull(ret_data), None)
                    # 确保数据类型兼容性
                    for col in ret_data.columns:
                        if ret_data[col].dtype == 'object':
                            # 将字符串'nan'和'None'转换为None
                            ret_data[col] = ret_data[col].astype(str)
                            ret_data[col] = ret_data[col].replace(['nan', 'None', '<NA>'], None)
                
                # 对于特定API返回格式优化
                if operation in ["获取市场状态", "获取交易日历", "获取自选股分组", "获取自选股"]:
                    # 市场状态等特殊API可能需要特殊处理，保持DataFrame格式
                    return ret_data
                else:
                    # 多行数据返回DataFrame
                    return ret_data
            else:
                # 非DataFrame数据直接返回（如交易日历可能返回列表）
                return ret_data
        except ImportError:
            # 如果pandas不可用，直接返回原数据
            return ret_data
        except Exception as e:
            self.logger.warning(f"数据格式处理异常: {e}，返回原始数据")
            return ret_data
    
    # ================== 基础行情接口 ==================
    
    def get_stock_info(self, market: str = "HK", stock_type: str = "STOCK") -> List[StockInfo]:
        """
        获取股票基础信息
        
        Args:
            market: 市场代码 (HK/US/CN等)
            stock_type: 股票类型 (STOCK/WARRANT等)
        
        Returns:
            List[StockInfo]: 股票信息列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_stock_basicinfo(market, stock_type)
            
            df = self._handle_response(ret, data, "获取股票基础信息")
            
            # 转换为StockInfo对象列表
            stock_list = []
            for _, row in df.iterrows():
                stock_info = StockInfo.from_dict(row.to_dict())
                stock_list.append(stock_info)
            
            self.logger.info(f"获取到 {len(stock_list)} 只股票的基础信息")
            return stock_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取股票基础信息异常: {str(e)}")
    
    def get_stock_quote(self, codes: List[str]) -> List[StockQuote]:
        """
        获取股票实时报价
        
        Args:
            codes: 股票代码列表 (如 ["HK.00700", "HK.00388"])
        
        Returns:
            List[StockQuote]: 股票报价列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_stock_quote(codes)
            
            df = self._handle_response(ret, data, "获取股票报价")
            
            # 转换为StockQuote对象列表
            quote_list = []
            for _, row in df.iterrows():
                quote = StockQuote.from_dict(row.to_dict())
                quote_list.append(quote)
            
            self.logger.debug(f"获取到 {len(quote_list)} 只股票的实时报价")
            return quote_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取股票报价异常: {str(e)}")
    
    def get_market_snapshot(self, codes: List[str]) -> List[MarketSnapshot]:
        """
        获取市场快照
        
        Args:
            codes: 股票代码列表
        
        Returns:
            List[MarketSnapshot]: 市场快照列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_market_snapshot(codes)
            
            df = self._handle_response(ret, data, "获取市场快照")
            
            # 转换为MarketSnapshot对象列表
            snapshot_list = []
            for _, row in df.iterrows():
                snapshot = MarketSnapshot.from_dict(row.to_dict())
                snapshot_list.append(snapshot)
            
            self.logger.info(f"获取到 {len(snapshot_list)} 只股票的市场快照")
            return snapshot_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取市场快照异常: {str(e)}")
    
    # ================== K线数据接口 ==================
    
    def get_current_kline(self, 
                         code: str, 
                         ktype: str = "K_DAY", 
                         num: int = 100,
                         autype: str = "qfq") -> List[KLineData]:
        """
        获取当前K线数据
        
        Args:
            code: 股票代码 (如 "HK.00700")
            ktype: K线类型 (K_1M, K_5M, K_15M, K_30M, K_60M, K_DAY, K_WEEK, K_MON)
            num: 获取数量
            autype: 复权类型 (qfq-前复权, hfq-后复权, None-不复权)
        
        Returns:
            List[KLineData]: K线数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换ktype为富途API格式
            futu_ktype = getattr(ft.KLType, ktype, ft.KLType.K_DAY)
            
            # 转换autype为富途API格式
            if autype == "qfq":
                futu_autype = ft.AuType.QFQ
            elif autype == "hfq":
                futu_autype = ft.AuType.HFQ
            else:
                futu_autype = ft.AuType.NONE
            
            ret, data = quote_ctx.get_cur_kline(code, num, futu_ktype, futu_autype)
            
            df = self._handle_response(ret, data, f"获取{code}的K线数据")
            
            # 转换为KLineData对象列表
            kline_list = []
            for _, row in df.iterrows():
                kline = KLineData.from_dict(row.to_dict())
                kline_list.append(kline)
            
            self.logger.info(f"获取到 {code} 的 {len(kline_list)} 条K线数据")
            return kline_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取K线数据异常: {str(e)}")
    
    def get_history_kline(self, 
                         code: str,
                         start: str,
                         end: str, 
                         ktype: str = "K_DAY",
                         autype: str = "qfq",
                         fields: Optional[List[str]] = None) -> List[KLineData]:
        """
        获取历史K线数据
        
        Args:
            code: 股票代码
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
            ktype: K线类型
            autype: 复权类型
            fields: 指定字段
        
        Returns:
            List[KLineData]: K线数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换参数
            futu_ktype = getattr(ft.KLType, ktype, ft.KLType.K_DAY)
            
            if autype == "qfq":
                futu_autype = ft.AuType.QFQ
            elif autype == "hfq":
                futu_autype = ft.AuType.HFQ
            else:
                futu_autype = ft.AuType.NONE
            
            # 使用request_history_kline获取历史数据
            if fields:
                ret, data, page_req_key = quote_ctx.request_history_kline(code, start, end, futu_ktype, futu_autype, fields)
            else:
                ret, data, page_req_key = quote_ctx.request_history_kline(code, start, end, futu_ktype, futu_autype)
            
            df = self._handle_response(ret, data, f"获取{code}的历史K线数据")
            
            # 转换为KLineData对象列表
            kline_list = []
            for _, row in df.iterrows():
                kline_data = KLineData.from_dict(row.to_dict())
                kline_list.append(kline_data)
            
            self.logger.info(f"获取到{code}的 {len(kline_list)} 条历史K线数据")
            return kline_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取历史K线数据异常: {str(e)}")
    
    # ================== 实用方法 ==================
    
    def get_market_state(self, codes: List[str]) -> List[MarketState]:
        """
        获取标的市场状态
        
        Args:
            codes: 股票代码列表 (如 ["HK.00700", "HK.00388"])
        
        Returns:
            List[MarketState]: 市场状态列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_market_state(codes)
            
            df = self._handle_response(ret, data, "获取市场状态")
            
            # 转换为MarketState对象列表
            state_list = []
            for _, row in df.iterrows():
                market_state = MarketState.from_dict(row.to_dict())
                state_list.append(market_state)
            
            self.logger.info(f"获取到 {len(state_list)} 只股票的市场状态")
            return state_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取市场状态异常: {str(e)}")
    
    def get_capital_flow(self, 
                        code: str, 
                        period_type: str = "INTRADAY", 
                        start: Optional[str] = None, 
                        end: Optional[str] = None) -> List[CapitalFlow]:
        """
        获取资金流向
        
        Args:
            code: 股票代码 (如 "HK.00700")
            period_type: 周期类型 (INTRADAY/DAILY等)
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
        
        Returns:
            List[CapitalFlow]: 资金流向数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换周期类型为富途API格式
            if period_type == "INTRADAY":
                futu_period_type = ft.PeriodType.INTRADAY
            elif period_type == "DAILY":
                futu_period_type = ft.PeriodType.DAILY
            else:
                futu_period_type = ft.PeriodType.INTRADAY
            
            ret, data = quote_ctx.get_capital_flow(code, futu_period_type, start, end)
            
            df = self._handle_response(ret, data, f"获取{code}的资金流向")
            
            # 转换为CapitalFlow对象列表
            flow_list = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                row_dict['code'] = code  # 确保包含股票代码
                capital_flow = CapitalFlow.from_dict(row_dict)
                flow_list.append(capital_flow)
            
            self.logger.info(f"获取到 {code} 的 {len(flow_list)} 条资金流向数据")
            return flow_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取资金流向异常: {str(e)}")
    
    def get_capital_distribution(self, code: str) -> List[CapitalDistribution]:
        """
        获取资金分布
        
        Args:
            code: 股票代码 (如 "HK.00700")
        
        Returns:
            List[CapitalDistribution]: 资金分布数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 调用富途API
            ret, data = quote_ctx.get_capital_distribution(code)
            
            df = self._handle_response(ret, data, f"获取{code}的资金分布")
            
            if hasattr(df, 'empty') and df.empty:
                self.logger.warning(f"{code} 的资金分布数据为空")
                return []
            
            
            # 转换为CapitalDistribution对象列表
            distribution_list = []
            if hasattr(df, 'iterrows'):
                for idx, row in df.iterrows():
                    try:
                        row_dict = row.to_dict()
                        row_dict['code'] = code  # 确保包含股票代码
                        self.logger.debug(f"处理第{idx}行数据: {row_dict}")
                        capital_distribution = CapitalDistribution.from_dict(row_dict)
                        distribution_list.append(capital_distribution)
                    except Exception as row_error:
                        self.logger.error(f"处理第{idx}行数据时出错: {row_error}")
                        continue
            else:
                # 如果不是DataFrame格式，尝试直接处理
                self.logger.warning(f"返回数据不是DataFrame格式，尝试直接处理: {type(df)}")
                if isinstance(df, list):
                    for item in df:
                        try:
                            if isinstance(item, dict):
                                item['code'] = code
                                capital_distribution = CapitalDistribution.from_dict(item)
                                distribution_list.append(capital_distribution)
                        except Exception as item_error:
                            self.logger.error(f"处理列表项时出错: {item_error}")
                            continue
            
            self.logger.info(f"获取到 {code} 的 {len(distribution_list)} 条资金分布数据")
            return distribution_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取资金分布异常: {str(e)}")
    
    def get_owner_plate(self, codes: List[str]) -> List[OwnerPlate]:
        """
        获取股票所属板块
        
        Args:
            codes: 股票代码列表 (如 ["HK.00700", "HK.00388"])
        
        Returns:
            List[OwnerPlate]: 股票所属板块信息列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_owner_plate(codes)
            
            df = self._handle_response(ret, data, "获取股票所属板块")
            
            # 转换为OwnerPlate对象列表
            plate_list = []
            for _, row in df.iterrows():
                owner_plate = OwnerPlate.from_dict(row.to_dict())
                plate_list.append(owner_plate)
            
            self.logger.info(f"获取到 {len(plate_list)} 条股票板块信息")
            return plate_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取股票所属板块异常: {str(e)}")
    
    def request_history_kline(self, 
                             code: str,
                             start: Optional[str] = None,
                             end: Optional[str] = None, 
                             ktype: str = "K_DAY",
                             autype: str = "qfq",
                             fields: Optional[List[str]] = None,
                             max_count: int = 1000,
                             page_req_key: Optional[str] = None,
                             extended_time: bool = False,
                             session: str = "NONE") -> tuple:
        """
        获取历史K线数据（支持分页）
        
        Args:
            code: 股票代码
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
            ktype: K线类型 (K_1M, K_5M, K_15M, K_30M, K_60M, K_DAY, K_WEEK, K_MON)
            autype: 复权类型 (qfq-前复权, hfq-后复权, None-不复权)
            fields: 指定字段
            max_count: 单页最大数量
            page_req_key: 分页请求key
            extended_time: 是否包含盘前盘后
            session: 交易时段 (NONE/NORMAL/PRE_MARKET/AFTER_HOURS)
        
        Returns:
            Tuple[List[KLineData], Optional[str]]: (K线数据列表, 下一页请求key)
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换参数
            futu_ktype = getattr(ft.KLType, ktype, ft.KLType.K_DAY)
            
            if autype == "qfq":
                futu_autype = ft.AuType.QFQ
            elif autype == "hfq":
                futu_autype = ft.AuType.HFQ
            else:
                futu_autype = ft.AuType.NONE
            
            # 转换fields参数
            futu_fields = None
            if fields:
                futu_fields = []
                for field in fields:
                    if hasattr(ft.KL_FIELD, field):
                        futu_fields.append(getattr(ft.KL_FIELD, field))
                if not futu_fields:
                    futu_fields = [ft.KL_FIELD.ALL]
            else:
                futu_fields = [ft.KL_FIELD.ALL]
            
            # 转换session参数
            if session == "NORMAL":
                futu_session = ft.Session.NORMAL
            elif session == "PRE_MARKET":
                futu_session = ft.Session.PRE_MARKET
            elif session == "AFTER_HOURS":
                futu_session = ft.Session.AFTER_HOURS
            else:
                futu_session = ft.Session.NONE
            
            # 调用富途API
            ret, data, next_page_key = quote_ctx.request_history_kline(
                code=code,
                start=start,
                end=end,
                ktype=futu_ktype,
                autype=futu_autype,
                fields=futu_fields,
                max_count=max_count,
                page_req_key=page_req_key,
                extended_time=extended_time,
                session=futu_session
            )
            
            df = self._handle_response(ret, data, f"获取{code}的历史K线数据")
            
            # 转换为KLineData对象列表
            kline_list = []
            for _, row in df.iterrows():
                kline_data = KLineData.from_dict(row.to_dict())
                kline_list.append(kline_data)
            
            self.logger.info(f"获取到{code}的 {len(kline_list)} 条历史K线数据，下一页key: {next_page_key}")
            return kline_list, next_page_key
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取历史K线数据异常: {str(e)}")
    
    def get_rehab(self, code: str) -> List[AuTypeInfo]:
        """
        获取复权因子
        
        Args:
            code: 股票代码 (如 "HK.00700")
        
        Returns:
            List[AuTypeInfo]: 复权信息列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_rehab(code)
            
            df = self._handle_response(ret, data, f"获取{code}的复权因子")
            
            # 转换为AuTypeInfo对象列表
            autype_list = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                row_dict['code'] = code  # 确保包含股票代码
                autype_info = AuTypeInfo.from_dict(row_dict)
                autype_list.append(autype_info)
            
            self.logger.info(f"获取到 {code} 的 {len(autype_list)} 条复权信息")
            return autype_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取复权因子异常: {str(e)}")
    
    def get_trading_days(self, market: str = "HK", start: Optional[str] = None, end: Optional[str] = None) -> List[str]:
        """
        获取交易日历
        
        Args:
            market: 市场代码 (HK/US/CN等)
            start: 开始日期 (YYYY-MM-DD格式)，为None时使用30天前
            end: 结束日期 (YYYY-MM-DD格式)，为None时使用当前日期
        
        Returns:
            List[str]: 交易日期列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.request_trading_days(market, start, end)
            
            result = self._handle_response(ret, data, "获取交易日历")
            
            # request_trading_days返回的是字典列表，不是DataFrame
            if isinstance(result, list) and len(result) > 0:
                # 如果是字典列表，提取time字段
                if isinstance(result[0], dict):
                    trading_days = [item['time'] for item in result if 'time' in item]
                else:
                    trading_days = result
            else:
                # 如果是DataFrame，提取time列
                trading_days = result['time'].tolist() if hasattr(result, 'columns') and 'time' in result.columns else []
            
            self.logger.info(f"获取到 {len(trading_days)} 个交易日")
            return trading_days
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取交易日历异常: {str(e)}")

    def get_autype_list(self, codes: List[str]) -> List[AuTypeInfo]:
        """
        获取复权因子列表 (对多个股票代码调用get_rehab)
        
        Args:
            codes: 股票代码列表 (如 ["HK.00700", "HK.00388"])
        
        Returns:
            List[AuTypeInfo]: 复权信息列表
        """
        try:
            all_autype_list = []
            
            # 逐个股票代码调用get_rehab方法
            for code in codes:
                try:
                    autype_list = self.get_rehab(code)
                    all_autype_list.extend(autype_list)
                except Exception as e:
                    self.logger.warning(f"获取股票 {code} 复权因子失败: {e}")
                    continue
            
            if not all_autype_list:
                raise FutuQuoteException(-1, "所有股票的复权因子获取失败")
            
            self.logger.info(f"获取到 {len(all_autype_list)} 条复权信息")
            return all_autype_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取复权因子列表异常: {str(e)}")

    def get_plate_list(self, market: str = "HK", plate_type: str = "ALL") -> List[PlateInfo]:
        """
        获取板块集合下的子板块列表
        
        Args:
            market: 市场代码 (HK/US/CN等)
            plate_type: 板块类型 (ALL/INDUSTRY/REGION/CONCEPT等)
        
        Returns:
            List[PlateInfo]: 板块信息列表
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换板块类型为富途API格式
            if plate_type == "ALL":
                futu_plate_type = ft.Plate.ALL
            elif plate_type == "INDUSTRY":
                futu_plate_type = ft.Plate.INDUSTRY
            elif plate_type == "REGION":
                futu_plate_type = ft.Plate.REGION
            elif plate_type == "CONCEPT":
                futu_plate_type = ft.Plate.CONCEPT
            else:
                futu_plate_type = ft.Plate.ALL
            
            ret, data = quote_ctx.get_plate_list(market, futu_plate_type)
            
            df = self._handle_response(ret, data, "获取板块列表")
            
            # 转换为PlateInfo对象列表
            plate_list = []
            for _, row in df.iterrows():
                plate_info = PlateInfo.from_dict(row.to_dict())
                plate_list.append(plate_info)
            
            self.logger.info(f"获取到 {len(plate_list)} 个板块信息")
            return plate_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取板块列表异常: {str(e)}")

    def get_plate_stock(self, plate_code: str) -> List[PlateStock]:
        """
        获取板块下的股票列表
        
        Args:
            plate_code: 板块代码 (如 "HK.BK1107")
        
        Returns:
            List[PlateStock]: 板块股票信息列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_plate_stock(plate_code)
            
            df = self._handle_response(ret, data, f"获取板块{plate_code}的股票列表")
            
            # 转换为PlateStock对象列表
            stock_list = []
            for _, row in df.iterrows():
                plate_stock = PlateStock.from_dict(row.to_dict())
                stock_list.append(plate_stock)
            
            self.logger.info(f"获取到板块 {plate_code} 下的 {len(stock_list)} 只股票")
            return stock_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取板块股票列表异常: {str(e)}")
    
    # ================== 订阅推送接口 ==================
    
    def subscribe(self, codes: List[str], sub_types: List[str], is_first_push: bool = True, is_unlimit_push: bool = False) -> bool:
        """
        订阅数据推送
        
        Args:
            codes: 股票代码列表 (如 ["HK.00700", "HK.00388"])
            sub_types: 订阅类型列表 (如 ["quote", "kline_day", "ticker"])
            is_first_push: 是否立即推送当前数据
            is_unlimit_push: 是否不限制推送数量
        
        Returns:
            bool: 是否订阅成功
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换订阅类型
            futu_sub_types = []
            for sub_type in sub_types:
                if sub_type in self._sub_type_map:
                    futu_sub_types.append(self._sub_type_map[sub_type])
                else:
                    self.logger.warning(f"不支持的订阅类型: {sub_type}")
                    continue
            
            if not futu_sub_types:
                raise FutuQuoteException(-1, "没有有效的订阅类型")
            
            # 执行订阅
            ret, err_msg = quote_ctx.subscribe(codes, futu_sub_types, is_first_push, is_unlimit_push)
            
            if ret != ft.RET_OK:
                self.logger.error(f"订阅失败: {err_msg}")
                raise FutuQuoteException(ret, err_msg)
            
            # 记录订阅信息
            with self._lock:
                for code in codes:
                    for sub_type in sub_types:
                        if sub_type in self._sub_type_map:
                            if code not in self._subscriptions[sub_type]:
                                self._subscriptions[sub_type][code] = []
                            self._subscriptions[sub_type][code] = codes
            
            self.logger.info(f"订阅成功: {codes} -> {sub_types}")
            return True
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"订阅异常: {str(e)}")
    
    def unsubscribe(self, codes: List[str], sub_types: List[str]) -> bool:
        """
        取消订阅数据推送
        
        Args:
            codes: 股票代码列表
            sub_types: 订阅类型列表
        
        Returns:
            bool: 是否取消订阅成功
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换订阅类型
            futu_sub_types = []
            for sub_type in sub_types:
                if sub_type in self._sub_type_map:
                    futu_sub_types.append(self._sub_type_map[sub_type])
                else:
                    self.logger.warning(f"不支持的订阅类型: {sub_type}")
                    continue
            
            if not futu_sub_types:
                raise FutuQuoteException(-1, "没有有效的订阅类型")
            
            # 执行取消订阅
            ret, err_msg = quote_ctx.unsubscribe(codes, futu_sub_types)
            
            if ret != ft.RET_OK:
                self.logger.error(f"取消订阅失败: {err_msg}")
                raise FutuQuoteException(ret, err_msg)
            
            # 更新订阅记录
            with self._lock:
                for code in codes:
                    for sub_type in sub_types:
                        if sub_type in self._subscriptions and code in self._subscriptions[sub_type]:
                            del self._subscriptions[sub_type][code]
            
            self.logger.info(f"取消订阅成功: {codes} -> {sub_types}")
            return True
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"取消订阅异常: {str(e)}")
    
    def unsubscribe_all(self) -> bool:
        """
        取消所有订阅
        
        Returns:
            bool: 是否取消成功
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 获取所有当前订阅
            all_codes = set()
            all_sub_types = set()
            
            with self._lock:
                for sub_type, code_dict in self._subscriptions.items():
                    all_sub_types.add(sub_type)
                    for code in code_dict:
                        all_codes.add(code)
            
            if not all_codes:
                self.logger.info("没有需要取消的订阅")
                return True
            
            # 转换为富途API格式
            futu_sub_types = [self._sub_type_map[st] for st in all_sub_types if st in self._sub_type_map]
            
            # 执行取消订阅
            ret, err_msg = quote_ctx.unsubscribe(list(all_codes), futu_sub_types)
            
            if ret != ft.RET_OK:
                self.logger.error(f"取消所有订阅失败: {err_msg}")
                raise FutuQuoteException(ret, err_msg)
            
            # 清空订阅记录
            with self._lock:
                self._subscriptions.clear()
            
            self.logger.info("取消所有订阅成功")
            return True
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"取消所有订阅异常: {str(e)}")
    
    def set_handler(self, handler_type: str, handler: Callable) -> bool:
        """
        设置推送数据处理器（回调函数）
        
        注意：此方法主要用于管理回调函数引用。
        富途API的实际推送处理需要继承特定的Handler基类。
        
        Args:
            handler_type: 处理器类型 (quote/kline/ticker/order_book/rt_data/broker)
            handler: 回调函数，接收推送数据
        
        Returns:
            bool: 是否设置成功
        """
        try:
            # 验证处理器类型
            valid_types = ["quote", "kline", "ticker", "order_book", "rt_data", "broker"]
            if not any(handler_type.startswith(t) for t in valid_types):
                raise FutuQuoteException(-1, f"不支持的处理器类型: {handler_type}")
            
            # 保存处理器引用
            self._handlers[handler_type] = handler
            
            self.logger.info(f"设置 {handler_type} 处理器成功")
            return True
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"设置处理器异常: {str(e)}")
    
    def get_handler(self, handler_type: str) -> Optional[Callable]:
        """
        获取指定类型的处理器
        
        Args:
            handler_type: 处理器类型
        
        Returns:
            Optional[Callable]: 处理器函数，如果不存在则返回None
        """
        return self._handlers.get(handler_type)
    
    # ================== 便捷订阅方法 ==================
    
    def subscribe_quote(self, codes: List[str], callback: Optional[Callable] = None) -> bool:
        """
        订阅基础报价推送
        
        Args:
            codes: 股票代码列表
            callback: 推送回调函数
        
        Returns:
            bool: 是否订阅成功
        """
        if callback:
            self.set_handler("quote", callback)
        return self.subscribe(codes, ["quote"])
    
    def subscribe_kline(self, codes: List[str], ktype: str = "day", callback: Optional[Callable] = None) -> bool:
        """
        订阅K线数据推送
        
        Args:
            codes: 股票代码列表
            ktype: K线类型 (1m/5m/15m/30m/60m/day/week/month)
            callback: 推送回调函数
        
        Returns:
            bool: 是否订阅成功
        """
        # 转换K线类型
        ktype_map = {
            "1m": "kline_1m", "5m": "kline_5m", "15m": "kline_15m", 
            "30m": "kline_30m", "60m": "kline_60m", "day": "kline_day",
            "week": "kline_week", "month": "kline_month"
        }
        
        sub_type = ktype_map.get(ktype, "kline_day")
        
        if callback:
            self.set_handler("kline", callback)
        return self.subscribe(codes, [sub_type])
    
    def subscribe_ticker(self, codes: List[str], callback: Optional[Callable] = None) -> bool:
        """
        订阅逐笔数据推送
        
        Args:
            codes: 股票代码列表
            callback: 推送回调函数
        
        Returns:
            bool: 是否订阅成功
        """
        if callback:
            self.set_handler("ticker", callback)
        return self.subscribe(codes, ["ticker"])
    
    def subscribe_order_book(self, codes: List[str], callback: Optional[Callable] = None) -> bool:
        """
        订阅买卖盘数据推送
        
        Args:
            codes: 股票代码列表
            callback: 推送回调函数
        
        Returns:
            bool: 是否订阅成功
        """
        if callback:
            self.set_handler("order_book", callback)
        return self.subscribe(codes, ["order_book"])
    
    def subscribe_rt_data(self, codes: List[str], callback: Optional[Callable] = None) -> bool:
        """
        订阅分时数据推送
        
        Args:
            codes: 股票代码列表
            callback: 推送回调函数
        
        Returns:
            bool: 是否订阅成功
        """
        if callback:
            self.set_handler("rt_data", callback)
        return self.subscribe(codes, ["rt_data"])
    
    def get_subscriptions(self) -> Dict[str, Dict[str, List[str]]]:
        """
        获取当前所有订阅信息
        
        Returns:
            Dict[str, Dict[str, List[str]]]: 订阅信息字典
        """
        with self._lock:
            return dict(self._subscriptions)
    
    def is_subscribed(self, code: str, sub_type: str) -> bool:
        """
        检查是否已订阅某股票的某种数据类型
        
        Args:
            code: 股票代码
            sub_type: 订阅类型
        
        Returns:
            bool: 是否已订阅
        """
        with self._lock:
            return code in self._subscriptions.get(sub_type, {})
    
    # ================== 实时数据获取接口 ==================
    
    def get_rt_ticker(self, code: str, num: int = 100):
        """
        获取实时逐笔数据
        
        Args:
            code: 股票代码 (如 "HK.00700")
            num: 获取数量 (最大1000)
        
        Returns:
            DataFrame: 实时逐笔数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_rt_ticker(code, num)
            
            df = self._handle_response(ret, data, f"获取{code}的实时逐笔数据")
            
            self.logger.info(f"获取到 {code} 的 {len(df) if hasattr(df, '__len__') else 0} 条实时逐笔数据")
            return df
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取实时逐笔数据异常: {str(e)}")
    
    def get_ticker_data(self, code: str, num: int = 100) -> List[TickerData]:
        """
        获取逐笔数据
        
        Args:
            code: 股票代码 (如 "HK.00700")
            num: 获取数量 (最大1000)
        
        Returns:
            List[TickerData]: 逐笔数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_rt_ticker(code, num)
            
            df = self._handle_response(ret, data, f"获取{code}的逐笔数据")
            
            # 转换为TickerData对象列表
            ticker_list = []
            for _, row in df.iterrows():
                ticker = TickerData.from_dict(row.to_dict())
                ticker_list.append(ticker)
            
            self.logger.info(f"获取到 {code} 的 {len(ticker_list)} 条逐笔数据")
            return ticker_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取逐笔数据异常: {str(e)}")
    
    def get_order_book(self, code: str, num = 10) -> OrderBookData:
        """
        获取买卖盘数据
        
        Args:
            code: 股票代码 (如 "HK.00700")
        
        Returns:
            OrderBookData: 买卖盘数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_order_book(code, num = num)
            
            df = self._handle_response(ret, data, f"获取{code}的买卖盘数据")
            
            # 处理富途API返回的特殊格式
            # API返回格式: {'code': 'HK.06181', 'Bid': [(price, vol, order_count, {}), ...], 'Ask': [...]}
            converted_data = {}
            
            import pandas as pd
            if isinstance(df, pd.DataFrame):
                if len(df) > 0:
                    row_dict = df.iloc[0].to_dict()
                    converted_data = self._convert_orderbook_format(row_dict)
                else:
                    raise FutuQuoteException(-1, f"没有获取到{code}的买卖盘数据")
            elif isinstance(df, dict):
                converted_data = self._convert_orderbook_format(df)
            else:
                raise FutuQuoteException(-1, f"获取到意外的数据格式: {type(df)}")
            
            order_book = OrderBookData.from_dict(converted_data)
            self.logger.info(f"获取到 {code} 的买卖盘数据")
            return order_book
                
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取买卖盘数据异常: {str(e)}")
    
    def _convert_orderbook_format(self, data: dict, num = 10) -> dict:
        """
        转换富途API返回的买卖盘数据格式
        
        Args:
            data: 原始数据，格式为 {'Bid': [(price, vol, count, {}), ...], 'Ask': [...]}
        
        Returns:
            dict: 转换后的数据格式，适配OrderBookData.from_dict
        """
        converted = {
            'code': data.get('code', ''),
            'svr_recv_time_bid': data.get('svr_recv_time_bid', ''),
            'svr_recv_time_ask': data.get('svr_recv_time_ask', '')
        }
        
        # 处理买盘数据 (Bid)
        bid_data = data.get('Bid', [])
        for i in range(num):  
            if i < len(bid_data):
                price, volume, count, extra = bid_data[i]
                converted[f'Bid{i+1}'] = price
                converted[f'BidVol{i+1}'] = volume
            else:
                converted[f'Bid{i+1}'] = 0.0
                converted[f'BidVol{i+1}'] = 0
        
        # 处理卖盘数据 (Ask)
        ask_data = data.get('Ask', [])
        for i in range(num):  
            if i < len(ask_data):
                price, volume, count, extra = ask_data[i]
                converted[f'Ask{i+1}'] = price
                converted[f'AskVol{i+1}'] = volume
            else:
                converted[f'Ask{i+1}'] = 0.0
                converted[f'AskVol{i+1}'] = 0
        
        return converted
    
    def get_rt_data(self, code: str) -> List[RTData]:
        """
        获取分时数据
        
        Args:
            code: 股票代码 (如 "HK.00700")
        
        Returns:
            List[RTData]: 分时数据列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_rt_data(code)
            
            df = self._handle_response(ret, data, f"获取{code}的分时数据")
            
            # 转换为RTData对象列表
            rt_list = []
            for _, row in df.iterrows():
                rt_data = RTData.from_dict(row.to_dict())
                rt_list.append(rt_data)
            
            self.logger.info(f"获取到 {code} 的 {len(rt_list)} 条分时数据")
            return rt_list
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取分时数据异常: {str(e)}")
    
    def get_broker_queue_data(self, code: str) -> BrokerQueueData:
        """
        获取经纪队列数据（返回BrokerQueueData对象）
        
        Args:
            code: 股票代码 (如 "HK.00700")
        
        Returns:
            BrokerQueueData: 经纪队列数据对象
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, bid_frame_table, ask_frame_table = quote_ctx.get_broker_queue(code)
            
            # 检查返回状态
            if ret != 0:
                raise FutuQuoteException(ret, f"获取{code}的经纪队列失败")
            
            self.logger.info(f"获取到 {code} 的经纪队列数据")
            
            # 创建BrokerQueueData对象
            broker_data = BrokerQueueData.from_dict({
                'code': code,
                'bid_frame_table': bid_frame_table.to_dict() if hasattr(bid_frame_table, 'to_dict') else bid_frame_table,
                'ask_frame_table': ask_frame_table.to_dict() if hasattr(ask_frame_table, 'to_dict') else ask_frame_table
            })
            
            return broker_data
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取经纪队列数据异常: {str(e)}")
    
    def get_broker_queue(self, code: str) -> Dict[str, Any]:
        """
        获取经纪队列
        
        Args:
            code: 股票代码
        
        Returns:
            Dict: 经纪队列数据，包含bid_frame_table和ask_frame_table
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, bid_frame_table, ask_frame_table = quote_ctx.get_broker_queue(code)
            
            # 检查返回状态
            if ret != 0:
                raise FutuQuoteException(ret, f"获取{code}的经纪队列失败")
            
            self.logger.info(f"获取到 {code} 的经纪队列数据")
            
            # 返回包含买盘和卖盘队列的字典
            result = {
                'bid_frame_table': bid_frame_table.to_dict() if hasattr(bid_frame_table, 'to_dict') else bid_frame_table,
                'ask_frame_table': ask_frame_table.to_dict() if hasattr(ask_frame_table, 'to_dict') else ask_frame_table
            }
            
            return result
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取经纪队列异常: {str(e)}")

    def get_stock_filter(self, market: str = "HK", filter_list: List = None, begin: int = 0) -> List:
        """
        股票筛选
        
        Args:
            market: 市场代码
            filter_list: 筛选条件列表
            begin: 开始索引
        
        Returns:
            List: 筛选结果
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换市场代码
            market_map = {
                "HK": ft.Market.HK,
                "US": ft.Market.US,
                "CN": ft.Market.CN_SH,
                "SH": ft.Market.CN_SH,
                "SZ": ft.Market.CN_SZ
            }
            
            futu_market = market_map.get(market.upper(), ft.Market.HK)
            ret, data = quote_ctx.get_stock_filter(market=futu_market, filter_list=filter_list or [], begin=begin)
            
            result = self._handle_response(ret, data, f"股票筛选 {market}")
            
            self.logger.info(f"完成 {market} 市场股票筛选")
            return result
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"股票筛选异常: {str(e)}")

    def query_subscription_quota(self) -> Dict:
        """
        查询订阅配额
        
        Returns:
            Dict: 订阅配额信息
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.query_subscription()
            
            result = self._handle_response(ret, data, "查询订阅配额")
            
            self.logger.info("查询订阅配额成功")
            return result.to_dict() if hasattr(result, 'to_dict') else result
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"查询订阅配额异常: {str(e)}")

    def get_history_kl_quota(self, get_detail: bool = True) -> Dict:
        """
        获取历史K线配额
        
        Args:
            get_detail: 是否获取详细信息
        
        Returns:
            Dict: 历史K线配额信息
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_history_kl_quota(get_detail=get_detail)
            
            result = self._handle_response(ret, data, "获取历史K线配额")
            
            self.logger.info("获取历史K线配额成功")
            return result.to_dict() if hasattr(result, 'to_dict') else result
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取历史K线配额异常: {str(e)}")

    def get_reference_stock_list(self, code: str, reference_type) -> List:
        """
        获取关联股票列表
        
        Args:
            code: 股票代码
            reference_type: 关联类型
        
        Returns:
            List: 关联股票列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_referencestock_list(code, reference_type)
            
            df = self._handle_response(ret, data, f"获取{code}的关联股票")
            
            self.logger.info(f"获取到 {code} 的关联股票信息")
            return df
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取关联股票异常: {str(e)}")

    # ================== 衍生品接口 ==================
    
    def get_option_expiration_date(self, owner_stock_code: str, market: str = "HK", currency: str = "HKD") -> Dict:
        """
        获取期权到期日
        
        Args:
            owner_stock_code: 正股代码
            market: 市场
            currency: 货币类型
        
        Returns:
            Dict: 期权到期日数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_option_expiration_date(owner_stock_code)
            
            return self._handle_response(ret, data, f"获取 {owner_stock_code} 期权到期日")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取期权到期日异常: {str(e)}")
    
    def get_option_chain(self, owner_stock_code: str, option_type: str = "ALL", 
                        strike_price_begin: Optional[float] = None, strike_price_end: Optional[float] = None,
                        expiry_date_begin: Optional[str] = None, expiry_date_end: Optional[str] = None,
                        data_filter: Optional[str] = None) -> Dict:
        """
        获取期权链
        
        Args:
            owner_stock_code: 正股代码 
            option_type: 期权类型 (ALL/CALL/PUT)
            strike_price_begin: 行权价范围开始
            strike_price_end: 行权价范围结束
            expiry_date_begin: 到期日范围开始
            expiry_date_end: 到期日范围结束
            data_filter: 数据过滤器
        
        Returns:
            Dict: 期权链数据
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换期权类型
            option_type_map = {
                "ALL": ft.OptionType.ALL,
                "CALL": ft.OptionType.CALL,
                "PUT": ft.OptionType.PUT
            }
            futu_option_type = option_type_map.get(option_type.upper(), ft.OptionType.ALL)
            
            ret, data = quote_ctx.get_option_chain(
                owner_stock_code,
                option_type=futu_option_type,
                strike_price_begin=strike_price_begin,
                strike_price_end=strike_price_end,
                expiry_date_begin=expiry_date_begin,
                expiry_date_end=expiry_date_end,
                data_filter=data_filter
            )
            
            return self._handle_response(ret, data, f"获取 {owner_stock_code} 期权链")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取期权链异常: {str(e)}")
    
    def get_warrant(self, begin: int = 0, num: int = 200, sort_field: str = "NAME", 
                   ascend: bool = True, filter_list: Optional[List] = None) -> Dict:
        """
        获取窝轮列表
        
        Args:
            begin: 数据起始点
            num: 返回数据数量限制
            sort_field: 排序字段
            ascend: 升序/降序
            filter_list: 过滤条件列表
        
        Returns:
            Dict: 窝轮数据
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换排序字段
            sort_field_map = {
                "NAME": ft.SortField.NAME,
                "CODE": ft.SortField.CODE,
                "CUR_PRICE": ft.SortField.CUR_PRICE,
                "PRICE_CHANGE_VAL": ft.SortField.PRICE_CHANGE_VAL,
                "CHANGE_RATE": ft.SortField.CHANGE_RATE,
                "STATUS": ft.SortField.STATUS,
                "LAST_SETTLE_PRICE": ft.SortField.LAST_SETTLE_PRICE,
                "POSITION": ft.SortField.POSITION,
                "POSITION_CHANGE": ft.SortField.POSITION_CHANGE,
                "VOLUME": ft.SortField.VOLUME
            }
            futu_sort_field = sort_field_map.get(sort_field.upper(), ft.SortField.NAME)
            
            # 转换排序方向
            futu_sort_dir = ft.SortDir.ASCEND if ascend else ft.SortDir.DESCEND
            
            ret, data = quote_ctx.get_warrant(
                begin=begin,
                num=num,
                sort_field=futu_sort_field,
                sort_dir=futu_sort_dir,
                filter_list=filter_list or []
            )
            
            return self._handle_response(ret, data, "获取窝轮列表")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取窝轮列表异常: {str(e)}")
    
    def get_future_info(self, code_list: List[str]) -> Dict:
        """
        获取期货合约信息
        
        Args:
            code_list: 期货代码列表
        
        Returns:
            Dict: 期货合约信息
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_future_info(code_list)
            
            return self._handle_response(ret, data, f"获取期货合约信息")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取期货合约信息异常: {str(e)}")
    
    # ================== 全市场筛选接口 ==================
    
    def get_ipo_list(self, market: str = "HK") -> Dict:
        """
        获取IPO列表
        
        Args:
            market: 市场代码 (HK/US/CN)
        
        Returns:
            Dict: IPO列表数据
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换市场代码
            market_map = {
                "HK": ft.Market.HK,
                "US": ft.Market.US,
                "CN": ft.Market.SH  # 使用上海市场代表中国
            }
            futu_market = market_map.get(market.upper(), ft.Market.HK)
            
            ret, data = quote_ctx.get_ipo_list(futu_market)
            
            return self._handle_response(ret, data, f"获取 {market} IPO列表")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取IPO列表异常: {str(e)}")
    
    def get_plate_stock(self, plate_code: str, sort_field: str = "CODE", ascend: bool = True) -> Dict:
        """
        获取板块股票列表
        
        Args:
            plate_code: 板块代码
            sort_field: 排序字段
            ascend: 升序/降序
        
        Returns:
            Dict: 板块股票数据
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换排序字段
            sort_field_map = {
                "CODE": ft.SortField.CODE,
                "NAME": ft.SortField.NAME,  
                "CUR_PRICE": ft.SortField.CUR_PRICE,
                "CHANGE_RATE": ft.SortField.CHANGE_RATE,
                "VOLUME": ft.SortField.VOLUME
            }
            futu_sort_field = sort_field_map.get(sort_field.upper(), ft.SortField.CODE)
            
            # 转换排序方向
            futu_sort_dir = ft.SortDir.ASCEND if ascend else ft.SortDir.DESCEND
            
            ret, data = quote_ctx.get_plate_stock(
                plate_code, 
                sort_field=futu_sort_field,
                sort_dir=futu_sort_dir
            )
            
            return self._handle_response(ret, data, f"获取板块 {plate_code} 股票列表")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取板块股票列表异常: {str(e)}")
    
    def get_global_state(self) -> Dict:
        """
        获取全局状态
        
        Returns:
            Dict: 全局状态数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_global_state()
            
            return self._handle_response(ret, data, "获取全局状态")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取全局状态异常: {str(e)}")
    
    # ================== 个性化功能接口 ==================
    
    def set_price_reminder(self, code: str, price: float, reminder_type: str = "PRICE_UP", 
                          frequency: str = "ONCE", note: str = "") -> Dict:
        """
        设置到价提醒
        
        Args:
            code: 股票代码
            price: 提醒价格
            reminder_type: 提醒类型 (PRICE_UP/PRICE_DOWN)
            frequency: 提醒频率 (ONCE/DAILY)
            note: 备注
        
        Returns:
            Dict: 设置结果
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换提醒类型和频率（这里需要根据实际API进行调整）
            ret, data = quote_ctx.set_price_reminder(
                code=code,
                price=price,
                type=reminder_type,
                frequency=frequency,
                note=note
            )
            
            return self._handle_response(ret, data, f"设置 {code} 到价提醒")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"设置到价提醒异常: {str(e)}")
    
    def get_price_reminder(self, code: Optional[str] = None) -> Dict:
        """
        获取到价提醒列表
        
        Args:
            code: 股票代码，为None则获取所有
        
        Returns:
            Dict: 到价提醒列表
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_price_reminder(code)
            
            return self._handle_response(ret, data, "获取到价提醒列表")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取到价提醒异常: {str(e)}")
    
    def get_user_security_group(self, group_type: str = "CUSTOM") -> Dict:
        """
        获取自选股分组
        
        Returns:
            Dict: 自选股分组数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_user_security_group(group_type = group_type )
            
            return self._handle_response(ret, data, "获取自选股分组")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取自选股分组异常: {str(e)}")
    
    def get_user_security(self, group_name: str = "特别关注") -> Dict:
        """
        获取自选股
        
        Args:
            group_name: 分组名称，为空则获取所有
        
        Returns:
            Dict: 自选股数据
        """
        try:
            quote_ctx = self._get_quote_context()
            ret, data = quote_ctx.get_user_security(group_name)
            
            return self._handle_response(ret, data, f"获取自选股")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"获取自选股异常: {str(e)}")
    
    def modify_user_security(self, group_name: str, operation: str, code_list: List[str]) -> Dict:
        """
        修改自选股
        
        Args:
            group_name: 分组名称
            operation: 操作类型 (ADD/DEL)
            code_list: 股票代码列表
        
        Returns:
            Dict: 修改结果
        """
        try:
            quote_ctx = self._get_quote_context()
            
            # 转换操作类型
            operation_map = {
                "ADD": ft.ModifyUserSecurityOp.ADD,
                "DEL": ft.ModifyUserSecurityOp.DEL
            }
            futu_operation = operation_map.get(operation.upper())
            if not futu_operation:
                raise ValueError(f"无效的操作类型: {operation}")
            
            ret, data = quote_ctx.modify_user_security(
                group_name, 
                futu_operation, 
                code_list
            )
            
            return self._handle_response(ret, data, f"修改自选股")
            
        except Exception as e:
            if isinstance(e, FutuException):
                raise
            raise FutuQuoteException(-1, f"修改自选股异常: {str(e)}")

    # ================== 推送回调处理器 ==================
    
    def register_stock_quote_handler(self, handler) -> bool:
        """注册股票报价推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("股票报价推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册股票报价推送回调失败: {e}")
            return False
    
    def register_order_book_handler(self, handler) -> bool:
        """注册买卖盘推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("买卖盘推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册买卖盘推送回调失败: {e}")
            return False
    
    def register_kline_handler(self, handler) -> bool:
        """注册K线推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("K线推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册K线推送回调失败: {e}")
            return False
    
    def register_ticker_handler(self, handler) -> bool:
        """注册逐笔推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("逐笔推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册逐笔推送回调失败: {e}")
            return False
    
    def register_rt_data_handler(self, handler) -> bool:
        """注册分时推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("分时推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册分时推送回调失败: {e}")
            return False
    
    def register_broker_handler(self, handler) -> bool:
        """注册经纪队列推送回调"""
        try:
            quote_ctx = self._get_quote_context()
            quote_ctx.set_handler(handler)
            self.logger.info("经纪队列推送回调注册成功")
            return True
        except Exception as e:
            self.logger.error(f"注册经纪队列推送回调失败: {e}")
            return False