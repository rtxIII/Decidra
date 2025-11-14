#对应https://openapi.futunn.com/futu-api-doc/quote/overview.html
"""
富途API基础类
提供统一的富途OpenAPI封装和基础功能
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from utils import logger
from utils.global_vars import *

# 使用新的API封装
from api.futu import create_client
from base.futu_class import FutuException


class FutuModuleBase:
    """
    富途API基础类
    
    提供连接管理和基础功能，其他功能类继承此类
    """
    
    def __init__(self):
        """初始化富途基础管理器"""
        self.config = config
        self.logger = get_logger("futu_base")

        # 获取配置信息 - 修正配置节名称
        credential_config = self.config['FutuOpenD.Credential']
        futu_config = self.config['FutuOpenD.Config']  # 修正：使用正确的配置节名称
        
        self.password_md5 = credential_config.get('Password_md5')
        self.host = futu_config.get('Host', '127.0.0.1')
        self.port = int(futu_config.get('Port', '11111'))
        
        # 连接状态标志
        self._is_closed = False
        
        # 创建客户端
        try:
            self.client = create_client(
                host=self.host,
                port=self.port,
                password_md5=self.password_md5
            )
            self.logger.info("FutuBase initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize FutuBase: {e}")
            raise

    def open(self):
        """启动连接"""
        self._is_closed = False
        self.client.connect()
    
    def check(self):
        _re, _st =  self.get_connection_state()
        if not _re:
            self.open()
            return self.get_connection_state()
        return _re


    def close(self):
        """优雅关闭连接"""
        # 检查是否已经关闭或客户端不存在
        if self._is_closed or not hasattr(self, 'client') or self.client is None:
            return
        
        # 设置关闭标志，防止重复关闭
        self._is_closed = True
            
        try:
            self.logger.info("开始关闭富途连接...")
            
            # 1. 先取消所有订阅（快速操作）
            try:
                if hasattr(self.client, 'quote') and self.client.quote:
                    self.client.quote.unsubscribe_all()
                    self.logger.info("取消订阅完成")
            except Exception as e:
                self.logger.warning(f"取消订阅时出错: {e}")
            
            # 2. 使用富途API标准的disconnect方法（同步执行）
            try:
                self.client.disconnect()
                self.logger.info("富途连接已关闭")
            except Exception as e:
                self.logger.warning(f"断开连接时出错: {e}")
                
        except Exception as e:
            self.logger.warning(f"关闭富途连接时出错: {e}")
        finally:
            # 确保客户端引用被清除
            self.client = None
            self.logger.info("富途客户端引用已清除")

    def _unlock_trade(self):
        """解锁交易功能"""
        try:
            if self.password_md5:
                self.client.trade.unlock_trade(password_md5=self.password_md5)
                self.logger.info("Trading unlocked successfully")
            else:
                self.logger.warning("No password provided for trading unlock")
        except Exception as e:
            self.logger.error(f"Failed to unlock trading: {e}")

    def get_connection_state(self) -> tuple:
        """获取连接状态"""
        try:
            if hasattr(self.client, 'is_connected'):
                is_connected = self.client.is_connected
                return is_connected, "Connected" if is_connected else "Disconnected"
            else:
                # 回退：尝试简单的API调用来测试连接
                test_result = self.client.quote.get_global_state()
                if test_result:
                    return True, "Connected"
                else:
                    return False, "API test failed"
        except Exception as e:
            self.logger.error(f"Get connection state error: {e}")
            return False, f"Connection error: {e}"

    def is_normal_trading_time(self, stock_list: List[str]) -> bool:
        """检查是否在正常交易时间"""
        try:
            if not stock_list:
                return False
            
            # 使用第一只股票检查交易时间
            sample_code = stock_list[0]
            market_state = self.client.quote.get_market_state([sample_code])
            
            if market_state and len(market_state) > 0:
                state = market_state[0].get('market_state', 'UNKNOWN')
                self.logger.info(f"Market state for {sample_code}: {state}")
                return state in ['NORMAL', 'OPEN']
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to check trading time: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "connection_status": "disconnected",
                "quote_service": "unavailable", 
                "trade_service": "unavailable",
                "subscription_quota": {},
                "errors": []
            }
            
            # 检查连接状态
            try:
                connected, msg = self.get_connection_state()
                health_status["connection_status"] = "connected" if connected else "disconnected"
                if not connected:
                    health_status["errors"].append(f"Connection error: {msg}")
            except Exception as e:
                health_status["errors"].append(f"Connection check failed: {e}")
            
            # 检查行情服务
            try:
                test_data = self.client.quote.get_market_state(["HK.00700"])
                health_status["quote_service"] = "available" if test_data else "unavailable"
            except Exception as e:
                health_status["quote_service"] = "unavailable"
                health_status["errors"].append(f"Quote service error: {e}")
            
            # 检查交易服务
            try:
                self._unlock_trade()
                account_info = self.client.trade.get_account_info()
                health_status["trade_service"] = "available" if account_info is not None else "unavailable"
            except Exception as e:
                health_status["trade_service"] = "unavailable"
                health_status["errors"].append(f"Trade service error: {e}")
            
            # 检查订阅配额
            try:
                quota = self.client.quote.get_history_kl_quota()
                health_status["subscription_quota"] = quota if quota else {}
            except Exception as e:
                health_status["errors"].append(f"Quota check failed: {e}")
            
            self.logger.info(f"Health check completed. Status: {health_status['connection_status']}")
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "connection_status": "error",
                "quote_service": "error",
                "trade_service": "error", 
                "subscription_quota": {},
                "errors": [str(e)]
            } 