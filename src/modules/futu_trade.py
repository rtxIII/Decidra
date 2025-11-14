#对应https://openapi.futunn.com/futu-api-doc/trade/overview.html
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable

import pandas as pd

from utils import logger
from utils.global_vars import *

# 使用新的API封装
from base.futu_modue import FutuModuleBase


class FutuTrade(FutuModuleBase):
    """
    富途交易业务逻辑层
    
    继承FutuModuleBase，提供完整的富途交易接口
    对应: https://openapi.futunn.com/futu-api-doc/trade/overview.html
    使用时需先调用open方法, 务必close
    """
    
    def __init__(self, default_trd_env: str = "SIMULATE", default_market: str = "HK", default_currency: str = "HKD"):
        """初始化富途交易管理器"""
        super().__init__()
        self.logger = get_logger("futu_trade")
        
        # 默认交易配置
        self.default_trd_env = default_trd_env
        self.default_market = default_market
        self.default_currency = default_currency
        
        # 业务数据缓存
        self.account_info = None
        self.position_list = None
        self.order_history = []
        self.deal_history = []
        
        # 交易状态管理
        self.is_trade_unlocked = False
        self.order_callbacks = {}
        self.deal_callbacks = {}
        
        # 风险控制参数
        self.risk_config = {
            "max_single_order_amount": 100000,  # 单笔最大下单金额
            "max_position_ratio": 0.3,  # 单只股票最大持仓比例
            "enable_risk_control": False  # 是否启用风险控制
        }
        
        self.logger.info(f"FutuTrade initialized with {default_trd_env} environment")

        self.check()

    # ================== 账户管理接口 ==================
    
    def get_account_list(self, market: str = None) -> List[Dict]:
        """获取账户列表"""
        try:
            market = market or self.default_market
            result = self.client.trade.get_acc_list(market)

            if isinstance(result, pd.DataFrame):
                return result.to_dict('records')
            if isinstance(result, dict):
                return [result]
            return result if isinstance(result, list) else []

        except Exception as e:
            self.logger.error(f"Get account list error: {e}")
            return []
    
    def unlock_trading(self, password: str = None, market: str = "HK") -> bool:
        """解锁交易功能"""
        try:
            market = market or self.default_market
            password = password or self.password_md5
            
            if not password:
                self.logger.error("No password provided for trading unlock")
                return False
            
            result = self.client.trade.unlock_trade(password, market)
            
            if result:
                self.is_trade_unlocked = True
                self.logger.info(f"Trading unlocked successfully for {market}")
                return True
            else:
                self.logger.error("Failed to unlock trading")
                return False
                
        except Exception as e:
            self.logger.error(f"Unlock trading error: {e}")
            return False

    def unlock_trade(self, password: str = None, market: str = None) -> bool:
        """解锁交易功能 - 兼容性方法"""
        return self.unlock_trading(password, market)

    def get_account_info(self, trd_env: str = None, market: str = None, currency: str = None) -> Dict:
        """获取账户信息"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            currency = currency or self.default_currency

            result = self.client.trade.get_account_info(trd_env, market, currency)

            if isinstance(result, pd.DataFrame) and not result.empty:
                # 如果返回DataFrame，取第一行转为字典
                self.account_info = result.iloc[0].to_dict()
                return self.account_info
            elif isinstance(result, dict) and result:
                # 如果返回字典，直接使用
                self.account_info = result
                return self.account_info

            return {}

        except Exception as e:
            self.logger.error(f"Get account info error: {e}")
            return {}
    
    def get_funds_info(self, trd_env: str = None, market: str = None, currency: str = None) -> Dict:
        """获取资金信息"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            currency = currency or self.default_currency

            result = self.client.trade.get_funds(trd_env, market, currency)

            if isinstance(result, (pd.DataFrame, dict)):
                # 处理DataFrame返回
                if isinstance(result, pd.DataFrame) and not result.empty:
                    funds_info = result.iloc[0].to_dict()
                # 处理dict返回
                elif isinstance(result, dict):
                    funds_info = result.copy()
                else:
                    return {"success": False, "message": "No funds data available"}

                funds_info['success'] = True
                funds_info['timestamp'] = datetime.now().isoformat()
                return funds_info

            return {"success": False, "message": "No funds data available"}

        except Exception as e:
            self.logger.error(f"Get funds info error: {e}")
            return {"success": False, "message": str(e)}
    
    def get_cash_flow(self, trd_env: str = None, market: str = None,
                     start: str = None, end: str = None, currency: str = None) -> List[Dict]:
        """获取现金流水"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            currency = currency or self.default_currency

            result = self.client.trade.get_cash_flow(trd_env, market, start, end, currency)

            if isinstance(result, pd.DataFrame):
                return result.to_dict('records')
            if isinstance(result, dict):
                return [result]

            return []

        except Exception as e:
            self.logger.error(f"Get cash flow error: {e}")
            return []

    def get_funds(self, trd_env: str = None, market: str = None, currency: str = None) -> Dict:
        """获取资金信息 - 兼容性方法"""
        return self.get_funds_info(trd_env, market, currency)

    def get_acc_list(self, market: str = None) -> List[Dict]:
        """获取账户列表 - 兼容性方法"""
        return self.get_account_list(market)

    # ================== 持仓管理接口 ==================
    
    def get_position_list(self, trd_env: str = None, market: str = None, 
                         code: str = None, currency: str = None) -> List[Dict]:
        """获取持仓列表"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            currency = currency or self.default_currency
            
            result = self.client.trade.get_position_list(trd_env, market, code)
            
            if isinstance(result, pd.DataFrame):
                self.position_list = result.to_dict('records')
                return self.position_list
            if isinstance(result, dict):
                return [result]
            self.logger.warning(f"get_position_list return error: {result}")
            return []
            
        except Exception as e:
            self.logger.error(f"Get position list error: {e}")
            return []
    
    def get_position_by_code(self, code: str, trd_env: str = None, market: str = None) -> Dict:
        """获取特定股票的持仓信息"""
        try:
            positions = self.get_position_list(trd_env, market, code)
            
            for position in positions:
                if position.get('code') == code:
                    return position
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Get position by code error: {e}")
            return {}
    
    def get_total_position_value(self, trd_env: str = None, market: str = None) -> float:
        """获取总持仓市值"""
        try:
            positions = self.get_position_list(trd_env, market)
            
            total_value = 0.0
            for position in positions:
                qty = position.get('qty', 0)
                cur_price = position.get('nominal_price', 0)
                total_value += qty * cur_price
            
            return total_value
            
        except Exception as e:
            self.logger.error(f"Get total position value error: {e}")
            return 0.0

    # ================== 订单管理接口 ==================
    
    def place_order(self, code: str, price: float, qty: int,
                   order_type: str = "NORMAL",
                   trd_side: str = "BUY",
                   aux_price: Optional[float] = None,
                   trd_env: str = "SIMULATE",
                   market: str = None,
                   enable_risk_check: bool = True) -> Dict:
        """下单"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            
            # 风险检查
            if enable_risk_check and not self._risk_check_order(code, price, qty, trd_side, trd_env, market):
                return {"success": False, "message": "Risk check failed"}
            
            # 检查交易解锁状态
            if not self.is_trade_unlocked and trd_env != "SIMULATE":
                if not self.unlock_trading():
                    return {"success": False, "message": "Trading not unlocked"}
            
            result = self.client.trade.place_order(
                code=code, price=price, qty=qty,
                order_type=order_type, trd_side=trd_side,
                aux_price=aux_price,
                trd_env=trd_env, market=market
            )
            
            if isinstance(result, (pd.DataFrame, dict)):
                # 处理DataFrame返回
                if isinstance(result, pd.DataFrame) and not result.empty:
                    order_info = result.iloc[0].to_dict()
                # 处理dict返回
                elif isinstance(result, dict):
                    order_info = result.copy()
                else:
                    return {"success": False, "message": "Order placement failed"}

                order_info['success'] = True
                order_info['timestamp'] = datetime.now().isoformat()

                # 记录订单历史
                self.order_history.append(order_info)

                self.logger.info(f"Order placed successfully: {code} {trd_side} {qty}@{price}")
                return order_info

            return {"success": False, "message": "Order placement failed"}
            
        except Exception as e:
            self.logger.error(f"Place order error: {e}")
            return {"success": False, "message": str(e)}
    
    def cancel_order(self, order_id: str, trd_env: str = None, market: str = None) -> Dict:
        """撤销订单"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            
            result = self.client.trade.cancel_order(order_id, trd_env, market)
            
            if isinstance(result, (pd.DataFrame, dict)):
                # 处理DataFrame返回
                if isinstance(result, pd.DataFrame) and not result.empty:
                    cancel_info = result.iloc[0].to_dict()
                # 处理dict返回
                elif isinstance(result, dict):
                    cancel_info = result.copy()
                else:
                    return {"success": False, "message": "Order cancellation failed"}

                cancel_info['success'] = True
                cancel_info['timestamp'] = datetime.now().isoformat()

                self.logger.info(f"Order cancelled successfully: {order_id}")
                return cancel_info

            return {"success": False, "message": "Order cancellation failed"}
            
        except Exception as e:
            self.logger.error(f"Cancel order error: {e}")
            return {"success": False, "message": str(e)}
    
    def modify_order(self, order_id: str, price: float = None, qty: int = None,
                    trd_env: str = None, market: str = None) -> Dict:
        """修改订单"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market
            
            result = self.client.trade.modify_order(order_id, price, qty, trd_env, market)
            
            if isinstance(result, (pd.DataFrame, dict)):
                # 处理DataFrame返回
                if isinstance(result, pd.DataFrame) and not result.empty:
                    modify_info = result.iloc[0].to_dict()
                # 处理dict返回
                elif isinstance(result, dict):
                    modify_info = result.copy()
                else:
                    return {"success": False, "message": "Order modification failed"}

                modify_info['success'] = True
                modify_info['timestamp'] = datetime.now().isoformat()

                self.logger.info(f"Order modified successfully: {order_id}")
                return modify_info

            return {"success": False, "message": "Order modification failed"}
            
        except Exception as e:
            self.logger.error(f"Modify order error: {e}")
            return {"success": False, "message": str(e)}
    
    def get_order_list(self, order_status: str = None, trd_env: str = None,
                      market: str = None, start: str = None, end: str = None) -> List[Dict]:
        """获取订单列表"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_order_list(order_status, trd_env, market, start, end)

            if isinstance(result, pd.DataFrame):
                return result.to_dict('records')
            if isinstance(result, dict):
                return [result]

            return []

        except Exception as e:
            self.logger.error(f"Get order list error: {e}")
            return []
    
    def get_deal_list(self, trd_env: str = None, market: str = None) -> List[Dict]:
        """获取成交列表"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_deal_list(trd_env, market)

            if isinstance(result, pd.DataFrame):
                self.deal_history = result.to_dict('records')
                return self.deal_history
            if isinstance(result, dict):
                self.deal_history = [result]
                return self.deal_history

            return []

        except Exception as e:
            self.logger.error(f"Get deal list error: {e}")
            return []

    def get_history_order_list(self, trd_env: str = None, market: str = None,
                              start: str = None, end: str = None) -> List[Dict]:
        """获取历史订单列表"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_history_order_list(trd_env, market, start, end)

            if isinstance(result, pd.DataFrame):
                return result.to_dict('records')
            if isinstance(result, dict):
                return [result]

            return []

        except Exception as e:
            self.logger.error(f"Get history order list error: {e}")
            return []

    def get_history_deal_list(self, trd_env: str = None, market: str = None,
                             start: str = None, end: str = None) -> List[Dict]:
        """获取历史成交列表"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_history_deal_list(trd_env, market, start, end)

            if isinstance(result, pd.DataFrame):
                return result.to_dict('records')
            if isinstance(result, dict):
                return [result]

            return []

        except Exception as e:
            self.logger.error(f"Get history deal list error: {e}")
            return []

    # ================== 交易工具接口 ==================
    
    def get_max_buy_qty(self, code: str, price: float, trd_env: str = None, market: str = None) -> int:
        """获取最大买入数量"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_max_trd_qty("NORMAL", code, price, "BUY", trd_env, market)

            if isinstance(result, pd.DataFrame) and not result.empty:
                return int(result.iloc[0].get('max_qty', 0))
            if isinstance(result, dict):
                return int(result.get('max_qty', 0))

            return 0

        except Exception as e:
            self.logger.error(f"Get max buy qty error: {e}")
            return 0
    
    def get_max_sell_qty(self, code: str, price: float, trd_env: str = None, market: str = None) -> int:
        """获取最大卖出数量"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_max_trd_qty("NORMAL", code, price, "SELL", trd_env, market)

            if isinstance(result, pd.DataFrame) and not result.empty:
                return int(result.iloc[0].get('max_qty', 0))
            if isinstance(result, dict):
                return int(result.get('max_qty', 0))

            return 0

        except Exception as e:
            self.logger.error(f"Get max sell qty error: {e}")
            return 0
    
    def get_order_fee(self, code: str, price: float, qty: int,
                     order_type: str = "NORMAL", trd_side: str = "BUY",
                     trd_env: str = None, market: str = None) -> Dict:
        """获取订单费用预估"""
        try:
            trd_env = trd_env or self.default_trd_env
            market = market or self.default_market

            result = self.client.trade.get_order_fee(
                order_type, code, price, qty, trd_side, trd_env, market
            )

            if isinstance(result, pd.DataFrame) and not result.empty:
                return result.iloc[0].to_dict()
            if isinstance(result, dict):
                return result

            return {}

        except Exception as e:
            self.logger.error(f"Get order fee error: {e}")
            return {}

    # ================== 高级交易功能 ==================
    
    def market_buy(self, code: str, amount: float, trd_env: str = None, market: str = None) -> Dict:
        """市价买入（按金额）"""
        try:
            # 获取当前市价
            current_price = self._get_current_price(code)
            if not current_price:
                return {"success": False, "message": "Cannot get current price"}
            
            # 计算购买数量
            qty = int(amount / current_price)
            if qty <= 0:
                return {"success": False, "message": "Invalid quantity"}
            
            # 市价下单
            return self.place_order(code, current_price, qty, "MARKET", "BUY", trd_env, market)
            
        except Exception as e:
            self.logger.error(f"Market buy error: {e}")
            return {"success": False, "message": str(e)}
    
    def market_sell(self, code: str, qty: int = None, trd_env: str = None, market: str = None) -> Dict:
        """市价卖出（全部或指定数量）"""
        try:
            # 如果不指定数量，卖出全部持仓
            if qty is None:
                position = self.get_position_by_code(code, trd_env, market)
                if not position:
                    return {"success": False, "message": "No position found"}
                qty = position.get('qty', 0)
            
            if qty <= 0:
                return {"success": False, "message": "Invalid quantity"}
            
            # 获取当前市价
            current_price = self._get_current_price(code)
            if not current_price:
                return {"success": False, "message": "Cannot get current price"}
            
            # 市价下单
            return self.place_order(code, current_price, qty, "MARKET", "SELL", trd_env, market)
            
        except Exception as e:
            self.logger.error(f"Market sell error: {e}")
            return {"success": False, "message": str(e)}
    
    def batch_place_orders(self, orders: List[Dict], trd_env: str = None, market: str = None) -> List[Dict]:
        """批量下单"""
        results = []
        
        for order in orders:
            try:
                result = self.place_order(
                    code=order['code'],
                    price=order['price'],
                    qty=order['qty'],
                    order_type=order.get('order_type', 'NORMAL'),
                    trd_side=order.get('trd_side', 'BUY'),
                    trd_env=trd_env,
                    market=market,
                    enable_risk_check=order.get('enable_risk_check', True)
                )
                results.append(result)
                
                # 添加延时避免频繁请求
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Batch order error: {e}")
                results.append({"success": False, "message": str(e)})
        
        return results
    
    def batch_cancel_orders(self, order_ids: List[str], trd_env: str = None, market: str = None) -> List[Dict]:
        """批量撤单"""
        results = []
        
        for order_id in order_ids:
            try:
                result = self.cancel_order(order_id, trd_env, market)
                results.append(result)
                
                # 添加延时避免频繁请求
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Batch cancel error: {e}")
                results.append({"success": False, "message": str(e)})
        
        return results

    # ================== 风险控制接口 ==================
    
    def set_risk_config(self, config: Dict) -> bool:
        """设置风险控制配置"""
        try:
            self.risk_config.update(config)
            self.logger.info(f"Risk config updated: {config}")
            return True
        except Exception as e:
            self.logger.error(f"Set risk config error: {e}")
            return False
    
    def get_risk_config(self) -> Dict:
        """获取风险控制配置"""
        return self.risk_config.copy()
    
    def _risk_check_order(self, code: str, price: float, qty: int, trd_side: str, 
                         trd_env: str, market: str) -> bool:
        """订单风险检查"""
        try:
            if not self.risk_config.get('enable_risk_control', True):
                return True
            
            # 检查单笔订单金额
            order_amount = price * qty
            max_amount = self.risk_config.get('max_single_order_amount', 100000)
            
            if order_amount > max_amount:
                self.logger.warning(f"Order amount {order_amount} exceeds max {max_amount}")
                return False
            
            # 检查持仓比例（买入时）
            if trd_side.upper() == "BUY":
                total_value = self.get_total_position_value(trd_env, market)
                account_info = self.get_account_info(trd_env, market)
                
                if account_info:
                    total_assets = account_info.get('total_assets', 0)
                    if total_assets > 0:
                        max_ratio = self.risk_config.get('max_position_ratio', 0.3)
                        new_position_ratio = (total_value + order_amount) / total_assets
                        
                        if new_position_ratio > max_ratio:
                            self.logger.warning(f"Position ratio {new_position_ratio} exceeds max {max_ratio}")
                            return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Risk check error: {e}")
            return False
    
    def get_daily_pnl(self, trd_env: str = None, market: str = None) -> Dict:
        """获取当日盈亏"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            deals = self.get_deal_list(trd_env, market, today, today)
            
            total_pnl = 0.0
            total_fee = 0.0
            
            for deal in deals:
                pnl = deal.get('pnl', 0)
                fee = deal.get('fee', 0)
                total_pnl += pnl
                total_fee += fee
            
            return {
                'date': today,
                'total_pnl': total_pnl,
                'total_fee': total_fee,
                'net_pnl': total_pnl - total_fee,
                'deal_count': len(deals)
            }
            
        except Exception as e:
            self.logger.error(f"Get daily PnL error: {e}")
            return {}

    # ================== 事件处理接口 ==================
    
    def set_order_callback(self, callback: Callable, market: str = None):
        """设置订单回调"""
        try:
            market = market or self.default_market
            self.order_callbacks[market] = callback
            self.client.trade.set_order_callback(callback, market)
            self.logger.info(f"Order callback set for {market}")
        except Exception as e:
            self.logger.error(f"Set order callback error: {e}")
    
    def set_deal_callback(self, callback: Callable, market: str = None):
        """设置成交回调"""
        try:
            market = market or self.default_market
            self.deal_callbacks[market] = callback
            self.client.trade.set_deal_callback(callback, market)
            self.logger.info(f"Deal callback set for {market}")
        except Exception as e:
            self.logger.error(f"Set deal callback error: {e}")
    
    def enable_order_push(self, market: str = None):
        """启用订单推送"""
        try:
            market = market or self.default_market
            self.client.trade.enable_subscribe_order(market)
            self.logger.info(f"Order push enabled for {market}")
        except Exception as e:
            self.logger.error(f"Enable order push error: {e}")
    
    def enable_deal_push(self, market: str = None):
        """启用成交推送"""
        try:
            market = market or self.default_market
            self.client.trade.enable_subscribe_deal(market)
            self.logger.info(f"Deal push enabled for {market}")
        except Exception as e:
            self.logger.error(f"Enable deal push error: {e}")

    # ================== 辅助方法 ==================
    
    def _get_current_price(self, code: str) -> Optional[float]:
        """获取当前价格"""
        try:
            # 使用行情接口获取当前价格
            quotes = self.client.quote.get_stock_quote([code])
            if quotes and len(quotes) > 0:
                return quotes[0].get('cur_price', 0)
            return None
        except Exception as e:
            self.logger.error(f"Get current price error: {e}")
            return None
    
    def get_trading_status(self) -> Dict:
        """获取交易状态"""
        try:
            return {
                'is_trade_unlocked': self.is_trade_unlocked,
                'default_trd_env': self.default_trd_env,
                'default_market': self.default_market,
                'default_currency': self.default_currency,
                'risk_control_enabled': self.risk_config.get('enable_risk_control', True),
                'order_callback_set': bool(self.order_callbacks),
                'deal_callback_set': bool(self.deal_callbacks),
                'order_history_count': len(self.order_history),
                'deal_history_count': len(self.deal_history)
            }
        except Exception as e:
            self.logger.error(f"Get trading status error: {e}")
            return {}
    
    def clear_cache(self):
        """清除缓存数据"""
        try:
            self.account_info = None
            self.position_list = None
            self.order_history = []
            self.deal_history = []
            self.logger.info("Cache cleared")
        except Exception as e:
            self.logger.error(f"Clear cache error: {e}")
    
    def get_performance_summary(self, days: int = 7) -> Dict:
        """获取绩效总结"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            deals = self.get_deal_list(start=start_str, end=end_str)
            
            if not deals:
                return {}
            
            total_pnl = sum(deal.get('pnl', 0) for deal in deals)
            total_fee = sum(deal.get('fee', 0) for deal in deals)
            total_amount = sum(deal.get('price', 0) * deal.get('qty', 0) for deal in deals)
            
            win_deals = [d for d in deals if d.get('pnl', 0) > 0]
            lose_deals = [d for d in deals if d.get('pnl', 0) < 0]
            
            return {
                'period': f"{start_str} to {end_str}",
                'total_deals': len(deals),
                'total_pnl': total_pnl,
                'total_fee': total_fee,
                'net_pnl': total_pnl - total_fee,
                'total_amount': total_amount,
                'win_deals': len(win_deals),
                'lose_deals': len(lose_deals),
                'win_rate': len(win_deals) / len(deals) if deals else 0,
                'avg_pnl_per_deal': total_pnl / len(deals) if deals else 0
            }
            
        except Exception as e:
            self.logger.error(f"Get performance summary error: {e}")
            return {}
    
    def health_check(self) -> Dict:
        """交易系统健康检查"""
        try:
            base_health = super().health_check()
            
            # 添加交易相关检查
            trade_health = {
                'trade_unlocked': self.is_trade_unlocked,
                'risk_control_enabled': self.risk_config.get('enable_risk_control', True),
                'order_callbacks_active': len(self.order_callbacks) > 0,
                'deal_callbacks_active': len(self.deal_callbacks) > 0,
                'recent_order_count': len([o for o in self.order_history if 
                                          datetime.fromisoformat(o.get('timestamp', '1970-01-01')).date() == datetime.now().date()]),
                'recent_deal_count': len([d for d in self.deal_history if 
                                         datetime.fromisoformat(d.get('timestamp', '1970-01-01')).date() == datetime.now().date()])
            }
            
            base_health.update(trade_health)
            return base_health
            
        except Exception as e:
            self.logger.error(f"Trade health check error: {e}")
            return {"trade_health": "error", "error": str(e)}
