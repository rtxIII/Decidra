"""
AppCore - 应用核心和配置管理模块

负责MonitorApp的基础设施、配置管理和核心状态管理
"""

import asyncio
from typing import List, Dict, Optional, Any


from base.monitor import ConnectionStatus, MarketStatus
from utils.global_vars import get_config_manager
from utils.global_vars import get_logger


class AppCore:
    """
    应用核心管理器
    负责应用基础设施、配置管理和状态管理
    """
    
    def __init__(self, app_instance):
        """初始化应用核心"""
        self.app = app_instance
        self.logger = get_logger(__name__)
        
        # 配置管理器 - 使用全局单例
        self.config_manager = get_config_manager()
        
        # 核心状态 - 普通属性（AppCore不是Textual组件，不能使用reactive）
        self.current_stock_code: Optional[str] = None
        self.connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self.market_status: MarketStatus = MarketStatus.CLOSE
        self.refresh_mode: str = "快照模式"
        self.open_markets: List[str] = []  # 存储开市的市场名称
        self.current_group_cursor: int = 0
        self.current_stock_cursor: int = 0
        self.active_table: str = "stock"
        self.selected_group_name: Optional[str] = None
        
        # 数据存储
        self.monitored_stocks: List[str] = []
        self.stock_data: Dict[str, Any] = {}
        self.technical_indicators: Dict[str, Any] = {}
        self.stock_basicinfo_cache: Dict[str, Any] = {}
        
        # 重连控制
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        
        # 分组相关状态
        self.group_data: List[Dict[str, Any]] = []
        self.group_cursor_visible: bool = True
        
        # 持仓表相关状态
        self.position_data: List[Dict[str, Any]] = []
        self.position_cursor_visible: bool = True
        self.current_position_cursor: int = 0

        # 订单表相关状态
        self.order_data: List[Dict[str, Any]] = []
        self.order_cursor_visible: bool = True
        self.current_order_cursor: int = 0

        # 工作任务管理
        self._current_workers: set = set()
        self._worker_lock = asyncio.Lock()
        
        # 应用状态管理
        self._is_quitting = False
        
        self.logger.info("AppCore 初始化完成")
    
    async def load_configuration(self) -> None:
        """加载应用配置"""
        try:
            # 在线程池中执行同步的配置加载
            loop = asyncio.get_event_loop()
            config_data = await loop.run_in_executor(
                None, 
                lambda: self.config_manager._config_data
            )
            
            # 提取监控股票列表
            stocks_config = config_data.get('monitored_stocks', {})
            if isinstance(stocks_config, dict):
                # 从配置格式转换为列表
                monitored_stocks = []
                for key in sorted(stocks_config.keys()):
                    if key.startswith('stock_'):
                        monitored_stocks.append(stocks_config[key])
                self.monitored_stocks = monitored_stocks if monitored_stocks else [
                    'HK.00700',  # 腾讯
                    'HK.09988',  # 阿里巴巴
                ]
            else:
                self.monitored_stocks = stocks_config if isinstance(stocks_config, list) else [
                    'HK.00700',  # 腾讯
                    'HK.09988',  # 阿里巴巴
                ]
            
            self.logger.info(f"加载配置完成，监控股票: {self.monitored_stocks}")
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            # 使用默认配置
            self.monitored_stocks = ['HK.00700', 'HK.09988']
    
    async def save_config_async(self):
        """异步保存配置"""
        try:
            # 更新配置管理器的内部数据
            if hasattr(self.config_manager, '_config_data'):
                if 'monitored_stocks' not in self.config_manager._config_data:
                    self.config_manager._config_data['monitored_stocks'] = {}
                
                # 将股票列表转换为配置格式
                for i, stock in enumerate(self.monitored_stocks):
                    self.config_manager._config_data['monitored_stocks'][f'stock_{i}'] = stock
                
                # 清除旧的stock_*键
                keys_to_remove = []
                for key in self.config_manager._config_data['monitored_stocks'].keys():
                    if key.startswith('stock_') and int(key.split('_')[1]) >= len(self.monitored_stocks):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.config_manager._config_data['monitored_stocks'][key]
                
                # 在线程池中执行同步的配置保存
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, self.config_manager.save_config),
                    timeout=1.0
                )
        except Exception as e:
            self.logger.error(f"配置保存异常: {e}")
            raise
    
    def validate_stock_code(self, stock_code: str):
        """验证股票代码格式"""
        from textual.validation import ValidationResult
        import re
        
        # 基本格式验证：市场.代码
        pattern = r'^(HK|US|SH|SZ)\.[A-Z0-9]+$'
        if not re.match(pattern, stock_code.upper()):
            return ValidationResult.failure("股票代码格式错误。正确格式：HK.00700 (港股) 或 US.AAPL (美股)")
        
        return ValidationResult.success()
    
    async def update_status_display(self) -> None:
        """更新状态栏显示"""
        try:
            # 构建状态信息
            connection_status = "🟢 已连接" if self.connection_status == ConnectionStatus.CONNECTED else "🔴 未连接"
            
            # 构建市场状态信息，包含开市的市场名称
            if self.market_status == MarketStatus.OPEN and self.open_markets:
                open_markets_text = ",".join(self.open_markets)
                market_status = f"📈 开盘({open_markets_text})"
            elif self.market_status == MarketStatus.OPEN:
                market_status = "📈 开盘"
            else:
                market_status = "📉 闭市"
            refresh_info = f"🔄 {self.refresh_mode}"
            stock_count = f"📊 监控{len(self.monitored_stocks)}只股票"
            
            # 更新应用标题
            self.app.title = f"Decidra股票监控 | {connection_status} | {market_status} | {refresh_info} | {stock_count}"
            
            # 更新状态栏组件
            ui_manager = getattr(self.app, 'ui_manager', None)
            if ui_manager and hasattr(ui_manager, 'update_status_bar'):
                self.logger.info(f"调用update_status_bar更新界面显示，当前refresh_mode: {self.refresh_mode}")
                await ui_manager.update_status_bar()
                self.logger.info("update_status_bar调用完成")
            else:
                self.logger.warning("ui_manager不存在或没有update_status_bar方法")
            
        except Exception as e:
            self.logger.error(f"更新状态显示失败: {e}")