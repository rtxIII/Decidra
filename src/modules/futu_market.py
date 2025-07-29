#对应https://openapi.futunn.com/futu-api-doc/quote/overview.html
import itertools
import json
import pathlib
import platform
import subprocess
import time
from datetime import date, datetime, timedelta
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import List, Dict, Any, Optional
from base.futu_class import MarketState, GlobalMarketState

import pandas as pd

from modules import DataProcessingInterface
from utils import logger
from utils.global_vars import *

# 使用新的API封装，移除旧的futu库直接调用
from api.futu import create_client
from base.futu_class import FutuException


from base.futu_modue import FutuModuleBase

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
        self.logger = logger.get_logger("futu_market")
        
        # 业务数据缓存
        self.stock_list = None  
        self.plate_list = None
        self.owner_plate = None
        
        self.logger.info("FutuMarket initialized successfully")

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
            return self.client.quote.get_stock_quote(codes)
        except Exception as e:
            self.logger.error(f"Get stock quote error: {e}")
            return []

    def get_order_book(self, codes: List[str]) -> List:
        """获取买卖盘"""
        try:
            return self.client.quote.get_order_book(codes)
        except Exception as e:
            self.logger.error(f"Get order book error: {e}")
            return []

    def get_rt_data(self, codes: List[str]) -> List:
        """获取分时数据"""
        try:
            return self.client.quote.get_rt_data(codes)
        except Exception as e:
            self.logger.error(f"Get rt data error: {e}")
            return []

    def get_rt_ticker(self, codes: List[str]) -> List:
        """获取逐笔数据"""
        try:
            return self.client.quote.get_rt_ticker(codes)
        except Exception as e:
            self.logger.error(f"Get rt ticker error: {e}")
            return []

    def get_broker_queue(self, codes: List[str]) -> List:
        """获取经纪队列"""
        try:
            return self.client.quote.get_broker_queue(codes)
        except Exception as e:
            self.logger.error(f"Get broker queue error: {e}")
            return []

    # ================== 订阅管理接口 ==================
    
    def subscribe(self, codes: List[str], sub_types: List[str], is_first_push: bool = True, is_unlimit_push: bool = False) -> bool:
        """订阅数据推送"""
        try:
            success = self.client.quote.subscribe(codes, sub_types, is_first_push, is_unlimit_push)
            if success:
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

    # ================== K线数据接口 ==================
    
    def request_history_kline(self, code: str, start: str, end: str, ktype: str = "K_DAY", autype: str = "qfq", max_count: int = 1000) -> pd.DataFrame:
        """请求历史K线数据"""
        try:
            df = self.client.quote.request_history_kline(code, start, end, ktype, autype, max_count)
            self.logger.info(f"Successfully retrieved history kline for {code}")
            return df
        except Exception as e:
            self.logger.error(f"Request history kline error: {e}")
            return pd.DataFrame()

    def get_cur_kline(self, codes: List[str], num: int = 100, ktype: str = "K_DAY", autype: str = "qfq") -> List:
        """获取当前K线数据"""
        try:
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
    
    def get_capital_flow(self, codes: List[str], period_type: str = "INTRADAY") -> List:
        """获取资金流向"""
        try:
            return self.client.quote.get_capital_flow(codes, period_type)
        except Exception as e:
            self.logger.error(f"Get capital flow error: {e}")
            return []

    def get_capital_distribution(self, codes: List[str]) -> List:
        """获取资金分布"""
        try:
            return self.client.quote.get_capital_distribution(codes)
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

    def get_rehab(self, codes: List[str]) -> List:
        """获取复权信息"""
        try:
            return self.client.quote.get_rehab(codes)
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
    
    # ================== 交易API委托接口 ==================
    
    def get_acc_list(self, market: str = "HK") -> Dict:
        """获取账户列表"""
        try:
            return self.client.trade.get_acc_list(market)
        except Exception as e:
            self.logger.error(f"Get account list error: {e}")
            return {}
    
    def unlock_trade(self, password: str, market: str = "HK") -> Dict:
        """解锁交易"""
        try:
            return self.client.trade.unlock_trade(password, market)
        except Exception as e:
            self.logger.error(f"Unlock trade error: {e}")
            return {}
    
    def get_cash_flow(self, trd_env: str = "SIMULATE", market: str = "HK",
                     start: Optional[str] = None, end: Optional[str] = None,
                     currency: str = "HKD") -> Dict:
        """获取现金流水"""
        try:
            return self.client.trade.get_cash_flow(trd_env, market, start, end, currency)
        except Exception as e:
            self.logger.error(f"Get cash flow error: {e}")
            return {}
    
    def get_funds(self, trd_env: str = "SIMULATE", market: str = "HK",
                  currency: str = "HKD") -> Dict:
        """获取账户资金"""
        try:
            return self.client.trade.get_funds(trd_env, market, currency)
        except Exception as e:
            self.logger.error(f"Get funds error: {e}")
            return {}
    
    def set_order_callback(self, callback_func, market: str = "HK"):
        """设置订单推送回调"""
        try:
            return self.client.trade.set_order_callback(callback_func, market)
        except Exception as e:
            self.logger.error(f"Set order callback error: {e}")
    
    def set_deal_callback(self, callback_func, market: str = "HK"):
        """设置成交推送回调"""
        try:
            return self.client.trade.set_deal_callback(callback_func, market)
        except Exception as e:
            self.logger.error(f"Set deal callback error: {e}")
    
    def enable_subscribe_order(self, market: str = "HK"):
        """启用订单推送订阅"""
        try:
            return self.client.trade.enable_subscribe_order(market)
        except Exception as e:
            self.logger.error(f"Enable order subscription error: {e}")
    
    def enable_subscribe_deal(self, market: str = "HK"):
        """启用成交推送订阅"""
        try:
            return self.client.trade.enable_subscribe_deal(market)
        except Exception as e:
            self.logger.error(f"Enable deal subscription error: {e}")
