"""
UIManager - UI组件和界面状态管理模块

负责UI组件引用管理、界面更新、表格操作和光标控制
"""

import asyncio
from typing import Optional

from textual.widgets import DataTable, Static
from base.monitor import StockData
from utils.logger import get_logger


class UIManager:
    """
    UI管理器
    负责UI组件和界面状态管理
    """
    
    def __init__(self, app_core, app_instance):
        """初始化UI管理器"""
        self.app_core = app_core
        self.app = app_instance
        self.logger = get_logger(__name__)
        
        # UI组件引用
        self.stock_table: Optional[DataTable] = None
        self.group_table: Optional[DataTable] = None
        self.orders_table: Optional[DataTable] = None
        self.trading_mode_display: Optional[Static] = None
        self.chart_panel: Optional[Static] = None
        self.ai_analysis_panel: Optional[Static] = None
        self.info_panel: Optional = None
        
        # 缓存上次的单元格值，用于检测变化
        self.last_cell_values: dict = {}
        
        # 状态栏组件引用
        self.connection_status: Optional[Static] = None
        self.market_status: Optional[Static] = None
        self.refresh_mode: Optional[Static] = None
        self.last_update: Optional[Static] = None
        
        self.logger.info("UIManager 初始化完成")
    
    async def setup_ui_references(self) -> None:
        """设置UI组件引用"""
        # 获取股票表格组件
        try:
            self.stock_table = self.app.query_one("#stock_table", DataTable)
            self.stock_table.cursor_type = 'row'
            # 默认激活股票表格光标
            self.stock_table.show_cursor = True
            self.logger.debug("股票表格引用设置成功")
        except Exception as e:
            self.logger.error(f"获取股票表格引用失败: {e}")
        
        # 获取用户分组相关组件
        try:
            self.group_table = self.app.query_one("#group_table", DataTable)
            # 配置分组表格的光标特性
            if self.group_table:
                self.group_table.cursor_type = "row"
                # 默认不显示分组表格光标
                self.group_table.show_cursor = False
            self.logger.debug("分组表格引用设置成功")
        except Exception as e:
            self.logger.error(f"获取分组表格引用失败: {e}")

        # 获取交易模式显示组件
        try:
            self.trading_mode_display = self.app.query_one("#trading_mode_display", Static)
            self.logger.debug("交易模式显示组件引用设置成功")
        except Exception as e:
            self.logger.error(f"获取交易模式显示组件引用失败: {e}")

        # 获取订单表格组件
        try:
            self.orders_table = self.app.query_one("#orders_table", DataTable)
            # 配置订单表格的光标特性
            if self.orders_table:
                self.orders_table.cursor_type = "row"
                # 默认不显示订单表格光标
                self.orders_table.show_cursor = False
            self.logger.debug("订单表格引用设置成功")
        except Exception as e:
            self.logger.error(f"获取订单表格引用失败: {e}")
        
        # 获取图表面板（可能在分析界面标签页中）
        try:
            self.chart_panel = self.app.query_one("#kline_content", Static)
            self.logger.debug("图表面板引用设置成功")
        except Exception as e:
            self.logger.debug(f"图表面板不在当前标签页中: {e}")
            self.chart_panel = None
        
        # 获取AI分析面板（可能在分析界面标签页中）
        try:
            self.ai_analysis_panel = self.app.query_one("#ai_analysis_content", Static)
            self.logger.debug("AI分析面板引用设置成功")
        except Exception as e:
            self.logger.debug(f"AI分析面板不在当前标签页中: {e}")
            self.ai_analysis_panel = None
        
        # 获取InfoPanel引用
        try:
            from monitor.widgets.line_panel import InfoPanel
            self.info_panel = self.app.query_one("#info_panel", InfoPanel)
            self.logger.info("InfoPanel引用设置成功")
        except Exception as e:
            self.logger.error(f"获取InfoPanel引用失败: {e}")
        
        # 获取状态栏组件引用
        try:
            self.connection_status = self.app.query_one("#connection_status", Static)
            self.logger.debug("连接状态组件引用设置成功")
        except Exception as e:
            self.logger.error(f"获取连接状态组件引用失败: {e}")
            
        try:
            self.market_status = self.app.query_one("#market_status", Static)
            self.logger.debug("市场状态组件引用设置成功") 
        except Exception as e:
            self.logger.error(f"获取市场状态组件引用失败: {e}")
            
        try:
            self.refresh_mode = self.app.query_one("#refresh_mode", Static)
            self.logger.debug("刷新模式组件引用设置成功")
        except Exception as e:
            self.logger.error(f"获取刷新模式组件引用失败: {e}")
            
            
        try:
            self.last_update = self.app.query_one("#last_update", Static)
            self.logger.debug("最后更新时间组件引用设置成功")
        except Exception as e:
            self.logger.error(f"获取最后更新时间组件引用失败: {e}")
        
        self.logger.info("UI组件引用设置完成")
    
    async def initialize_info(self) -> None:
        """初始化InfoPanel"""
        try:
            if self.info_panel:
                from monitor.widgets.line_panel import InfoType, InfoLevel
                # 添加启动信息
                await self.info_panel.log_info("应用程序启动成功", "系统")
                await self.info_panel.log_info(f"监控股票数量: {len(self.app_core.monitored_stocks)}", "系统")
                await self.info_panel.log_info(f"连接状态: {self.app_core.connection_status.value}", "系统")
                
                # 添加操作提示
                await self.info_panel.add_info(
                    "使用快捷键:  A-左 D-右 Q-退出",
                    InfoType.USER_ACTION,
                    InfoLevel.INFO,
                    "系统提示"
                )
                
                self.logger.info("InfoPanel 初始化完成")

            # 初始化交易模式显示
            await self.update_trading_mode_display()

            # 初始化订单表格
            await self.load_default_orders()
            await self.update_orders_table()

        except Exception as e:
            self.logger.error(f"初始化InfoPanel失败: {e}")
    
    async def load_default_stocks(self) -> None:
        """加载默认股票到表格"""
        if self.stock_table:
            # 清空现有数据
            self.stock_table.clear()
            
            # 添加股票行
            for stock_code in self.app_core.monitored_stocks:
                self.stock_table.add_row(
                    stock_code,
                    stock_code,
                    "0.00",
                    "0.00%",
                    "0",
                    "未更新",
                    key=stock_code
                )
        
        self.logger.info(f"加载默认股票列表: {self.app_core.monitored_stocks}")
        if self.info_panel:
            await self.info_panel.log_info(f"加载默认股票列表: {self.app_core.monitored_stocks}", "系统")
        
        # 初始化股票光标位置
        self.app_core.current_stock_cursor = 0
        #if self.stock_table and len(self.app_core.monitored_stocks) > 0:
        #    await self.update_stock_cursor()
        
        # 初始化表格焦点状态
        await self.update_table_focus()
    
    async def update_stock_table(self) -> None:
        """更新股票表格"""
        if not self.stock_table:
            self.logger.warning("股票表格引用为空，无法更新")
            return
        
        try:
            updated_count = 0
            # 更新表格数据
            for stock_code in self.app_core.monitored_stocks:
                stock_info = self.app_core.stock_data.get(stock_code)
                self.logger.debug(f'UI股票数据: {stock_code} {stock_info}')
                if stock_info:
                    # 格式化数据
                    price_str = f"{stock_info.current_price:.2f}"
                    change_str = f"{stock_info.change_rate:.2f}%"
                    volume_str = f"{stock_info.volume:,}"
                    time_str = stock_info.update_time.strftime("%H:%M:%S")
                    
                    self.logger.debug(f'UI更新股票数据: {stock_code} - {stock_info.name} {price_str} {change_str}')
                    
                    
                    self.stock_table.update_cell(stock_code,'name', stock_info.name)
                    self.stock_table.update_cell(stock_code,'time', time_str)

                    # 更新行数据 - 先应用闪烁效果
                    await self.update_cell_with_flash(stock_code, 'price', price_str, 
                                                    change_rate=stock_info.change_rate)
                    await self.update_cell_with_flash(stock_code, 'change', change_str, 
                                                    change_rate=stock_info.change_rate)
                    await self.update_cell_with_flash(stock_code, 'volume', volume_str)
                    
                    updated_count += 1
                else:
                    self.logger.warning(f"股票 {stock_code} 没有数据，跳过更新")
            
            # 强制刷新表格显示
            #self.stock_table.refresh()
            self.logger.info(f"股票表格更新完成，共更新 {updated_count} 只股票")
                    
        except Exception as e:
            self.logger.error(f"更新股票表格失败: {e}")
            # 尝试强制刷新以确保UI同步
            if self.stock_table:
                self.stock_table.refresh()
    
    async def update_stock_cursor(self) -> None:
        """更新股票表格的光标显示"""
        if not self.stock_table or len(self.app_core.monitored_stocks) == 0:
            return
            
        try:
            # 确保光标位置在有效范围内
            if self.app_core.current_stock_cursor < 0:
                self.app_core.current_stock_cursor = 0
            elif self.app_core.current_stock_cursor >= len(self.app_core.monitored_stocks):
                self.app_core.current_stock_cursor = len(self.app_core.monitored_stocks) - 1
            
            # 使用DataTable的原生光标移动功能
            self.stock_table.move_cursor(
                row=self.app_core.current_stock_cursor, 
                column=0,
                animate=False,
                scroll=True
            )
            
            # 更新当前选中的股票代码
            if 0 <= self.app_core.current_stock_cursor < len(self.app_core.monitored_stocks):
                self.app_core.current_stock_code = self.app_core.monitored_stocks[self.app_core.current_stock_cursor]
                
                self.logger.debug(f"股票光标移动到行 {self.app_core.current_stock_cursor}, 股票: {self.app_core.current_stock_code}")
            
        except Exception as e:
            self.logger.error(f"更新股票光标失败: {e}")
            # 降级处理：仅更新当前股票代码
            if 0 <= self.app_core.current_stock_cursor < len(self.app_core.monitored_stocks):
                self.app_core.current_stock_code = self.app_core.monitored_stocks[self.app_core.current_stock_cursor]
    
    async def update_group_cursor(self) -> None:
        """更新分组表格的光标显示 - 使用DataTable原生光标"""
        if not self.group_table or len(self.app_core.group_data) == 0:
            return
            
        try:
            # 确保光标位置在有效范围内
            if self.app_core.current_group_cursor < 0:
                self.app_core.current_group_cursor = 0
            elif self.app_core.current_group_cursor >= len(self.app_core.group_data):
                self.app_core.current_group_cursor = len(self.app_core.group_data) - 1
            
            # 使用DataTable的原生光标移动功能
            self.group_table.move_cursor(
                row=self.app_core.current_group_cursor, 
                column=0,
                animate=False,
                scroll=True
            )
            
            self.logger.debug(f"分组光标移动到行 {self.app_core.current_group_cursor}")
            
        except Exception as e:
            self.logger.error(f"更新分组光标失败: {e}")
    
    async def update_table_focus(self) -> None:
        """更新表格焦点显示，确保同一时间只有一个表格显示光标"""
        try:
            if self.app_core.active_table == "stock":
                # 激活股票表格光标，隐藏分组表格光标
                if self.stock_table:
                    self.stock_table.show_cursor = True
                    await self.update_stock_cursor()
                if self.group_table:
                    self.group_table.show_cursor = False
                    self.group_table.refresh()
                self.logger.debug("激活股票表格焦点")
            elif self.app_core.active_table == "group":
                # 激活分组表格光标，隐藏股票表格光标
                if self.group_table:
                    self.group_table.show_cursor = True
                    await self.update_group_cursor()
                if self.stock_table:
                    self.stock_table.show_cursor = False
                    self.stock_table.refresh()
                self.logger.debug("激活分组表格焦点")
        except Exception as e:
            self.logger.error(f"更新表格焦点失败: {e}")
    
    async def update_group_preview(self) -> None:
        """更新统一窗口中的分组股票信息"""
        try:
            if 0 <= self.app_core.current_group_cursor < len(self.app_core.group_data):
                current_group = self.app_core.group_data[self.app_core.current_group_cursor]
                self.logger.debug(f"当前选中分组: {current_group['name']}")
            else:
                self.logger.debug("无效的分组光标位置")

        except Exception as e:
            self.logger.error(f"更新分组信息失败: {e}")

    async def update_trading_mode_display(self) -> None:
        """更新交易模式显示"""
        try:
            if self.trading_mode_display:
                # 从 data_manager 获取当前交易模式
                data_manager = getattr(self.app_core, 'data_manager', None)
                if data_manager:
                    current_mode = data_manager.get_trading_mode()
                    is_simulation = data_manager.is_simulation_mode()

                    # 根据交易模式设置不同的显示样式
                    if is_simulation:
                        display_text = "[bold yellow]🔄 当前交易模式: 模拟交易[/bold yellow]"
                    else:
                        display_text = "[bold red]⚠️ 当前交易模式: 真实交易[/bold red]"

                    self.trading_mode_display.update(display_text)
                    self.logger.debug(f"交易模式显示已更新: {current_mode}")
                else:
                    self.trading_mode_display.update("[dim]交易模式: 未知[/dim]")
                    self.logger.warning("无法获取 data_manager，交易模式显示为未知")
        except Exception as e:
            self.logger.error(f"更新交易模式显示失败: {e}")

    async def update_orders_table(self) -> None:
        """更新订单表格"""
        if not self.orders_table:
            self.logger.warning("订单表格引用为空，无法更新")
            return

        try:
            # 清空现有数据
            self.orders_table.clear()

            # 获取订单数据（这里先使用模拟数据，实际应该从数据管理器获取）
            # TODO: 从实际的数据管理器获取订单数据
            sample_orders = [
                ("001", "HK.00700", "买入", "已成交", "100"),
                ("002", "US.AAPL", "卖出", "待成交", "50"),
                ("003", "SH.600000", "买入", "已撤销", "200"),
            ]

            # 添加订单行
            for order_id, stock_code, order_type, status, quantity in sample_orders:
                # 根据状态设置不同颜色
                if status == "已成交":
                    status_display = f"[green]{status}[/green]"
                elif status == "待成交":
                    status_display = f"[yellow]{status}[/yellow]"
                else:
                    status_display = f"[red]{status}[/red]"

                # 根据类型设置颜色
                if order_type == "买入":
                    type_display = f"[green]{order_type}[/green]"
                else:
                    type_display = f"[red]{order_type}[/red]"

                self.orders_table.add_row(
                    order_id,
                    stock_code,
                    type_display,
                    status_display,
                    quantity,
                    key=order_id
                )

            self.logger.debug(f"订单表格更新完成，共 {len(sample_orders)} 条订单")

        except Exception as e:
            self.logger.error(f"更新订单表格失败: {e}")

    async def load_default_orders(self) -> None:
        """加载默认订单到表格"""
        if self.orders_table:
            # 初始化时加载空订单表格
            self.orders_table.clear()
            self.logger.info("订单表格初始化完成")


    async def add_stock_to_table(self, stock_code: str) -> None:
        """添加股票到表格"""

        if self.stock_table:
            self.stock_table.add_row(
                stock_code,
                stock_code,
                "0.00",
                "0.00%", 
                "0",
                "未更新",
                key=stock_code
            )
    
    async def remove_stock_from_table(self, stock_code: str) -> None:
        """从表格删除股票"""
        if self.stock_table:
            try:
                self.stock_table.remove_row(stock_code)
            except Exception as e:
                self.logger.warning(f"从表格删除股票行失败: {e}")
    
    async def update_status_bar(self) -> None:
        """更新状态栏各个组件的显示内容"""
        try:
            from datetime import datetime
            from base.monitor import ConnectionStatus, MarketStatus
            
            # 更新连接状态
            if self.connection_status:
                if self.app_core.connection_status == ConnectionStatus.CONNECTED:
                    self.connection_status.update("🟢 已连接")
                elif self.app_core.connection_status == ConnectionStatus.DISCONNECTED:
                    self.connection_status.update("🟡 未连接")
                else:
                    self.connection_status.update("🔴 连接错误")
            
            # 更新市场状态
            if self.market_status:
                if self.app_core.market_status == MarketStatus.OPEN and self.app_core.open_markets:
                    open_markets_text = ",".join(self.app_core.open_markets)
                    self.market_status.update(f"📈 开盘({open_markets_text})")
                elif self.app_core.market_status == MarketStatus.OPEN:
                    self.market_status.update("📈 开盘")
                else:
                    self.market_status.update("📉 闭市")
            
            # 更新刷新模式
            if self.refresh_mode:
                mode_text = getattr(self.app_core, 'refresh_mode', '未知模式')
                self.logger.info(f"正在更新刷新模式显示: {mode_text}")
                self.refresh_mode.update(f"🔄 {mode_text}")
                self.logger.info(f"刷新模式显示更新完成: 🔄 {mode_text}")
            else:
                self.logger.warning("刷新模式组件引用为空，无法更新显示")
            
            
            # 更新最后更新时间
            if self.last_update:
                current_time = datetime.now()
                time_str = current_time.strftime("%H:%M:%S")
                self.last_update.update(f"更新: {time_str}")
            
            self.logger.debug("状态栏更新完成")
            
        except Exception as e:
            self.logger.error(f"更新状态栏失败: {e}")
    
    async def update_cell_with_flash(self, stock_code: str, column: str, value: str, 
                                   change_rate: float = None) -> None:
        """
        更新表格单元格并应用0.5秒的颜色闪烁效果
        只有当值发生变化时才显示闪烁效果
        
        Args:
            stock_code: 股票代码
            column: 列名
            value: 更新的值
            change_rate: 涨跌幅(用于price和change列的颜色判断)
        """
        if not self.stock_table:
            return
            
        try:
            # 生成单元格的唯一键
            cell_key = f"{stock_code}:{column}"
            
            # 检查值是否发生变化
            last_value = self.last_cell_values.get(cell_key)
            has_changed = last_value != value
            
            # 更新缓存值
            self.last_cell_values[cell_key] = value
            
            if has_changed:
                # 值发生变化，应用闪烁效果
                self.logger.debug(f"数据变化检测: {cell_key} '{last_value}' -> '{value}'")
                
                # 根据列类型选择闪烁颜色
                if column in ['price', 'change']:
                    # 价格和涨跌相关列：使用黄色背景突出显示
                    flash_value = f"[bold yellow on blue]{value}[/bold yellow on blue]"
                else:
                    # 其他列：使用蓝色背景
                    flash_value = f"[bold white on blue]{value}[/bold white on blue]"
                
                # 立即更新为闪烁样式
                self.stock_table.update_cell(stock_code, column, flash_value)
                
                # 创建异步任务，0.5秒后恢复正常样式
                asyncio.create_task(
                    self._restore_cell_normal_style(stock_code, column, value, change_rate)
                )
            else:
                # 值未变化，直接更新为正常样式（不闪烁）
                self.logger.debug(f"数据无变化: {cell_key} 保持值 '{value}'")
                
                # 直接应用正常样式
                if column in ['price', 'change'] and change_rate is not None:
                    if change_rate > 0:
                        # 上涨：红色
                        normal_value = f"[bold red]{value}[/bold red]"
                    elif change_rate < 0:
                        # 下跌：绿色
                        normal_value = f"[bold green]{value}[/bold green]"
                    else:
                        # 平盘：默认颜色
                        normal_value = value
                else:
                    # 其他列使用默认颜色
                    normal_value = value
                
                self.stock_table.update_cell(stock_code, column, normal_value)
            
        except Exception as e:
            self.logger.error(f"应用单元格闪烁效果失败: {e}")
            # 失败时直接更新为正常值
            self.stock_table.update_cell(stock_code, column, value)
    
    async def _restore_cell_normal_style(self, stock_code: str, column: str, value: str, 
                                       change_rate: float = None) -> None:
        """
        0.5秒后恢复单元格的正常样式
        
        Args:
            stock_code: 股票代码
            column: 列名
            value: 原始值
            change_rate: 涨跌幅(用于确定颜色)
        """
        try:
            # 等待0.5秒
            await asyncio.sleep(0.5)
            
            # 根据列类型和涨跌情况应用正常样式
            if column in ['price', 'change'] and change_rate is not None:
                if change_rate > 0:
                    # 上涨：红色
                    normal_value = f"[bold red]{value}[/bold red]"
                elif change_rate < 0:
                    # 下跌：绿色
                    normal_value = f"[bold green]{value}[/bold green]"
                else:
                    # 平盘：默认颜色
                    normal_value = value
            else:
                # 其他列使用默认颜色
                normal_value = value
            
            # 恢复正常样式
            if self.stock_table:
                self.stock_table.update_cell(stock_code, column, normal_value)
                
        except Exception as e:
            self.logger.error(f"恢复单元格正常样式失败: {e}")
    
    async def notify_analysis_panel_created(self) -> None:
        """通知lifecycle管理器AnalysisPanel已创建"""
        try:
            self.logger.info("尝试通知lifecycle管理器AnalysisPanel已创建")
            
            # 尝试多种方式获取lifecycle_manager
            lifecycle_manager = None
            
            # 方式1: 从app_core直接获取
            if hasattr(self.app_core, 'lifecycle_manager'):
                lifecycle_manager = self.app_core.lifecycle_manager
                self.logger.debug("从app_core获取到lifecycle_manager")
            
            # 方式2: 从app获取
            elif hasattr(self.app_core, 'app') and hasattr(self.app_core.app, 'lifecycle_manager'):
                lifecycle_manager = self.app_core.app.lifecycle_manager
                self.logger.debug("从app_core.app获取到lifecycle_manager")
            
            self.logger.debug(f"最终获取到lifecycle_manager: {lifecycle_manager}")
            
            if lifecycle_manager and hasattr(lifecycle_manager, 'setup_analysis_panel_welcome'):
                lifecycle_manager.setup_analysis_panel_welcome()
                self.logger.info("已成功通知lifecycle管理器AnalysisPanel创建")
            else:
                self.logger.warning(f"lifecycle_manager未找到或没有setup_analysis_panel_welcome方法，manager={lifecycle_manager}")
        except Exception as e:
            self.logger.error(f"通知AnalysisPanel创建失败: {e}")
    
    # ================== 标签页管理方法 ==================
    
    async def create_analysis_tab(self, stock_code: str) -> bool:
        """
        创建分析标签页
        
        Args:
            stock_code: 股票代码 (如 HK.00700, US.AAPL)
            
        Returns:
            bool: 创建是否成功
        """
        try:
            self.logger.info(f"开始创建分析标签页: {stock_code}")
            
            # 获取主标签页容器
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                self.logger.error("找不到主标签页容器 #main_tabs")
                return False
            
            # 生成标签页ID和标题
            tab_id = f"analysis_{stock_code.replace('.', '_')}"
            tab_title = f"📊 {stock_code}"
            
            # 检查标签页是否已存在
            existing_panes = list(main_tabs.query("TabPane"))
            for pane in existing_panes:
                if pane.id == tab_id:
                    self.logger.info(f"分析标签页 {tab_id} 已存在，激活该标签页")
                    #main_tabs.active = tab_id
                    return True
            
            # 导入分析界面组件
            try:
                from monitor.monitor_layout import AnalysisPanel
                from textual.widgets import TabPane
            except ImportError as e:
                self.logger.error(f"导入分析界面组件失败: {e}")
                return False
            
            # 创建新的分析面板
            analysis_content = AnalysisPanel(id="analysis_panel")
            analysis_content.set_app_reference(self.app)
            
            # 创建TabPane并添加到主标签页容器
            new_tab_pane = TabPane(tab_title, analysis_content, id=tab_id)
            await main_tabs.add_pane(new_tab_pane)
            
            # 激活新创建的标签页
            #main_tabs.active = tab_id
            
            # 等待一小段时间让标签页完全创建
            import asyncio
            await asyncio.sleep(0.1)
            
            # 加载股票分析数据
            analysis_data_manager = getattr(self.app_core, 'analysis_data_manager', None)
            if analysis_data_manager:
                # 异步设置当前股票并加载数据
                success = await analysis_data_manager.set_current_stock(stock_code)
                if success:
                    # 通知AnalysisPanel股票已切换
                    await analysis_content.on_stock_changed(stock_code)
                    self.logger.info(f"已为股票 {stock_code} 加载分析数据")
                else:
                    self.logger.error(f"加载股票 {stock_code} 分析数据失败")
            else:
                self.logger.error("AnalysisDataManager未初始化")
            
            # 通知分析面板已创建
            await self.notify_analysis_panel_created()
            
            self.logger.info(f"成功创建分析标签页: {tab_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建分析标签页 {stock_code} 失败: {e}")
            return False
    
    async def close_analysis_tab(self, stock_code: str = None) -> bool:
        """
        关闭分析标签页
        
        Args:
            stock_code: 要关闭的股票代码。如果为None，则关闭当前激活的分析标签页
            
        Returns:
            bool: 关闭是否成功
        """
        try:
            self.logger.info(f"开始关闭分析标签页: {stock_code or '当前激活'}")
            
            # 获取主标签页容器
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                self.logger.error("找不到主标签页容器 #main_tabs")
                return False
            
            tab_id_to_close = None
            
            if stock_code:
                # 关闭指定股票的分析标签页
                tab_id_to_close = f"analysis_{stock_code.replace('.', '_')}"
            else:
                # 关闭当前激活的分析标签页（如果是分析标签页）
                current_active = main_tabs.active
                if current_active and current_active.startswith("analysis_"):
                    tab_id_to_close = current_active
                else:
                    self.logger.warning("当前激活的标签页不是分析标签页，无法关闭")
                    return False
            
            # 检查标签页是否存在
            existing_panes = list(main_tabs.query("TabPane"))
            pane_exists = any(pane.id == tab_id_to_close for pane in existing_panes)
            
            if not pane_exists:
                self.logger.warning(f"分析标签页 {tab_id_to_close} 不存在")
                return False
            
            # 在关闭前停止相关的实时数据更新
            if stock_code:
                analysis_data_manager = getattr(self.app_core, 'analysis_data_manager', None)
                if analysis_data_manager:
                    try:
                        # 清理该股票的实时数据任务
                        await analysis_data_manager.cleanup_stock_data(stock_code)
                        self.logger.debug(f"已清理股票 {stock_code} 的分析数据")
                    except Exception as e:
                        self.logger.warning(f"清理分析数据失败: {e}")
            
            # 移除标签页
            await main_tabs.remove_pane(tab_id_to_close)
            
            # 如果关闭的是当前激活标签页，切换到主界面
            if main_tabs.active == "" or main_tabs.active == tab_id_to_close:
                main_tabs.active = "main"
            
            self.logger.info(f"成功关闭分析标签页: {tab_id_to_close}")
            return True
            
        except Exception as e:
            self.logger.error(f"关闭分析标签页失败: {e}")
            return False
    
    async def close_current_tab(self) -> bool:
        """
        关闭当前激活的标签页（仅限分析标签页）
        这个方法专门用于Cmd+W快捷键
        
        Returns:
            bool: 关闭是否成功
        """
        try:
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                return False
                
            current_active = main_tabs.active
            
            # 只允许关闭分析标签页，保护主界面标签页
            if current_active and current_active.startswith("analysis_"):
                # 从tab_id中提取股票代码
                stock_code = current_active.replace("analysis_", "").replace("_", ".")
                return await self.close_analysis_tab(stock_code)
            else:
                self.logger.debug(f"当前标签页 {current_active} 不是分析标签页，无法关闭")
                return False
                
        except Exception as e:
            self.logger.error(f"关闭当前标签页失败: {e}")
            return False
    
    def has_analysis_tab(self, stock_code: str) -> bool:
        """检查分析标签页是否存在"""
        try:
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                return False
            
            tab_id = f"analysis_{stock_code.replace('.', '_')}"
            existing_panes = list(main_tabs.query("TabPane"))
            
            for pane in existing_panes:
                if pane.id == tab_id:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查分析标签页存在性失败: {e}")
            return False