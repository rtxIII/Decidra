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
        layout: horizontal;
    }
    
    AnalysisPanel .realtime-data-column TabbedContent {
        height: 1fr;
    }
    
    AnalysisPanel .realtime-data-column TabPane {
        padding: 0;
    }
    
    /* AI交互区域样式 - 重新布局为左右两栏 */
    AnalysisPanel .ai-interaction-area .ai-chat-section {
        width: 50%;
        overflow-y: auto;
        background: $surface;
        border: solid $secondary;
        padding: 1;
        margin-right: 1;
    }
    
    AnalysisPanel .ai-interaction-area .ai-analysis-section {
        width: 50%;
        overflow-y: auto;
        background: $surface;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """严格按照MVP设计组合分析面板的完整布局"""
        # 1. 基础信息区域
        with Container(classes="basic-info-area"):
            yield Static(
                "股票代码: 000001    名称: 平安银行    市场: 深交所    行业: 银行业    市值: 2847.3亿    流通股: 193.6亿股    PE: 5.2    PB: 0.65    ROE: 12.8%    更新时间: 2025-07-17 14:32:25",
                id="basic_info_content"
            )
        
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
                with TabbedContent(initial="kline"):
                    # K线数据标签页
                    with TabPane("K线数据", id="kline"):
                        yield Static(
                            "[bold blue]K线数据[/bold blue]\n" +
                            "开盘:12.58  最高:12.96\n" +
                            "最低:12.51  收盘:12.85\n" +
                            "成交:1.2亿  涨跌:+2.35%",
                            id="kline_content"
                        )
                    
                    # 逐笔数据标签页
                    with TabPane("逐笔数据", id="tick"):
                        yield Static(
                            "[bold yellow]逐笔数据[/bold yellow]\n" +
                            "14:32:15  12.85↑125  89手\n" +
                            "14:32:18  12.84↓89   45手\n" +
                            "14:32:20  12.85↑201  156手\n" +
                            "14:32:22  12.86↑67   67手",
                            id="tick_content"
                        )
                    
                    # 经纪队列数据标签页
                    with TabPane("经纪队列", id="broker"):
                        yield Static(
                            "[bold cyan]经纪队列[/bold cyan]\n" +
                            "中信证券 买入排队 1.2万手\n" +
                            "平安证券 卖出排队 8.9千手\n" +
                            "招商证券 买入排队 6.8千手",
                            id="broker_content"
                        )
            
            # 3.3 资金流向区域（38%宽度） - 与第4层互换位置
            with Container(classes="money-flow-column"):
                yield Static("资金流向/分布区域", id="money_flow_title")
                yield Static(
                    "主力净流入: +2.3亿 ↑    超大单: +1.8亿(+3.2%)    大单: +0.5亿(+0.9%)    中单: -1.2亿(-2.1%)    小单: -1.1亿(-1.9%)    │    大单占比: 45.2%    中单: 32.1%    小单: 22.7%    │    北向资金: +0.85亿     融资余额: 25.6亿(-0.3%)     融券余额: 1.2亿(+2.1%)     资金净流入排名: 17/4832     活跃度: 中等     │    换手率排名: 456/4832    热度: ★★★☆☆",
                    id="money_flow_content_column"
                )
        
        # 4. AI交互区域 - 重新布局为左右两栏
        with Container(classes="ai-interaction-area"):
            # AI对话历史区域 - 移到左边并扩展到最左边
            with Container(classes="ai-chat-section"):
                yield Static(
                    "[bold white]💭 智能问答 (输入'?'查看命令)[/bold white]\n" +
                    "[bold green]> 用户:[/bold green] 这只股票适合长期持有吗？\n" +
                    "[bold cyan]🤖 AI:[/bold cyan] 从基本面看，平安银行ROE12.8%，PB0.65倍，估值偏低。银行股适合\n" +
                    "      长期价值投资，建议分批建仓，关注利率政策变化...\n\n" +
                    "[bold green]> 用户:[/bold green] 目前技术面风险大吗？\n" +
                    "[bold cyan]🤖 AI:[/bold cyan] RSI65.2偏高，短期存在回调风险，建议等待回调至支撑位...\n\n" +
                    "[bold cyan]🎛️ 快捷功能:[/bold cyan] [F1]技术分析 [F2]基本面 [F3]资金面 [F4]同行对比 [F5]风险评估",
                    id="ai_chat_history"
                )
            
            # AI分析区域 - 移到右边并扩展到最右边
            with Container(classes="ai-analysis-section"):
                yield Static(
                    "[bold cyan]🤖 AI:[/bold cyan] 根据技术面分析，该股票处于上升通道中，建议关注：\n\n" +
                    "[bold yellow]📊 技术指标:[/bold yellow]\n" +
                    "• RSI(14): 65.2 ➤ 偏强势，注意回调风险\n" +
                    "• MACD: 金叉信号，动能向上\n" +
                    "• 均线: 突破20日线，多头排列\n\n" +
                    "[bold green]🎯 关键价位:[/bold green]\n" +
                    "• 支撑位: 12.45 (重要支撑)\n" +
                    "• 阻力位: 13.15 (前高压力)\n" +
                    "• 目标价: 13.20-13.50\n\n" +
                    "[bold blue]🔮 AI预测 (置信度75%):[/bold blue]\n" +
                    "短期(1-3天): 看涨 ↗ 预期涨幅 2-4%\n" +
                    "中期(1-2周): 震荡上行，关注量能",
                    id="ai_analysis_content"
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
        yield AnalysisPanel(id="analysis_panel")


class StatusBar(Container):
    """状态栏组件"""
    
    DEFAULT_CSS = """
    StatusBar {
        height: 3;
        background: $surface;
        color: $text;
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
        color: $text;
    }
    
    StatusBar .connection-status {
        background: $success;
        color: $text-success;
        padding: 0 1;
    }
    
    StatusBar .market-status {
        background: $warning;
        color: $text-warning;
        padding: 0 1;
    }
    
    StatusBar .refresh-mode {
        background: $primary;
        color: $text-primary;
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
        with TabbedContent(initial="main"):
            # 主界面标签页
            with TabPane("主界面", id="main"):
                yield MainLayoutTab(id="main_layout")
            
            # 分析界面标签页
            with TabPane("分析界面", id="analysis"):
                yield AnalysisLayoutTab(id="analysis_layout")


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
    "AnalysisLayoutTab",
    "StatusBar",
    "MonitorLayout",
    "ResponsiveLayout"
]