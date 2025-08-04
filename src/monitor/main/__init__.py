"""
Monitor main module - 股票监控应用核心模块

这个包包含了MonitorApp应用的核心组件，按功能职责拆分为以下模块：

- app_core: 应用核心和配置管理
- data_manager: 股票数据和API管理  
- ui_manager: UI组件和界面状态管理
- group_manager: 用户分组管理
- event_handler: 事件处理和用户动作
- lifecycle_manager: 应用生命周期管理
"""

from .event_handler import EventHandler
from .data import DataManager

__all__ = [
    'DataManager',
    'EventHandler'
    ]