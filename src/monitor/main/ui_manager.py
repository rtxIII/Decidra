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
        self.group_stocks_content: Optional[Static] = None
        self.chart_panel: Optional[Static] = None
        self.ai_analysis_panel: Optional[Static] = None
        self.info_panel: Optional = None
        
        self.logger.info("UIManager 初始化完成")
    
    async def setup_ui_references(self) -> None:
        """设置UI组件引用"""
        try:
            # 获取股票表格组件
            self.stock_table = self.app.query_one("#stock_table", DataTable)
            self.stock_table.cursor_type = 'row'
            self.stock_table.show_cursor = True
            
            # 获取用户分组相关组件
            self.group_table = self.app.query_one("#group_table", DataTable)
            self.group_stocks_content = self.app.query_one("#group_stocks_content", Static)
            
            # 配置分组表格的光标特性
            if self.group_table:
                self.group_table.cursor_type = "row"
                self.group_table.show_cursor = True
            
            # 获取图表面板
            self.chart_panel = self.app.query_one("#kline_chart", Static)
            
            # 获取AI分析面板
            self.ai_analysis_panel = self.app.query_one("#ai_content", Static)
            
            # 获取InfoPanel引用
            from monitor.widgets.line_panel import InfoPanel
            self.info_panel = self.app.query_one("#info_panel", InfoPanel)
            
            self.logger.info("UI组件引用设置完成")
            
        except Exception as e:
            self.logger.error(f"设置UI组件引用失败: {e}")
    
    async def initialize_info_panel(self) -> None:
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
                    "使用快捷键: A-添加股票 D-删除股票 R-刷新数据 Q-退出",
                    InfoType.USER_ACTION,
                    InfoLevel.INFO,
                    "系统提示"
                )
                
                self.logger.info("InfoPanel 初始化完成")
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
                    
                    # 更新行数据
                    self.stock_table.update_cell(stock_code, 'name', stock_info.name)
                    self.stock_table.update_cell(stock_code, 'price', price_str)
                    self.stock_table.update_cell(stock_code, 'change', change_str)
                    self.stock_table.update_cell(stock_code, 'volume', volume_str)
                    self.stock_table.update_cell(stock_code, 'time', time_str)
                    
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
                if self.group_stocks_content:
                    # 统一窗口中的信息显示
                    preview_text = f"[bold cyan]{current_group['name']}[/bold cyan] [dim]({current_group['stock_count']}只股票)[/dim]\n\n"
                    
                    # 显示股票列表
                    stock_list = current_group.get('stock_list', [])
                    if stock_list and len(stock_list) > 0:
                        # 使用列表格式显示股票
                        for stock in stock_list[:12]:  # 显示前12只股票以充分利用空间
                            if isinstance(stock, dict):
                                stock_code = stock.get('code', 'Unknown')
                                stock_name = stock.get('name', '')
                                if stock_name:
                                    preview_text += f"• {stock_code} {stock_name[:8]}\n"
                                else:
                                    preview_text += f"• {stock_code}\n"
                            else:
                                preview_text += f"• {stock}\n"
                        
                        if len(stock_list) > 12:
                            preview_text += f"\n[dim]...还有 {len(stock_list) - 12} 只股票[/dim]\n"
                    else:
                        preview_text += "[dim]该分组暂无股票[/dim]\n"
                    
                    preview_text += "\n[yellow]Space键选择此分组作为主监控列表[/yellow]"
                    
                    self.group_stocks_content.update(preview_text)
                    self.logger.debug(f"已更新分组信息: {current_group['name']}")
            else:
                # 无效的光标位置
                if self.group_stocks_content:
                    self.group_stocks_content.update("[dim]使用 k/l 键选择分组\n使用 Space 键切换监控列表[/dim]")
                    
        except Exception as e:
            self.logger.error(f"更新分组信息失败: {e}")
            if self.group_stocks_content:
                self.group_stocks_content.update("[red]信息加载失败[/red]")
    
    async def update_analysis_interface(self) -> None:
        """更新分析界面内容"""
        if not self.app_core.current_stock_code:
            return
            
        try:
            # 更新图表面板
            if self.chart_panel:
                chart_text = f"""[bold blue]{self.app_core.current_stock_code} K线图表[/bold blue]

[dim]图表功能：
• D: 切换到日线图
• W: 切换到周线图  
• M: 切换到月线图
• ←→: 调整时间范围
• ESC: 返回主界面[/dim]

[yellow]正在加载图表数据...[/yellow]"""
                self.chart_panel.update(chart_text)
            
            # 更新AI分析面板
            if self.ai_analysis_panel:
                ai_text = f"""[bold green]{self.app_core.current_stock_code} AI智能分析[/bold green]

[dim]分析维度：
• 技术指标分析 (MA, RSI, MACD)
• 买卖信号推荐
• 支撑位和阻力位
• 风险评估等级[/dim]

[yellow]正在生成AI分析报告...[/yellow]"""
                self.ai_analysis_panel.update(ai_text)
            
        except Exception as e:
            self.logger.error(f"更新分析界面失败: {e}")
    
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