"""
Monitor UI Layout Module
基于 Textual 框架的监控界面布局组件
参考: https://textual.textualize.io/guide/layout/
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Grid, Horizontal
from textual.widgets import (
    Header, Footer, Static, DataTable, Label, 
    TabbedContent, TabPane, Input, ProgressBar
)
from textual.reactive import reactive
from textual.binding import Binding
from typing import List, Dict, Optional

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


class ChartPanel(Container):
    """图表面板 - 分析界面上部80%"""
    
    DEFAULT_CSS = """
    ChartPanel {
        height: 80%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 1;
    }
    
    ChartPanel .chart-container {
        height: 60%;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    ChartPanel .volume-container {
        height: 40%;
        background: $surface;
        border: solid $secondary;
    }
    
    ChartPanel .chart-controls {
        height: 3;
        dock: bottom;
        background: $panel;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "K线图表分析"
        
    def compose(self) -> ComposeResult:
        """组合图表组件"""
        # K线图表区域
        with Container(classes="chart-container"):
            yield Static(
                "[bold blue]K线图表显示区域[/bold blue]\n\n" +
                "[dim]图表功能：\n" +
                "• D: 切换到日线图\n" +
                "• W: 切换到周线图\n" +
                "• M: 切换到月线图\n" +
                "• ←→: 调整时间范围[/dim]",
                id="kline_chart"
            )
        
        # 成交量区域
        with Container(classes="volume-container"):
            yield Static(
                "[bold green]成交量柱状图[/bold green]\n" +
                "显示成交量数据...",
                id="volume_chart"
            )
        
        # 图表控制快捷键提示
        with Container(classes="chart-controls"):
            yield Static(
                "[bold blue]D[/bold blue] 日线  [bold green]W[/bold green] 周线  [bold yellow]M[/bold yellow] 月线  [dim]时间范围: 最近30天[/dim]",
                id="chart_hotkey_hints"
            )


class AnalysisPanel(Container):
    """分析面板 - 分析界面下部20%"""
    
    DEFAULT_CSS = """
    AnalysisPanel {
        height: 20%;
        layout: vertical;
    }
    
    AnalysisPanel .ai-analysis {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        padding: 1;
    }
    
    AnalysisPanel .input-area {
        height: 3;
        dock: bottom;
        background: $panel;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合分析面板组件"""
        # AI分析和操作计划区域
        with Container(classes="ai-analysis"):
            yield Static("AI分析建议", id="ai_title")
            yield Static(
                "[bold green]AI智能分析[/bold green]\n\n" +
                "[dim]分析维度：\n" +
                "• 技术指标分析 (MA, RSI, MACD)\n" +
                "• 买卖信号推荐\n" +
                "• 支撑位和阻力位\n" +
                "• 风险评估等级[/dim]\n\n" +
                "[yellow]正在生成AI分析报告...[/yellow]",
                id="ai_content"
            )
            
            # 用户输入区域
            with Container(classes="input-area"):
                yield Input(
                    placeholder="输入操作计划...",
                    id="plan_input"
                )


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
    
    DEFAULT_CSS = """
    AnalysisLayoutTab {
        layout: vertical;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合分析界面布局"""
        yield ChartPanel(id="chart_panel")
        yield AnalysisPanel(id="analysis_panel")


class StatusBar(Container):
    """状态栏组件"""
    
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: top;
        background: $accent;
        color: $text;
        layout: horizontal;
    }
    
    StatusBar .status-item {
        margin: 0 2;
        content-align: center middle;
    }
    
    StatusBar .connection-status {
        background: $success;
        color: $text;
        padding: 0 1;
    }
    
    StatusBar .market-status {
        background: $warning;
        color: $text;
        padding: 0 1;
    }
    
    StatusBar .refresh-mode {
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """组合状态栏"""
        yield Static("🟢 已连接", classes="status-item connection-status", id="connection_status")
        yield Static("📈 开盘", classes="status-item market-status", id="market_status")
        yield Static("🔄 实时模式", classes="status-item refresh-mode", id="refresh_mode")
        yield Static("📊 监控3只股票", classes="status-item", id="stock_count")
        yield Static("更新: 刚刚", classes="status-item", id="last_update")


class MonitorLayout(Container):
    """监控界面完整布局"""
    
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
        # 头部状态栏
        yield Header()
        yield StatusBar(id="status_bar")
        
        # 主体标签页内容
        with TabbedContent(initial="main"):
            # 主界面标签页
            with TabPane("主界面", id="main"):
                yield MainLayoutTab(id="main_layout")
            
            # 分析界面标签页
            with TabPane("分析界面", id="analysis"):
                yield AnalysisLayoutTab(id="analysis_layout")
        
        # 底部导航栏
        yield Footer()


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
    "ChartPanel",
    "AnalysisPanel",
    "MainLayoutTab",
    "AnalysisLayoutTab",
    "StatusBar",
    "MonitorLayout",
    "ResponsiveLayout"
]