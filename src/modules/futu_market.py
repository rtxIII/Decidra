#对应https://openapi.futunn.com/futu-api-doc/quote/overview.html
import itertools
import json
import pathlib
import platform
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from base.futu_class import MarketState, GlobalMarketState, OrderBookData, KLineData

import pandas as pd

from utils import logger
from utils.global_vars import *

# 使用新的API封装，移除旧的futu库直接调用
from api.futu import create_client
from base.futu_class import FutuException


from base.futu_modue import FutuModuleBase

"""
from modules.futu_market import FutuMarket
f = FutuMarket()
f.get_market_state(['HK.00700'])
f.get_market_snapshot(['HK.00700'])
"""


class FutuMarket(FutuModuleBase):
    """
    富途行情业务逻辑层
    
    继承FutuBase，提供完整的富途行情接口
    对应: https://openapi.futunn.com/futu-api-doc/quote/overview.html
    使用时需先调用open方法, 务必close
    """
    
    def __init__(self):
        """初始化富途行情管理器"""
        super().__init__()
        self.logger = get_logger("futu_market")
        
        # 业务数据缓存
        self.stock_list = None  
        self.plate_list = None
        self.owner_plate = None
        
        # 订阅管理
        self.subscribed_stocks: Dict[str, Set[str]] = {}  # {股票代码: {订阅类型集合}}
        self.subscription_limits = {
            'quote': 200,           # 报价订阅限制
            'order_book': 200,      # 五档订阅限制  
            'ticker': 200,          # 逐笔订阅限制
            'kline_1m': 200,        # 1分钟K线订阅限制
            'kline_5m': 200,        # 5分钟K线订阅限制
            'kline_15m': 200,       # 15分钟K线订阅限制
            'kline_30m': 200,       # 30分钟K线订阅限制
            'kline_60m': 200,       # 60分钟K线订阅限制
            'kline_day': 200,       # 日K订阅限制
            'kline_week': 200,      # 周K订阅限制
            'kline_month': 200,     # 月K订阅限制
            'broker': 200           # 经纪队列订阅限制
        }
        
        self.logger.info("FutuMarket initialized successfully")
    
        self.check()

    # ================== 市场状态接口 ==================
    
    def get_market_state(self, codes: List[str]) -> List:
        """获取市场状态"""
        try:
            return self.client.quote.get_market_state(codes)
        except Exception as e:
            self.logger.error(f"Get market state error: {e}")
            return []

    def get_global_state(self) -> Optional[GlobalMarketState]:
        """获取全局状态
        
        Returns:
            Optional[GlobalMarketState]: 全局市场状态对象，失败时返回None
        """
        try:
            result = self.client.quote.get_global_state()
            
            if result and isinstance(result, dict):
                # 使用GlobalMarketState.from_dict处理返回数据
                global_state = GlobalMarketState.from_dict(result)
                self.logger.debug(f"Global state retrieved successfully: qot_logined={global_state.qot_logined}")
                return global_state
            else:
                self.logger.warning(f"Invalid global state format: {type(result)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Get global state error: {e}")
            return None

    # ================== 实时行情接口 ==================
    
    def get_market_snapshot(self, codes: List[str]) -> List:
        """获取市场快照"""
        try:
            return self.client.quote.get_market_snapshot(codes)
        except Exception as e:
            self.logger.error(f"Get market snapshot error: {e}")
            return []

    def get_stock_quote(self, codes: List[str]) -> List:
        """获取股票报价"""
        try:
            # 智能订阅检测 - 确保已订阅quote数据
            if not self._ensure_auto_subscription(codes, 'quote'):
                self.logger.warning(f"无法确保 {codes} 的 quote 数据订阅，可能影响数据获取")
            
            return self.client.quote.get_stock_quote(codes)
        except Exception as e:
            self.logger.error(f"Get stock quote error: {e}")
            return []

    def get_order_book(self, code:str) -> OrderBookData:
        """获取买卖盘"""
        try:
            # 智能订阅检测 - 确保已订阅order_book数据
            if not self._ensure_auto_subscription(code, 'order_book'):
                self.logger.warning(f"无法确保 {code} 的 order_book 数据订阅，可能影响数据获取")
            
            return self.client.quote.get_order_book(code)
        except Exception as e:
            self.logger.error(f"Get order book error: {e}")
            return []

    def get_rt_data(self,  code:str) -> List:
        """获取分时数据"""
        try:
            return self.client.quote.get_rt_data(code)
        except Exception as e:
            self.logger.error(f"Get rt data error: {e}")
            return []

    def get_rt_ticker(self, code:str) -> pd.DataFrame:
        """获取逐笔数据"""
        try:
            # 智能订阅检测 - 确保已订阅ticker数据
            if not self._ensure_auto_subscription(code, 'ticker'):
                self.logger.warning(f"无法确保 {code} 的 ticker 数据订阅，可能影响数据获取")
            
            return self.client.quote.get_rt_ticker(code)
        except Exception as e:
            self.logger.error(f"Get rt ticker error: {e}")
            return pd.DataFrame()

    def get_broker_queue(self, code: str) -> Dict:
        """获取经纪队列"""
        try:
            # 智能订阅检测 - 确保已订阅broker数据
            if not self._ensure_auto_subscription(code, 'broker'):
                self.logger.warning(f"无法确保 {code} 的 broker 数据订阅，可能影响数据获取")
            
            return self.client.quote.get_broker_queue(code)
        except Exception as e:
            self.logger.error(f"Get broker queue error: {e}")
            return []

    # ================== 订阅管理接口 ==================
    
    def subscribe(self, codes: List[str], sub_types: List[str], is_first_push: bool = True, is_unlimit_push: bool = False) -> bool:
        """订阅数据推送"""
        try:
            success = self.client.quote.subscribe(codes, sub_types, is_first_push, is_unlimit_push)
            if success:
                # 更新本地订阅状态
                for code in codes:
                    if code not in self.subscribed_stocks:
                        self.subscribed_stocks[code] = set()
                    self.subscribed_stocks[code].update(sub_types)
                
                self.logger.info(f"Successfully subscribed to {sub_types} for {len(codes)} stocks")
            else:
                self.logger.error(f"Failed to subscribe to {sub_types}")
            return success
        except Exception as e:
            self.logger.error(f"Subscription error: {e}")
            return False

    def unsubscribe(self, codes: List[str], sub_types: List[str]) -> bool:
        """取消订阅"""
        try:
            success = self.client.quote.unsubscribe(codes, sub_types)
            if success:
                # 更新本地订阅状态
                for code in codes:
                    if code in self.subscribed_stocks:
                        for sub_type in sub_types:
                            self.subscribed_stocks[code].discard(sub_type)
                        # 如果该股票没有任何订阅，移除记录
                        if not self.subscribed_stocks[code]:
                            del self.subscribed_stocks[code]
                
                self.logger.info(f"Successfully unsubscribed from {sub_types} for {len(codes)} stocks")
            return success
        except Exception as e:
            self.logger.error(f"Unsubscription error: {e}")
            return False

    def unsubscribe_all(self) -> bool:
        """取消所有订阅"""
        try:
            success = self.client.quote.unsubscribe_all()
            if success:
                # 清空本地订阅状态
                self.subscribed_stocks.clear()
                self.logger.info("Successfully unsubscribed from all")
            return success
        except Exception as e:
            self.logger.error(f"Unsubscribe all error: {e}")
            return False

    def get_subscriptions(self) -> List:
        """获取当前订阅信息"""
        try:
            return self.client.quote.get_subscriptions()
        except Exception as e:
            self.logger.error(f"Get subscriptions error: {e}")
            return []

    # ================== 订阅管理器功能 ==================
    
    def ensure_subscription(self, codes: List[str], sub_types: List[str]) -> bool:
        """
        确保股票已订阅指定类型的数据
        
        Args:
            codes: 股票代码列表
            sub_types: 订阅类型列表，如 ['quote', 'order_book', 'ticker']
            
        Returns:
            bool: 是否成功确保订阅
        """
        try:
            if isinstance(sub_types, str):
                sub_types = [sub_types]
                
            need_subscribe_codes = []
            need_subscribe_types = []
            
            for code in codes:
                for sub_type in sub_types:
                    if not self.is_subscribed(code, sub_type):
                        if code not in need_subscribe_codes:
                            need_subscribe_codes.append(code)
                        if sub_type not in need_subscribe_types:
                            need_subscribe_types.append(sub_type)
            
            if need_subscribe_codes and need_subscribe_types:
                # 检查订阅限制
                if not self._check_subscription_limits(need_subscribe_codes, need_subscribe_types):
                    self.logger.warning(f"订阅数量超出限制，无法订阅 {len(need_subscribe_codes)} 只股票的 {need_subscribe_types} 数据")
                    return False
                
                # 执行订阅
                success = self.subscribe(need_subscribe_codes, need_subscribe_types)
                if success:
                    self.logger.info(f"成功确保 {len(need_subscribe_codes)} 只股票的 {need_subscribe_types} 数据订阅")
                    return True
                else:
                    self.logger.error(f"确保订阅失败")
                    return False
            
            # 所有数据都已订阅
            self.logger.debug(f"所有指定股票和数据类型都已订阅")
            return True
            
        except Exception as e:
            self.logger.error(f"确保订阅异常: {e}")
            return False
    
    def is_subscribed(self, code: str, sub_type: str) -> bool:
        """
        检查股票是否已订阅指定类型
        
        Args:
            code: 股票代码
            sub_type: 订阅类型
            
        Returns:
            bool: 是否已订阅
        """
        return (code in self.subscribed_stocks and 
                sub_type in self.subscribed_stocks[code])
    
    def get_subscribed_types(self, code: str) -> Set[str]:
        """
        获取股票已订阅的类型
        
        Args:
            code: 股票代码
            
        Returns:
            Set[str]: 已订阅类型集合
        """
        return self.subscribed_stocks.get(code, set()).copy()
    
    def get_all_subscribed_stocks(self) -> Dict[str, Set[str]]:
        """
        获取所有已订阅股票和其订阅类型
        
        Returns:
            Dict[str, Set[str]]: 股票代码到订阅类型集合的映射
        """
        # 进行深拷贝，确保返回独立的副本
        return {code: types.copy() for code, types in self.subscribed_stocks.items()}
    
    def get_subscription_count(self, sub_type: str = None) -> int:
        """
        获取订阅数量
        
        Args:
            sub_type: 可选，指定订阅类型；如果不指定则返回所有股票订阅数
            
        Returns:
            int: 订阅数量
        """
        if sub_type:
            count = 0
            for code, types in self.subscribed_stocks.items():
                if sub_type in types:
                    count += 1
            return count
        else:
            return len(self.subscribed_stocks)
    
    def clean_subscription(self, codes: List[str], sub_types: List[str] = None) -> bool:
        """
        清理指定股票的订阅
        
        Args:
            codes: 要清理的股票代码列表
            sub_types: 要清理的订阅类型；如果为None则清理所有类型
            
        Returns:
            bool: 是否清理成功
        """
        try:
            if sub_types is None:
                # 清理所有类型的订阅
                existing_codes = []
                all_sub_types = set()
                
                for code in codes:
                    if code in self.subscribed_stocks:
                        existing_codes.append(code)
                        all_sub_types.update(self.subscribed_stocks[code])
                
                if existing_codes and all_sub_types:
                    return self.unsubscribe(existing_codes, list(all_sub_types))
            else:
                # 清理指定类型的订阅
                existing_codes = []
                for code in codes:
                    if code in self.subscribed_stocks:
                        for sub_type in sub_types:
                            if sub_type in self.subscribed_stocks[code]:
                                existing_codes.append(code)
                                break
                
                if existing_codes:
                    return self.unsubscribe(existing_codes, sub_types)
            
            return True
            
        except Exception as e:
            self.logger.error(f"清理订阅异常: {e}")
            return False
    
    def sync_subscription_status(self) -> bool:
        """
        同步订阅状态
        从API获取实际订阅状态，更新本地记录
        
        Returns:
            bool: 是否同步成功
        """
        try:
            # 获取API实际订阅状态
            actual_subscriptions = self.get_subscriptions()
            
            if actual_subscriptions:
                # 清空本地记录
                self.subscribed_stocks.clear()
                
                # 根据API返回结果更新本地记录
                # actual_subscriptions 格式: {sub_type: {code: [code, ...]}}
                for sub_type, codes_dict in actual_subscriptions.items():
                    for code in codes_dict.keys():
                        if code not in self.subscribed_stocks:
                            self.subscribed_stocks[code] = set()
                        self.subscribed_stocks[code].add(sub_type)
                
                self.logger.info(f"订阅状态同步成功，共同步 {len(self.subscribed_stocks)} 只股票的订阅状态")
                return True
            else:
                self.logger.info("无订阅数据，清空本地状态")
                self.subscribed_stocks.clear()
                return True
                
        except Exception as e:
            self.logger.error(f"同步订阅状态异常: {e}")
            return False
    
    def _check_subscription_limits(self, codes: List[str], sub_types: List[str]) -> bool:
        """
        检查订阅限制
        
        Args:
            codes: 要订阅的股票代码列表
            sub_types: 要订阅的类型列表
            
        Returns:
            bool: 是否在限制范围内
        """
        for sub_type in sub_types:
            if sub_type in self.subscription_limits:
                current_count = self.get_subscription_count(sub_type)
                new_count = len(codes)
                
                if current_count + new_count > self.subscription_limits[sub_type]:
                    self.logger.warning(
                        f"订阅类型 {sub_type} 超出限制：当前 {current_count}，"
                        f"新增 {new_count}，限制 {self.subscription_limits[sub_type]}"
                    )
                    return False
        return True
    
    def get_subscription_summary(self) -> Dict[str, Any]:
        """
        获取订阅摘要信息
        
        Returns:
            Dict[str, Any]: 订阅摘要
        """
        summary = {
            'total_stocks': len(self.subscribed_stocks),
            'subscription_counts': {},
            'limits': self.subscription_limits.copy(),
            'usage_rates': {}
        }
        
        # 统计各类型订阅数量
        for sub_type in self.subscription_limits.keys():
            count = self.get_subscription_count(sub_type)
            summary['subscription_counts'][sub_type] = count
            
            # 计算使用率
            limit = self.subscription_limits[sub_type]
            if limit > 0:
                usage_rate = (count / limit) * 100
                summary['usage_rates'][sub_type] = round(usage_rate, 2)
        
        return summary

    # ================== K线数据接口 ==================
    
    def request_history_kline(self, code: str, start: str, end: str, ktype: str = "K_DAY", autype: str = "qfq", max_count: int = 1000) -> pd.DataFrame:
        """请求历史K线数据"""
        try:
            # 使用关键字参数避免参数顺序错误
            kline_data, _ = self.client.quote.request_history_kline(
                code=code, 
                start=start, 
                end=end, 
                ktype=ktype, 
                autype=autype, 
                max_count=max_count
            )
            # 将返回的 KLineData 对象列表转换为 DataFrame
            if kline_data:
                df_data = []
                for kline in kline_data:
                    df_data.append({
                        'time_key': kline.time_key,
                        'open': kline.open,
                        'high': kline.high,
                        'low': kline.low,
                        'close': kline.close,
                        'volume': kline.volume,
                        'turnover': kline.turnover
                    })
                df = pd.DataFrame(df_data)
                self.logger.info(f"Successfully retrieved {len(df)} history kline records for {code}")
                return df
            else:
                self.logger.warning(f"No history kline data found for {code}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Request history kline error: {e}")
            return pd.DataFrame()

    def get_cur_kline(self, codes: List[str], num: int = 100, ktype: str = "K_DAY", autype: str = "qfq") -> List:
        """获取当前K线数据"""
        try:
            # 智能订阅检测 - 根据ktype确定需要的订阅类型
            subscription_type = self._get_subscription_type_from_ktype(ktype)
            if not self._ensure_auto_subscription(codes, subscription_type):
                self.logger.warning(f"无法确保 {codes} 的 {subscription_type} 数据订阅，可能影响K线数据获取")
            
            # 修复API方法名称不匹配的问题
            if len(codes) == 1:
                # 单个股票调用get_current_kline
                return self.client.quote.get_current_kline(codes[0], ktype, num, autype)
            else:
                # 多个股票需要逐个调用
                results = []
                for code in codes:
                    result = self.client.quote.get_current_kline(code, ktype, num, autype)
                    results.extend(result)
                return results
        except Exception as e:
            self.logger.error(f"Get cur kline error: {e}")
            return []

    def get_autype_list(self, codes: List[str]) -> List:
        """获取复权因子列表"""
        try:
            return self.client.quote.get_autype_list(codes)
        except Exception as e:
            self.logger.error(f"Get autype list error: {e}")
            return []

    # ================== 基本数据接口 ==================
    
    def get_capital_flow(self, code: str, period_type: str = "INTRADAY") -> List:
        """获取资金流向"""
        try:
            return self.client.quote.get_capital_flow(code, period_type)
        except Exception as e:
            self.logger.error(f"Get capital flow error: {e}")
            return []

    def get_capital_distribution(self, code: str) -> List:
        """获取资金分布"""
        try:
            return self.client.quote.get_capital_distribution(code)
        except Exception as e:
            self.logger.error(f"Get capital distribution error: {e}")
            return []

    def get_owner_plate(self, codes: List[str]) -> List:
        """获取股票所属板块"""
        try:
            return self.client.quote.get_owner_plate(codes)
        except Exception as e:
            self.logger.error(f"Get owner plate error: {e}")
            return []

    def get_rehab(self, code: str) -> List:
        """获取复权信息"""
        try:
            return self.client.quote.get_rehab(code)
        except Exception as e:
            self.logger.error(f"Get rehab error: {e}")
            return []

    # ================== 衍生品接口 ==================
    
    def get_option_expiration_date(self, owner_stock_code: str) -> List:
        """获取期权到期日"""
        try:
            if hasattr(self.client.quote, 'get_option_expiration_date'):
                return self.client.quote.get_option_expiration_date(owner_stock_code)
            else:
                self.logger.warning("get_option_expiration_date method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get option expiration date error: {e}")
            return []

    def get_option_chain(self, owner_stock_code: str, expiry_date: str = "", option_type: str = "ALL") -> List:
        """获取期权链"""
        try:
            if hasattr(self.client.quote, 'get_option_chain'):
                return self.client.quote.get_option_chain(owner_stock_code, expiry_date, option_type)
            else:
                self.logger.warning("get_option_chain method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get option chain error: {e}")
            return []

    def get_warrant(self, begin: int = 0, num: int = 200, sort_field: str = "code", **kwargs) -> List:
        """获取窝轮"""
        try:
            if hasattr(self.client.quote, 'get_warrant'):
                return self.client.quote.get_warrant(begin, num, sort_field, **kwargs)
            else:
                self.logger.warning("get_warrant method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get warrant error: {e}")
            return []

    def get_future_info(self, codes: List[str]) -> List:
        """获取期货信息"""
        try:
            if hasattr(self.client.quote, 'get_future_info'):
                return self.client.quote.get_future_info(codes)
            else:
                self.logger.warning("get_future_info method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get future info error: {e}")
            return []

    # ================== 全市场筛选接口 ==================
    
    def get_stock_filter(self, **kwargs) -> List:
        """股票筛选"""
        try:
            return self.client.quote.get_stock_filter(**kwargs)
        except Exception as e:
            self.logger.error(f"Get stock filter error: {e}")
            return []

    def get_plate_stock(self, plate_code: str, sort_field: str = "code") -> List:
        """获取板块股票"""
        try:
            if hasattr(self.client.quote, 'get_plate_stock'):
                return self.client.quote.get_plate_stock(plate_code, sort_field)
            else:
                self.logger.warning("get_plate_stock method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get plate stock error: {e}")
            return []

    def get_plate_list(self, market: str = "HK", plate_class: str = "ALL") -> List:
        """获取板块列表"""
        try:
            return self.client.quote.get_plate_list(market, plate_class)
        except Exception as e:
            self.logger.error(f"Get plate list error: {e}")
            return []

    def get_stock_basicinfo(self, market: str = "HK", stock_type: str = "STOCK") -> List:
        """获取股票基本信息"""
        try:
            return self.client.quote.get_stock_info(market, stock_type)
        except Exception as e:
            self.logger.error(f"Get stock basicinfo error: {e}")
            return []
    
    def get_stock_basicinfo_multi_types(self, market: str = "HK", stock_types: List[str] = None) -> List:
        """获取多种类型证券的基本信息并合并结果
        
        Args:
            market: 市场代码，如 "HK", "US", "SH", "SZ"
            stock_types: 证券类型列表，如 ["STOCK", "IDX", "ETF"]
            
        Returns:
            List: 合并后的证券基本信息列表
        """
        if stock_types is None:
            stock_types = ["STOCK", "IDX", "ETF"]
        
        all_results = []
        
        for stock_type in stock_types:
            try:
                self.logger.debug(f"获取 {market} 市场 {stock_type} 类型证券信息")
                results = self.client.quote.get_stock_info(market, stock_type)
                
                if results:
                    all_results.extend(results)
                    self.logger.debug(f"获取到 {len(results)} 只 {stock_type} 类型证券")
                else:
                    self.logger.debug(f"{market} 市场 {stock_type} 类型证券信息为空")
                    
            except Exception as e:
                self.logger.error(f"获取 {market} 市场 {stock_type} 类型证券信息失败: {e}")
                continue
        
        self.logger.info(f"合并 {market} 市场证券信息完成，共获取 {len(all_results)} 只证券")
        return all_results

    def get_ipo_list(self, market: str = "HK") -> List:
        """获取IPO列表"""
        try:
            if hasattr(self.client.quote, 'get_ipo_list'):
                return self.client.quote.get_ipo_list(market)
            else:
                self.logger.warning("get_ipo_list method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get IPO list error: {e}")
            return []

    def get_reference_stock_list(self, code: str, reference_type: str = "WARRANT") -> List:
        """获取相关股票列表"""
        try:
            return self.client.quote.get_reference_stock_list(code, reference_type)
        except Exception as e:
            self.logger.error(f"Get reference stock list error: {e}")
            return []

    def request_trading_days(self, market: str = "HK", start: Optional[str] = None, end: Optional[str] = None) -> List:
        """获取交易日"""
        try:
            return self.client.quote.request_trading_days(market, start, end)
        except Exception as e:
            self.logger.error(f"Request trading days error: {e}")
            return []

    # ================== 个性化功能接口 ==================
    
    def set_price_reminder(self, code: str, value: float, reminder_type: str = "PRICE_UP", enable: bool = True) -> bool:
        """设置到价提醒"""
        try:
            if hasattr(self.client.quote, 'set_price_reminder'):
                return self.client.quote.set_price_reminder(code, value, reminder_type, enable)
            else:
                self.logger.warning("set_price_reminder method not available")
                return False
        except Exception as e:
            self.logger.error(f"Set price reminder error: {e}")
            return False

    def get_price_reminder(self, code: Optional[str] = None) -> List:
        """获取到价提醒"""
        try:
            if hasattr(self.client.quote, 'get_price_reminder'):
                return self.client.quote.get_price_reminder(code)
            else:
                self.logger.warning("get_price_reminder method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get price reminder error: {e}")
            return []

    def get_user_security_group(self, group_type: str = "CUSTOM") -> List:
        """获取自选股分组"""
        try:
            if hasattr(self.client.quote, 'get_user_security_group'):
                return self.client.quote.get_user_security_group(group_type)
            else:
                self.logger.warning("get_user_security_group method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get user security group error: {e}")
            return []

    def get_user_security(self, group_name: str = "自选股") -> List:
        """获取自选股"""
        try:
            if hasattr(self.client.quote, 'get_user_security'):
                return self.client.quote.get_user_security(group_name)
            else:
                self.logger.warning("get_user_security method not available")
                return []
        except Exception as e:
            self.logger.error(f"Get user security error: {e}")
            return []

    def modify_user_security(self, group_name: str, codes: List[str], op_type: str = "ADD") -> bool:
        """修改自选股"""
        try:
            if hasattr(self.client.quote, 'modify_user_security'):
                # 修复参数顺序：确保与 api/futu_quote.py 中的期望一致
                # api/futu_quote.py 期待的参数顺序：(group_name, operation, code_list)
                return self.client.quote.modify_user_security(group_name, op_type, codes)
            else:
                self.logger.warning("modify_user_security method not available")
                return False
        except Exception as e:
            self.logger.error(f"Modify user security error: {e}")
            return False

    # ================== 配额管理接口 ==================
    
    def get_history_kl_quota(self) -> Dict:
        """获取历史K线配额"""
        try:
            return self.client.quote.get_history_kl_quota()
        except Exception as e:
            self.logger.error(f"Get history kl quota error: {e}")
            return {}

    # ================== 兼容性方法 ==================
    
    def update_plate_list(self):
        """更新板块列表（兼容旧接口）"""
        try:
            self.plate_list = self.get_plate_list()
            self.logger.info("Plate list updated successfully")
        except Exception as e:
            self.logger.error(f"Update plate list error: {e}")

    def update_owner_plate(self, codes: List[str]):
        """更新股票所属板块（兼容旧接口）"""
        try:
            self.owner_plate = self.get_owner_plate(codes)
            self.logger.info("Owner plate updated successfully")
        except Exception as e:
            self.logger.error(f"Update owner plate error: {e}")

    def kline_subscribe(self, codes: List[str], ktype: str = "K_DAY"):
        """K线订阅（兼容旧接口）"""
        try:
            sub_types = ["K_DAY", "K_1M", "K_5M", "K_15M", "K_30M", "K_60M"]
            if ktype in sub_types:
                return self.subscribe(codes, [ktype])
            else:
                return self.subscribe(codes, ["K_DAY"])
        except Exception as e:
            self.logger.error(f"Kline subscribe error: {e}")
            return False

    def display_quota(self):
        """显示配额（兼容旧接口）"""
        try:
            quota = self.get_history_kl_quota()
            self.logger.info(f"Current quota: {quota}")
            return quota
        except Exception as e:
            self.logger.error(f"Display quota error: {e}")
            return {}

    def get_data_realtime(self, codes: List[str], fields: List[str] = None):
        """获取实时数据（兼容旧接口）"""
        try:
            if fields:
                # 如果指定字段，使用get_cur_kline
                return self.get_cur_kline(codes, num=1)
            else:
                # 否则获取快照数据
                return self.get_market_snapshot(codes)
        except Exception as e:
            self.logger.error(f"Get data realtime error: {e}")
            return []

    def get_filtered_turnover_stocks(self, **kwargs):
        """获取筛选后的成交股票（兼容旧接口）"""
        try:
            return self.get_stock_filter(**kwargs)
        except Exception as e:
            self.logger.error(f"Get filtered turnover stocks error: {e}")
            return []
    
    
    # ================== 订阅管理器辅助方法 ==================
    
    def _get_subscription_type_from_ktype(self, ktype: str) -> str:
        """
        将K线类型转换为对应的订阅类型
        
        Args:
            ktype: K线类型，如 "K_DAY", "K_1M" 等
            
        Returns:
            str: 对应的订阅类型
        """
        ktype_mapping = {
            'K_1M': 'kline_1m',
            'K_5M': 'kline_5m', 
            'K_15M': 'kline_15m',
            'K_30M': 'kline_30m',
            'K_60M': 'kline_60m',
            'K_DAY': 'kline_day',
            'K_WEEK': 'kline_week',
            'K_MON': 'kline_month'
        }
        return ktype_mapping.get(ktype, 'kline_day')  # 默认返回日K订阅
    
    def _ensure_auto_subscription(self, codes, sub_type: str) -> bool:
        """
        智能订阅检测和自动订阅
        
        Args:
            codes: 股票代码，可以是单个字符串或列表
            sub_type: 订阅类型
            
        Returns:
            bool: 是否成功确保订阅
        """
        try:
            # 标准化代码格式为列表
            if isinstance(codes, str):
                code_list = [codes]
            else:
                code_list = codes
            
            # 检查是否需要订阅
            need_subscribe = []
            for code in code_list:
                if not self.is_subscribed(code, sub_type):
                    need_subscribe.append(code)
            
            # 如果有需要订阅的股票，执行自动订阅
            if need_subscribe:
                success = self.ensure_subscription(need_subscribe, [sub_type])
                if success:
                    self.logger.info(f"自动订阅成功: {len(need_subscribe)} 只股票的 {sub_type} 数据")
                else:
                    self.logger.warning(f"自动订阅失败: {need_subscribe} 的 {sub_type} 数据")
                return success
            else:
                # 所有股票都已订阅
                return True
                
        except Exception as e:
            self.logger.error(f"智能订阅检测异常: {e}")
            return False
    
    def ensure_subscription_single(self, code: str, sub_type: str) -> bool:
        """
        确保单个股票的单个类型订阅
        这是 ensure_subscription 的便捷方法
        
        Args:
            code: 股票代码
            sub_type: 订阅类型
            
        Returns:
            bool: 是否成功确保订阅
        """
        return self.ensure_subscription([code], [sub_type])
    
    def get_unsubscribed_stocks(self, codes: List[str], sub_type: str) -> List[str]:
        """
        获取未订阅指定类型的股票列表
        
        Args:
            codes: 要检查的股票代码列表
            sub_type: 订阅类型
            
        Returns:
            List[str]: 未订阅的股票代码列表
        """
        unsubscribed = []
        for code in codes:
            if not self.is_subscribed(code, sub_type):
                unsubscribed.append(code)
        return unsubscribed
    
    def cleanup_subscription_manager(self):
        """
        清理订阅管理器
        在关闭连接前调用此方法进行清理
        """
        try:
            # 取消所有订阅
            self.unsubscribe_all()
            
            # 清理本地状态
            self.subscribed_stocks.clear()
            
            self.logger.info("订阅管理器清理完成")
            
        except Exception as e:
            self.logger.error(f"清理订阅管理器异常: {e}")
