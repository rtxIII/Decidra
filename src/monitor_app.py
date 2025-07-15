#!/usr/bin/env python3
"""
Decidra股票监控应用程序 - 重构版本
基于Textual框架的终端用户界面实现

使用组合模式将原有的MonitorApp类拆分为多个功能明确的管理器模块
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any

from textual.events import Key
from textual.app import App, ComposeResult
from textual.widgets import DataTable
from textual.binding import Binding

# 项目内部导入
from modules.futu_market import FutuMarket
from utils.logger import get_logger

# 导入新的UI布局组件
from monitor.ui import MonitorLayout

# 导入重构后的管理器模块
from monitor.main import (
    AppCore, DataManager, UIManager, 
    GroupManager, EventHandler, LifecycleManager
)


class MonitorApp(App):
    """
    Decidra股票监控主应用程序 - 重构版本
    基于Textual框架实现终端界面，使用组合模式集成各功能管理器
    """
    
    # 键盘绑定定义 - 必须在类级别定义
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("h", "help", "帮助"),
        Binding("n", "add_stock", "添加股票"),
        Binding("k", "delete_stock", "删除股票"),
        Binding("r", "refresh", "刷新数据"),
        Binding("escape", "go_back", "返回"),
        Binding("tab", "switch_tab", "切换标签"),
        Binding("enter", "enter_analysis", "进入分析"),
        Binding("w", "cursor_up", "向上移动"),
        Binding("s", "cursor_down", "向下移动"),
        Binding("a", "focus_left_table", "焦点左移"),
        Binding("d", "focus_right_table", "焦点右移"),
        Binding("space", "select_group", "选择分组"),
        Binding("ctrl+c", "quit", "强制退出", priority=True),
    ]
    
    def __init__(self):
        """初始化监控应用"""
        super().__init__()
        
        # 设置日志
        self.logger = get_logger(__name__)
        
        # 创建共享的富途市场实例
        self.futu_market = FutuMarket()
        # 标记为共享实例，防止其他组件重复关闭
        self.futu_market._is_shared_instance = True
        
        # 初始化应用核心
        self.app_core = AppCore(self)
        
        # 初始化各个管理器
        self.data_manager = DataManager(self.app_core, self.futu_market)
        self.ui_manager = UIManager(self.app_core, self)
        self.group_manager = GroupManager(self.app_core, self.futu_market)
        self.event_handler = EventHandler(self.app_core, self)
        self.lifecycle_manager = LifecycleManager(self.app_core, self)
        
        # 将管理器引用添加到app_core，以便各管理器之间可以相互访问
        self.app_core.data_manager = self.data_manager
        self.app_core.ui_manager = self.ui_manager
        self.app_core.group_manager = self.group_manager
        self.app_core.event_handler = self.event_handler
        self.app_core.lifecycle_manager = self.lifecycle_manager
        
        self.logger.info("MonitorApp 初始化完成")
    
    def compose(self) -> ComposeResult:
        """构建用户界面 - 使用新的UI布局组件"""
        # 使用新的MonitorLayout组件，包含完整的布局结构
        yield MonitorLayout(id="monitor_layout")
    
    def on_key(self, event: Key) -> None:
        """处理按键事件 - 委托给事件处理器"""
        self.event_handler.on_key(event)
    
    async def on_mount(self) -> None:
        """应用启动时的初始化 - 委托给生命周期管理器"""
        await self.lifecycle_manager.on_mount()
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件 - 委托给事件处理器"""
        await self.event_handler.on_data_table_row_selected(event)
    
    # 动作方法 - 委托给事件处理器
    async def action_add_stock(self) -> None:
        """添加股票动作"""
        await self.event_handler.action_add_stock()
    
    async def action_delete_stock(self) -> None:
        """删除股票动作"""
        await self.event_handler.action_delete_stock()
    
    async def action_refresh(self) -> None:
        """手动刷新动作"""
        await self.event_handler.action_refresh()
    
    async def action_help(self) -> None:
        """显示帮助动作"""
        await self.event_handler.action_help()
    
    async def action_go_back(self) -> None:
        """返回主界面动作"""
        await self.event_handler.action_go_back()
    
    async def action_switch_tab(self) -> None:
        """切换标签页动作"""
        await self.event_handler.action_switch_tab()
    
    async def action_cursor_up(self) -> None:
        """光标向上移动"""
        await self.event_handler.action_cursor_up()
    
    async def action_cursor_down(self) -> None:
        """光标向下移动"""
        await self.event_handler.action_cursor_down()
    
    async def action_select_group(self) -> None:
        """选择当前光标所在的分组"""
        await self.event_handler.action_select_group()
    
    async def action_focus_left_table(self) -> None:
        """左移焦点到股票表格"""
        await self.event_handler.action_focus_left_table()
    
    async def action_focus_right_table(self) -> None:
        """右移焦点到分组表格"""
        await self.event_handler.action_focus_right_table()
    
    async def action_enter_analysis(self) -> None:
        """进入分析界面动作"""
        await self.event_handler.action_enter_analysis()
    
    async def action_quit(self) -> None:
        """退出应用动作 - 委托给生命周期管理器"""
        await self.lifecycle_manager.action_quit()
    
    # 便捷访问属性，保持向后兼容性
    @property
    def current_stock_code(self) -> Optional[str]:
        """当前选中的股票代码"""
        return self.app_core.current_stock_code
    
    @current_stock_code.setter
    def current_stock_code(self, value: Optional[str]):
        """设置当前选中的股票代码"""
        self.app_core.current_stock_code = value
    
    @property
    def connection_status(self):
        """连接状态"""
        return self.app_core.connection_status
    
    @connection_status.setter
    def connection_status(self, value):
        """设置连接状态"""
        self.app_core.connection_status = value
    
    @property
    def market_status(self):
        """市场状态"""
        return self.app_core.market_status
    
    @market_status.setter
    def market_status(self, value):
        """设置市场状态"""
        self.app_core.market_status = value
    
    @property
    def monitored_stocks(self) -> List[str]:
        """监控股票列表"""
        return self.app_core.monitored_stocks
    
    @monitored_stocks.setter
    def monitored_stocks(self, value: List[str]):
        """设置监控股票列表"""
        self.app_core.monitored_stocks = value
    
    @property
    def stock_data(self) -> Dict[str, Any]:
        """股票数据"""
        return self.app_core.stock_data
    
    # 为了保持兼容性而保留的引用属性
    @property
    def stock_table(self) -> Optional[DataTable]:
        """股票表格引用"""
        return self.ui_manager.stock_table if self.ui_manager else None
    
    @property
    def group_table(self) -> Optional[DataTable]:
        """分组表格引用"""
        return self.ui_manager.group_table if self.ui_manager else None
    
    @property
    def info_panel(self):
        """信息面板引用"""
        return self.ui_manager.info_panel if self.ui_manager else None


def main():
    """主函数"""
    app = MonitorApp()
    app.run()


if __name__ == "__main__":
    main()