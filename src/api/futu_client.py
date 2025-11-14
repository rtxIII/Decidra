"""
富途客户端核心模块

主要包含FutuClient类，负责连接管理和上下文管理。
"""

import logging
from typing import Optional
from utils.global_vars import get_logger
from base.futu_class import FutuException, FutuConnectException, FutuTradeException, FutuConfig

try:
    import futu as ft
except ImportError:
    raise ImportError(
        "futu-api is required. Install it with: pip install futu-api"
    )

ft.set_futu_debug_model(False)


class FutuClient:
    """富途API统一客户端"""
    
    def __init__(self, config: Optional[FutuConfig] = None, **kwargs):
        """
        初始化富途客户端
        
        Args:
            config: 配置对象，如果为None则使用默认配置
            **kwargs: 直接传递给FutuConfig的参数
        """
        if config is None:
            config = FutuConfig(**kwargs)
        
        self.config = config
        self._setup_logging()
        
        # 初始化上下文对象
        self._quote_ctx: Optional[ft.OpenQuoteContext] = None
        self._trade_hk_ctx: Optional[ft.OpenHKTradeContext] = None
        self._trade_us_ctx: Optional[ft.OpenUSTradeContext] = None
        self._trade_cn_ctx: Optional[ft.OpenCNTradeContext] = None
        
        # 连接状态
        self._connected = False
        self._unlocked = False
        
        # 延迟导入管理器，避免循环导入
        self._quote_manager = None
        self._trade_manager = None
        
        #self.logger = logging.getLogger(__name__)
        self.logger = get_logger(__name__)
        self.logger.info(f"FutuClient initialized with config: {self.config.host}:{self.config.port}")
    
    @property
    def quote(self):
        """获取行情管理器"""
        if self._quote_manager is None:
            from .futu_quote import QuoteManager
            self._quote_manager = QuoteManager(self)
        return self._quote_manager
    
    @property
    def trade(self):
        """获取交易管理器"""
        if self._trade_manager is None:
            from .futu_trade import TradeManager
            self._trade_manager = TradeManager(self)
        return self._trade_manager
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    @property
    def is_unlocked(self) -> bool:
        """检查交易是否已解锁"""
        return self._unlocked
    
    def connect(self) -> bool:
        """
        连接到FutuOpenD
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if self._connected:
                return 1
            # 创建行情上下文
            self._quote_ctx = ft.OpenQuoteContext(
                host=self.config.host,
                port=self.config.port,
                is_encrypt=self.config.enable_proto_encrypt,
                is_async_connect=False
            )
            
            # 测试连接
            ret, data = self._quote_ctx.get_global_state()
            if ret != ft.RET_OK:
                raise FutuConnectException(ret, data)
            
            self._connected = True
            self.logger.info("Successfully connected to FutuOpenD")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            self._cleanup_connections()
            if isinstance(e, FutuException):
                raise
            raise FutuConnectException(-1, str(e))
    
    def disconnect(self):
        """断开连接"""
        try:
            self._cleanup_connections()
            self._connected = False
            self._unlocked = False
            self.logger.info("Disconnected from FutuOpenD")
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
    
    def _cleanup_connections(self):
        """清理连接"""
        contexts = [
            self._quote_ctx,
            self._trade_hk_ctx,
            self._trade_us_ctx,
            self._trade_cn_ctx
        ]
        
        for ctx in contexts:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception as e:
                    self.logger.warning(f"Error closing context: {e}")
        
        self._quote_ctx = None
        self._trade_hk_ctx = None
        self._trade_us_ctx = None
        self._trade_cn_ctx = None
    
    def _get_trade_context(self, market: str = "HK"):
        """
        获取交易上下文
        
        Args:
            market: 市场代码 (HK/US/CN)
        
        Returns:
            交易上下文对象
        """
        if not self._connected:
            raise FutuConnectException(-1, "Not connected to FutuOpenD")
        
        market = market.upper()
        
        if market == "HK":
            if self._trade_hk_ctx is None:
                self._trade_hk_ctx = ft.OpenSecTradeContext(
                    filter_trdmarket=ft.TrdMarket.HK,
                    host=self.config.host,
                    port=self.config.port,
                    is_encrypt=self.config.enable_proto_encrypt,
                    security_firm=ft.SecurityFirm.FUTUSECURITIES
                )
            return self._trade_hk_ctx
            #if self._trade_hk_ctx is None:
            #    self._trade_hk_ctx = ft.OpenHKTradeContext(
            #        host=self.config.host,
            #        port=self.config.port,
            #        is_encrypt=self.config.enable_proto_encrypt
            #    )
            #return self._trade_hk_ctx
        
        elif market == "US":
            if self._trade_us_ctx is None:
                self._trade_us_ctx = ft.OpenUSTradeContext(
                    host=self.config.host,
                    port=self.config.port,
                    is_encrypt=self.config.enable_proto_encrypt
                )
            return self._trade_us_ctx
        
        elif market == "CN":
            if self._trade_cn_ctx is None:
                self._trade_cn_ctx = ft.OpenCNTradeContext(
                    host=self.config.host,
                    port=self.config.port,
                    is_encrypt=self.config.enable_proto_encrypt
                )
            return self._trade_cn_ctx
        
        else:
            raise ValueError(f"Unsupported market: {market}")
    
    def unlock_trade(self, password: Optional[str] = None, market: str = "HK") -> bool:
        """
        解锁交易
        
        Args:
            password: 交易密码，如果为None则使用配置中的密码
            market: 市场代码
        
        Returns:
            bool: 解锁是否成功
        """
        if password is None:
            password = self.config.trade_pwd_md5 or self.config.trade_pwd
        
        if not password:
            raise ValueError("Trade password not provided")
        
        try:
            trade_ctx = self._get_trade_context(market)
            
            # 如果是明文密码，转换为MD5
            if len(password) != 32:  # 不是MD5格式
                password = FutuConfig._generate_md5(password)
            
            ret, data = trade_ctx.unlock_trade(password_md5=password)
            if ret != ft.RET_OK:
                raise FutuTradeException(ret, data)
            
            self._unlocked = True
            self.logger.info(f"Successfully unlocked {market} trading")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unlock trading: {e}")
            if isinstance(e, FutuException):
                raise
            raise FutuTradeException(-1, str(e))
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
    
    def __repr__(self):
        status = "connected" if self._connected else "disconnected"
        unlock_status = "unlocked" if self._unlocked else "locked"
        return f"FutuClient({self.config.host}:{self.config.port}, {status}, {unlock_status})"