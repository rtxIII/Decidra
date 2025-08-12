"""
Monitor UI Layout Module
基于 Textual 框架的监控界面布局组件
参考: https://textual.textualize.io/guide/layout/
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Grid, Horizontal
from textual.widgets import (
    Static, DataTable, Label, 
    TabbedContent, TabPane, ProgressBar
)
from textual.reactive import reactive
from textual.binding import Binding
from typing import List, Dict, Optional
import asyncio
from utils.logger import get_logger

STOCK_COLUMNS = {
            "code": {"label": "代码", "width": 10},
            "name": {"label": "名称", "width": 10},
            "price": {"label": "价格", "width": 10},
            "change": {"label": "涨跌", "width": 10},
            "volume": {"label": "成交量", "width": 10},
            "time": {"label": "时间", "width": 10},
        }


class StockListPanel(Container):
    """股票列表面板 - 左侧70%区域"""
    
    DEFAULT_CSS = """
    StockListPanel {
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
    }
    
    StockListPanel DataTable {
        height: 1fr;
        
        padding: 1;
    }
    
    StockListPanel DataTable > .datatable--header {
        
        height: 3;
        padding: 1;
    }
    
    StockListPanel DataTable > .datatable--body {
        
        padding: 1;
    }
    
    StockListPanel DataTable > .datatable--row {
        height: 3;
        padding: 0 1;
    }
    
    StockListPanel .button-bar {
        height: 3;
        dock: bottom;
        background: $surface;
        text-align: center;
        
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "监控股票列表"
        
    def compose(self) -> ComposeResult:
        """组合股票列表组件"""
        # 股票数据表格
        stock_table = DataTable(
            show_cursor=True,
            zebra_stripes=True,
            cursor_type="row",
            show_header=True,
            show_row_labels=False,
            id="stock_table"
        )
        # 添加表格列
        for column_key, column_data in STOCK_COLUMNS.items():
            column_width = column_data["width"]
            column_label = column_data["label"]
            stock_table.add_column(column_label, key=column_key, width=column_width)
        yield stock_table
        
        # 快捷键提示区域
        with Container(classes="button-bar"):
            yield Static(
                "[bold green]A[/bold green] 添加股票  [bold red]D[/bold red] 删除股票  [bold blue]R[/bold blue] 刷新数据  [bold yellow]Space[/bold yellow] 选择分组",
                id="hotkey_hints"
            )


class UserGroupPanel(Container):
    """用户分组面板 - 右侧30%区域（完全合并的单一窗口）"""
    
    DEFAULT_CSS = """
    UserGroupPanel {
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 1;
        layout: vertical;
    }
    
    UserGroupPanel .group-info-combined {
        height: 50%;
        background: $surface;
        overflow-y: auto;
        padding: 1;
        margin-bottom: 1;
    }
    
    UserGroupPanel .group-info-combined DataTable {
        height: 40%;
        margin-bottom: 1;
    }
    
    UserGroupPanel .group-info-combined .info-content {
        height: 60%;
        padding: 1;
    }
    
    UserGroupPanel .position-info {
        height: 50%;
        background: $surface;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 1;
    }
    
    UserGroupPanel DataTable {
        height: 1fr;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "分组与股票管理"
        
    def compose(self) -> ComposeResult:
        """组合完全统一的单一窗口"""
        # 合并的分组表格和信息显示区域（50%空间）
        with Container(classes="group-info-combined"):
            # 分组表格
            group_table = DataTable(
                show_cursor=True,
                zebra_stripes=True,
                cursor_type="row",
                show_header=True,
                show_row_labels=False,
                id="group_table"
            )
            group_table.add_columns("分组名称", "股票数量", "类型")
            yield group_table
            
            # 信息显示内容
            with Container(classes="info-content"):
                yield Static(
                    "[dim]使用 k/l 键选择分组\n使用 Space 键切换监控列表\n\n选择分组后将显示包含的股票详情[/dim]",
                    id="group_stocks_content"
                )
        
        # 持仓信息区域（30%空间，位于最下面）
        with Container(classes="position-info"):
            yield Static("持仓订单信息", id="position_title")
            yield Static(
                "[bold white]持仓情况:[/bold white]\n" +
                "数量: --\n" +
                "成本价: --\n" +
                "盈亏: --\n\n" +
                "[bold white]挂单情况:[/bold white]\n" +
                "无挂单",
                id="position_content"
            )




class AnalysisPanel(Container):
    """分析面板 - 严格按照MVP设计的完整实现"""
    
    BINDINGS = [
        Binding("z", "return_to_main", "返回主界面", priority=True),
    ]
    
    def __init__(self, **kwargs):
        """初始化分析面板"""
        super().__init__(**kwargs)
        self._app_ref = None
        self._basic_info_widget = None
        self._tabbed_content = None
        self.logger = get_logger(__name__)
        
    def set_app_reference(self, app):
        """设置应用引用以访问数据管理器"""
        self._app_ref = app
        
    def get_analysis_data_manager(self):
        """获取分析数据管理器"""
        if self._app_ref and hasattr(self._app_ref, 'app_core'):
            return getattr(self._app_ref.app_core, 'analysis_data_manager', None)
        return None
        
    def format_basic_info(self, analysis_data=None) -> str:
        """格式化基础信息显示文本"""
        if not analysis_data:
            return "等待股票数据加载..."
            
        basic_info = analysis_data.basic_info
        realtime_quote = analysis_data.realtime_quote
        
        # 提取基础信息
        stock_code = basic_info.get('code', '未知')
        stock_name = basic_info.get('name', '未知')
        last_price = basic_info.get('last_price', '未知')
        prev_close_price = basic_info.get('prev_close_price', '未知')
        volume     = basic_info.get('volume', '未知')
        turnover     = basic_info.get('turnover', '未知')
        turnover_rate     = basic_info.get('turnover_rate', '未知')
        amplitude     = basic_info.get('amplitude', '未知')
        listing_date  = basic_info.get('listing_date', '未知')

        
        # 提取实时数据用于计算市值等
        current_price = realtime_quote.get('cur_price', 0)
        volume = realtime_quote.get('volume', 0)
        
        # 判断市场
        market_map = {
            'HK': '港交所',
            'US': '纳斯达克/纽交所', 
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所'
        }
        market = stock_code.split('.')[0] if '.' in stock_code else 'Unknown'
        market_name = market_map.get(market, '未知市场')
        
        # 格式化显示文本
        info_text = (
            f"股票代码: {stock_code}    "
            f"名称: {stock_name}    "
            f"最新价格: {last_price}    "
            f"昨收盘价格: {prev_close_price}    "
            f"成交金额: {turnover}    "
            f"换手率: {turnover_rate}   "
            f"振幅: {amplitude}    "
        )
        
        if current_price > 0:
            market_cap = current_price * volume if volume > 0 else 0
            if market_cap > 100000000:  # 大于1亿
                market_cap_text = f"{market_cap/100000000:.1f}亿"
            else:
                market_cap_text = f"{market_cap/10000:.1f}万" if market_cap > 10000 else f"{market_cap:.0f}"
            info_text += f"当前价: {current_price:.2f}    市值估算: {market_cap_text}    "
            
        if listing_date and listing_date != '未知':
            info_text += f"上市日期: {listing_date}    "
            
        info_text += f"更新时间: {analysis_data.last_update.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return info_text
        
    async def update_basic_info(self):
        """更新基础信息显示"""
        try:
            data_manager = self.get_analysis_data_manager()
            if not data_manager:
                if self._basic_info_widget:
                    self._basic_info_widget.update("等待数据管理器初始化...")
                return
                
            analysis_data = data_manager.get_current_analysis_data()
            formatted_info = self.format_basic_info(analysis_data)
            
            if self._basic_info_widget:
                self._basic_info_widget.update(formatted_info)
                
        except Exception as e:
            if self._basic_info_widget:
                self._basic_info_widget.update(f"数据加载错误: {str(e)}")
    
    async def on_stock_changed(self, stock_code: str):
        """处理股票切换事件"""
        try:
            data_manager = self.get_analysis_data_manager()
            if not data_manager:
                return
                
            # 设置当前分析的股票并加载数据
            success = await data_manager.set_current_stock(stock_code)
            if success:
                # 更新基础信息显示
                await self.update_basic_info()
            else:
                if self._basic_info_widget:
                    self._basic_info_widget.update(f"加载股票 {stock_code} 数据失败")
                    
        except Exception as e:
            if self._basic_info_widget:
                self._basic_info_widget.update(f"股票切换错误: {str(e)}")
    
    async def initialize_info_panel(self) -> None:
        """初始化 InfoPanel 并显示欢迎信息"""
        try:
            # 等待一小段时间确保InfoPanel完全初始化
            await asyncio.sleep(0.1)
            
            # 查找 InfoPanel
            info_panel = self.query_one("#ai_info_panel", expect_type=None)
            if info_panel and hasattr(info_panel, 'log_info'):
                await info_panel.log_info("欢迎使用股票分析功能！", "系统")
                await info_panel.log_info("您可以选择股票进行深度分析", "系统")
                self.logger.info("AnalysisPanel InfoPanel 欢迎信息已显示")
            else:
                self.logger.warning(f"未找到InfoPanel或InfoPanel不支持log_info方法: {info_panel}")
                
        except Exception as e:
            self.logger.error(f"初始化AnalysisPanel InfoPanel失败: {e}")
    
    async def on_mount(self) -> None:
        """组件挂载时初始化"""
        #self.logger.debug(f"DEBUG: AnalysisPanel on_mount 开始，组件ID: {self.id}")
        
        # 尝试初始加载数据
        await self.update_basic_info()
        
        # 获取 TabbedContent 组件引用
        try:
            self._tabbed_content = self.query_one("#realtime_tabs", TabbedContent)
            #self.logger.debug(f"DEBUG: 成功找到 TabbedContent: {self._tabbed_content}")
        except Exception as e:
            #self.logger.debug(f"DEBUG: 未找到 TabbedContent: {e}")
            self._tabbed_content = None
        
        # 初始化 InfoPanel 并显示欢迎信息
        await self.initialize_info_panel()
            
        # 设置焦点，确保能接收键盘事件
        self.can_focus = True
        #self.logger.debug(f"DEBUG: AnalysisPanel 设置 can_focus=True")
        
        # 立即获取焦点
        self.focus()
        #self.logger.debug(f"DEBUG: AnalysisPanel 调用 focus()，当前焦点状态: {self.has_focus}")
        
        # 延迟再次确认焦点状态
        def ensure_focus():
            #self.logger.debug(f"DEBUG: 延迟检查焦点状态: {self.has_focus}")
            if not self.has_focus:
                self.logger.debug("DEBUG: 焦点丢失，重新获取焦点")
                self.focus()
                #self.logger.debug(f"DEBUG: 重新获取焦点后状态: {self.has_focus}")
            else:
                self.logger.debug("DEBUG: 焦点状态正常")
        
        self.call_after_refresh(ensure_focus)
        self.logger.debug("DEBUG: AnalysisPanel 设置焦点完成")
    
    def _ensure_focus_after_switch(self) -> None:
        """标签页切换后确保获得焦点"""
        def ensure_focus():
            try:
                # 找到当前活跃标签页中的AnalysisPanel
                main_tabs = self.app.query_one("#main_tabs", TabbedContent)
                current_tab_id = main_tabs.active
                #self.logger.debug(f"DEBUG: 焦点恢复 - 当前活跃标签页: {current_tab_id}")
                
                # 如果当前是主界面标签页，不需要设置AnalysisPanel焦点
                if current_tab_id == "main":
                    self.logger.debug("DEBUG: 当前在主界面，无需设置AnalysisPanel焦点")
                    return
                
                # 只有分析标签页才需要设置AnalysisPanel焦点
                if current_tab_id.startswith('analysis_'):
                    # 查找当前标签页中的AnalysisPanel
                    try:
                        # 直接查找当前标签页的AnalysisPanel
                        current_panel = main_tabs.query_one(f"#{current_tab_id} AnalysisPanel")
                        current_panel.focus()
                        #self.logger.debug(f"DEBUG: 为当前标签页的AnalysisPanel设置焦点，焦点状态: {current_panel.has_focus}")
                    except Exception as e:
                        # 备用方案：找到所有AnalysisPanel并设置第一个
                        analysis_panels = self.app.query("AnalysisPanel")
                        if analysis_panels:
                            analysis_panels[0].focus()
                            #self.logger.debug(f"DEBUG: 备用方案设置焦点成功")
                        
            except Exception as e:
                pass
                #self.logger.debug(f"DEBUG: 切换后设置焦点失败: {e}")
        
        # 延迟执行以确保标签页切换完成
        self.call_after_refresh(ensure_focus)
    
    def on_click(self, event) -> None:
        """处理点击事件，确保获得焦点"""
        #self.logger.debug(f"DEBUG: AnalysisPanel 被点击，当前焦点状态: {self.has_focus}")
        self.focus()
        #self.logger.debug(f"DEBUG: 点击后重新设置焦点，焦点状态: {self.has_focus}")
    
    def on_key(self, event) -> None:
        """处理所有键盘事件"""
        # 只有当前获得焦点的AnalysisPanel才处理事件，防止重复执行
        if not self.has_focus:
            return
            
        #self.logger.debug(f"DEBUG: AnalysisPanel 收到按键事件: {event.key}, 焦点状态: {self.has_focus}")
        if event.key == "z":
            #self.logger.debug("DEBUG: z键被按下，返回主界面")
            self.action_return_to_main()
            event.prevent_default()
        else:
            pass
            #self.logger.debug(f"DEBUG: AnalysisPanel 未处理的按键: {event.key}")
    
    def action_return_to_main(self) -> None:
        """返回主界面（z键）"""
        try:
            # 获取主标签页容器
            main_tabs = self.app.query_one("#main_tabs", TabbedContent)
            main_tabs.active = "main"
            self.logger.debug("DEBUG: 已返回主界面")
        except Exception as e:
            pass
            #self.logger.debug(f"DEBUG: 返回主界面失败: {e}")
    
    
    DEFAULT_CSS = """
    AnalysisPanel {
        height: 1fr;
        layout: vertical;
        overflow-y: auto;
    }
    
    AnalysisPanel .basic-info-area {
        height: 15%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        margin-bottom: 0;
    }
    
    AnalysisPanel .quote-area {
        height: 15%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        margin-bottom: 0;
    }
    
    AnalysisPanel .three-column-area {
        height: 40%;
        layout: horizontal;
        margin-bottom: 0;
    }
    
    AnalysisPanel .order-book-column {
        width: 24%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        margin-right: 0;
    }
    
    AnalysisPanel .realtime-data-column {
        width: 37%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        margin-right: 0;
    }
    
    AnalysisPanel .money-flow-column {
        width: 39%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        layout: vertical;
    }
    
    AnalysisPanel .ai-interaction-area {
        height: 30%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 0;
        layout: vertical;
    }
    
    AnalysisPanel .realtime-data-column TabbedContent {
        height: 1fr;
    }
    
    AnalysisPanel .realtime-data-column TabPane {
        padding: 0;
    }
    
    /* AI交互区域样式 - 使用InfoPanel */
    AnalysisPanel .ai-interaction-area InfoPanel {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
        background: $surface;
        border: solid $secondary;
        padding: 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        """严格按照MVP设计组合分析面板的完整布局"""
        # 1. 基础信息区域
        with Container(classes="basic-info-area"):
            basic_info_widget = Static(
                "等待股票数据加载...",
                id="basic_info_content"
            )
            self._basic_info_widget = basic_info_widget
            yield basic_info_widget
        
        # 2. 报价区域  
        with Container(classes="quote-area"):
            yield Static(
                "最新价: 12.85 ↑    涨跌幅: +2.35%    涨跌额: +0.29    开盘: 12.58    最高: 12.96    最低: 12.51    成交量: 1.2亿手    成交额: 153.7亿    换手率: 0.62%    振幅: 3.58%",
                id="quote_info_content"
            )
        
        # 3. 三栏布局区域
        with Container(classes="three-column-area"):
            # 3.1 摆盘区域（25%宽度）
            with Container(classes="order-book-column"):
                yield Static("摆盘区域", id="order_book_title")
                yield Static(
                    "[bold red]卖五: 12.89  1250手[/bold red]\n" +
                    "[bold red]卖四: 12.88  2100手[/bold red]\n" +
                    "[bold red]卖三: 12.87  3400手[/bold red]\n" +
                    "[bold red]卖二: 12.86  4200手[/bold red]\n" +
                    "[bold red]卖一: 12.85  5800手[/bold red]\n" +
                    "──────────────────\n" +
                    "[bold green]买一: 12.84  6200手[/bold green]\n" +
                    "[bold green]买二: 12.83  4900手[/bold green]\n" +
                    "[bold green]买三: 12.82  3100手[/bold green]\n" +
                    "[bold green]买四: 12.81  2800手[/bold green]\n" +
                    "[bold green]买五: 12.80  1900手[/bold green]\n\n" +
                    "📈 委比: +8.2%\n" +
                    "📊 委差: +1.8万手",
                    id="order_book_content"
                )
            
            # 3.2 实时数据区域（37%宽度）
            with Container(classes="realtime-data-column"):
                yield Static("实时数据区域", id="realtime_data_title")
                    # K线数据标签页
                yield Static(
                            "[bold blue]K线数据[/bold blue]\n" +
                            "开盘:12.58  最高:12.96\n" +
                            "最低:12.51  收盘:12.85\n" +
                            "成交:1.2亿  涨跌:+2.35%",
                            id="kline_content"
                        )
                    
                    # 逐笔数据标签页
                yield Static(
                            "[bold yellow]逐笔数据[/bold yellow]\n" +
                            "14:32:15  12.85↑125  89手\n" +
                            "14:32:18  12.84↓89   45手\n" +
                            "14:32:20  12.85↑201  156手\n" +
                            "14:32:22  12.86↑67   67手",
                            id="tick_content"
                        )
                    
                    # 经纪队列数据标签页
                yield Static(
                            "[bold cyan]经纪队列[/bold cyan]\n" +
                            "中信证券 买入排队 1.2万手\n" +
                            "平安证券 卖出排队 8.9千手\n" +
                            "招商证券 买入排队 6.8千手",
                            id="broker_content"
                        )
            
            # 3.3 资金流向区域（38%宽度） 
            with Container(classes="money-flow-column"):
                yield Static("资金流向/分布区域", id="money_flow_title")
                yield Static(
                    "主力净流入: +2.3亿 ↑    超大单: +1.8亿(+3.2%)    大单: +0.5亿(+0.9%)    中单: -1.2亿(-2.1%)    小单: -1.1亿(-1.9%)    │    大单占比: 45.2%    中单: 32.1%    小单: 22.7%    │    北向资金: +0.85亿     融资余额: 25.6亿(-0.3%)     融券余额: 1.2亿(+2.1%)     资金净流入排名: 17/4832     活跃度: 中等     │    换手率排名: 456/4832    热度: ★★★☆☆",
                    id="money_flow_content_column"
                )
        
        # 4. AI交互区域 - 使用InfoPanel替代Container
        with Container(classes="ai-interaction-area"):
            # 导入InfoPanel并使用
            from monitor.widgets.line_panel import InfoPanel
            yield InfoPanel(title="AI智能分析", id="ai_info_panel")


class MainLayoutTab(Container):
    """主界面标签页布局"""
    
    DEFAULT_CSS = """
    MainLayoutTab {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 7fr 3fr;
        grid-rows: 3fr 2fr;
        grid-gutter: 1;
        height: 1fr;
    }
    
    MainLayoutTab #stock_list_panel {
        column-span: 1;
        row-span: 1;
    }
    
    MainLayoutTab #user_group_panel {
        column-span: 1;
        row-span: 2;
    }
    
    MainLayoutTab #info_panel {
        column-span: 1;
        row-span: 1;
    }
    """
    BINDINGS = []
    
    def compose(self) -> ComposeResult:
        """组合主界面布局"""
        yield StockListPanel(id="stock_list_panel")
        yield UserGroupPanel(id="user_group_panel")
        # 导入InfoPanel并添加到布局中
        from monitor.widgets.line_panel import InfoPanel
        yield InfoPanel(title="系统信息", id="info_panel")


class AnalysisLayoutTab(Container):
    """分析界面标签页布局"""
    
    def __init__(self, **kwargs):
        """初始化分析界面标签页"""
        super().__init__(**kwargs)
        self._app_ref = None
        self.analysis_panel = None
        self.logger = get_logger(__name__)
        
    def set_app_reference(self, app):
        """设置应用引用"""
        self._app_ref = app
        if self.analysis_panel:
            self.analysis_panel.set_app_reference(app)
    
    def on_key(self, event) -> None:
        """将键盘事件传递给AnalysisPanel"""
        #self.logger.debug(f"DEBUG: AnalysisLayoutTab 收到按键事件: {event.key}")
        if self.analysis_panel and hasattr(self.analysis_panel, 'on_key'):
            self.analysis_panel.on_key(event)
    
    DEFAULT_CSS = """
    AnalysisLayoutTab {
        layout: vertical;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合分析界面布局"""
        self.analysis_panel = AnalysisPanel(id="analysis_panel")
        if self._app_ref:
            self.analysis_panel.set_app_reference(self._app_ref)
        yield self.analysis_panel


class StatusBar(Container):
    """状态栏组件"""
    
    DEFAULT_CSS = """
    StatusBar {
        height: 3;
        background: $surface;
        color: black;
        layout: horizontal;
        border: solid $accent;
        margin-bottom: 0;
    }
    
    StatusBar .status-item {
        width: 1fr;
        margin: 0 1;
        padding: 0 1;
        content-align: center middle;
        background: $accent;
        color: black;
    }
    
    StatusBar .connection-status {
        background: $success;
        color: black;
        padding: 0 1;
    }
    
    StatusBar .market-status {
        background: $warning;
        color: black;
        padding: 0 1;
    }
    
    StatusBar .refresh-mode {
        background: $primary;
        color: black;
        padding: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合状态栏"""
        yield Static("🟢 已连接", classes="status-item connection-status", id="connection_status")
        yield Static("📈 开盘", classes="status-item market-status", id="market_status")
        yield Static("🔄 实时模式", classes="status-item refresh-mode", id="refresh_mode")
        yield Static("更新: 刚刚", classes="status-item", id="last_update")


class MonitorLayout(Container):
    """监控界面完整布局"""
    
    def __init__(self, **kwargs):
        """初始化监控界面布局"""
        super().__init__(**kwargs)
        self._app_ref = None
        self.logger = get_logger(__name__)
    
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("r", "refresh", "刷新", priority=True),
        Binding("h", "help", "帮助"),
        Binding("a", "add_stock", "添加股票"),
        Binding("d", "delete_stock", "删除股票"),
        Binding("escape", "go_back", "返回"),
        Binding("tab", "switch_tab", "切换标签"),
        Binding("enter", "enter_analysis", "进入分析"),
        Binding("ctrl+c", "quit", "强制退出", priority=True),
    ]
    
    DEFAULT_CSS = """
    MonitorLayout {
        layout: vertical;
    }
    
    MonitorLayout StatusBar {
        dock: top;
        height: 3;
    }
    
    MonitorLayout TabbedContent {
        height: 1fr;
        margin: 1 0;
    }
    
    MonitorLayout TabPane {
        padding: 1;
    }
    
    /* 全局样式 */
    .green { color: $success; }
    .red { color: $error; }
    .yellow { color: $warning; }
    .blue { color: $primary; }
    .cyan { color: $accent; }
    
    /* 表格样式 */
    DataTable > .datatable--header {
        background: $accent;
        color: $text;
    }
    
    DataTable > .datatable--cursor {
        background: $primary;
        color: $text;
    }
    
    /* 按钮样式 */
    Button.-success {
        background: $success;
        color: $text;
    }
    
    Button.-error {
        background: $error;
        color: $text;
    }
    
    Button.-primary {
        background: $primary;
        color: $text;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合完整监控界面"""
        # 状态栏保留，但去除Header和Footer让界面更紧凑
        yield StatusBar(id="status_bar")
        
        # 主体标签页内容
        with TabbedContent(initial="main", id="main_tabs"):
            # 主界面标签页
            with TabPane("主界面", id="main"):
                yield MainLayoutTab(id="main_layout")


class ResponsiveLayout(Container):
    """响应式布局容器 - 支持不同终端尺寸"""
    
    # 响应式断点
    size_small = reactive(False)
    size_medium = reactive(False)
    size_large = reactive(True)
    
    DEFAULT_CSS = """
    ResponsiveLayout {
        layout: vertical;
    }
    
    /* 小屏幕布局 */
    ResponsiveLayout.-small MainLayoutTab {
        layout: vertical;
        grid-columns: 1fr;
    }
    
    ResponsiveLayout.-small StockListPanel {
        height: 60%;
    }
    
    ResponsiveLayout.-small UserGroupPanel {
        height: 25%;
    }
    
    ResponsiveLayout.-small InfoPanel {
        height: 15%;
    }
    
    /* 中等屏幕布局 */
    ResponsiveLayout.-medium MainLayoutTab {
        grid-columns: 6.5fr 3.5fr;
    }
    
    /* 大屏幕布局 (默认) */
    ResponsiveLayout.-large MainLayoutTab {
        grid-columns: 7fr 3fr;
    }
    """
    
    def watch_size(self) -> None:
        """监听窗口大小变化"""
        console_size = self.app.console.size
        width = console_size.width
        
        # 根据宽度设置响应式类
        if width < 80:
            self.set_class(True, "-small")
            self.set_class(False, "-medium", "-large")
            self.size_small = True
            self.size_medium = False
            self.size_large = False
        elif width < 120:
            self.set_class(True, "-medium")
            self.set_class(False, "-small", "-large")
            self.size_small = False
            self.size_medium = True
            self.size_large = False
        else:
            self.set_class(True, "-large")
            self.set_class(False, "-small", "-medium")
            self.size_small = False
            self.size_medium = False
            self.size_large = True
    
    def compose(self) -> ComposeResult:
        """组合响应式布局"""
        yield MonitorLayout(id="monitor_layout")


# 导出主要布局组件
__all__ = [
    "StockListPanel",
    "UserGroupPanel", 
    "AnalysisPanel",
    "MainLayoutTab",
    "StatusBar",
    "MonitorLayout",
    "ResponsiveLayout"
]