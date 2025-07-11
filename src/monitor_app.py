#!/usr/bin/env python3
"""
Decidra股票监控应用程序
基于Textual框架的终端用户界面实现
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any

from textual.events import Key

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Header, Footer, TabbedContent, TabPane, DataTable, Static, 
    Button, Label
)
from textual.widget import Widget
from textual.reactive import reactive
from textual.binding import Binding

# 项目内部导入
from base.monitor import (
    StockData, TechnicalIndicators, MarketStatus, ConnectionStatus
)
from monitor.data_flow import DataFlowManager
from modules.futu_market import FutuMarket
from monitor.indicators import IndicatorsManager
from monitor.performance import PerformanceMonitor
from utils.config_manager import ConfigManager
from utils.logger import get_logger

# 导入新的UI布局组件
from monitor.ui import (
    MonitorLayout, StockListPanel, UserGroupPanel, 
    ChartPanel, AnalysisPanel, StatusBar,
    MainLayoutTab, AnalysisLayoutTab, ResponsiveLayout
)


class MonitorApp(App):
    """
    Decidra股票监控主应用程序
    基于Textual框架实现终端界面
    """
    
    
    # 键盘绑定定义
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("h", "help", "帮助"),
        Binding("a", "add_stock", "添加股票"),
        Binding("d", "delete_stock", "删除股票"),
        Binding("escape", "go_back", "返回"),
        Binding("tab", "switch_tab", "切换标签"),
        Binding("enter", "enter_analysis", "进入分析"),
        Binding("ctrl+c", "quit", "强制退出", priority=True),
    ]
    
    # 响应式属性
    current_stock_code: reactive[Optional[str]] = reactive(None)
    connection_status: reactive[ConnectionStatus] = reactive(ConnectionStatus.DISCONNECTED)
    market_status: reactive[MarketStatus] = reactive(MarketStatus.CLOSE)
    refresh_mode: reactive[str] = reactive("快照模式")
    
    def __init__(self):
        """初始化监控应用"""
        super().__init__()
        
        # 设置日志
        self.logger = get_logger(__name__)
        
        # 初始化组件管理器
        self.config_manager = ConfigManager()
        
        # 创建共享的富途市场实例
        self.futu_market = FutuMarket()
        # 标记为共享实例，防止其他组件重复关闭
        self.futu_market._is_shared_instance = True
        
        # 使用共享实例初始化其他管理器
        self.data_flow_manager = DataFlowManager(futu_market=self.futu_market)
        self.indicators_manager = IndicatorsManager()
        self.performance_monitor = PerformanceMonitor()
        
        # 数据存储
        self.monitored_stocks: List[str] = []
        self.stock_data: Dict[str, StockData] = {}
        self.technical_indicators: Dict[str, TechnicalIndicators] = {}
        
        # 重连控制
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        
        # 界面组件引用
        self.stock_table: Optional[DataTable] = None
        self.group_table: Optional[DataTable] = None
        self.group_stocks_content: Optional[Static] = None
        self.chart_panel: Optional[Static] = None
        self.ai_analysis_panel: Optional[Static] = None
        
        # 定时器
        self.refresh_timer: Optional[asyncio.Task] = None
        
        self.logger.info("MonitorApp 初始化完成")
    
    def compose(self) -> ComposeResult:
        """构建用户界面 - 使用新的UI布局组件"""
        # 使用新的MonitorLayout组件，包含完整的布局结构
        yield MonitorLayout(id="monitor_layout")

    def on_key(self, event: Key) -> None:
        """处理按键事件"""
        # 只处理退出相关的按键
        if event.key == "q":
            event.prevent_default()
            self.action_quit()
        elif event.key == "ctrl+c":
            event.prevent_default()
            self.action_quit()
        # 其他按键正常处理，不退出程序

    
    
    async def on_mount(self) -> None:
        """应用启动时的初始化"""
        self.logger.info("MonitorApp 正在启动...")
        
        # 加载配置
        await self._load_configuration()
        
        # 初始化数据管理器
        await self._initialize_data_managers()
        
        # 获取新UI组件的引用
        await self._setup_ui_references()
        
        # 加载默认股票列表
        await self._load_default_stocks()
        
        # 加载用户分组数据
        await self._load_user_groups()
        
        # 启动数据刷新
        await self._start_data_refresh()
        
        self.logger.info("MonitorApp 启动完成")
        
        # 更新状态显示
        await self._update_status_display()
    
    async def _setup_ui_references(self) -> None:
        """设置UI组件引用"""
        try:
            # 获取股票表格组件
            self.stock_table = self.query_one("#stock_table", DataTable)
            
            # 获取用户分组相关组件
            self.group_table = self.query_one("#group_table", DataTable)
            self.group_stocks_content = self.query_one("#group_stocks_content", Static)
            
            # 获取图表面板
            self.chart_panel = self.query_one("#kline_chart", Static)
            
            # 获取AI分析面板
            self.ai_analysis_panel = self.query_one("#ai_content", Static)
            
            self.logger.info("UI组件引用设置完成")
            
        except Exception as e:
            self.logger.error(f"设置UI组件引用失败: {e}")
    
    async def _load_configuration(self) -> None:
        """加载配置"""
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
                    'US.AAPL',   # 苹果
                ]
            else:
                self.monitored_stocks = stocks_config if isinstance(stocks_config, list) else [
                    'HK.00700',  # 腾讯
                    'HK.09988',  # 阿里巴巴
                    'US.AAPL',   # 苹果
                ]
            
            self.logger.info(f"加载配置完成，监控股票: {self.monitored_stocks}")
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            # 使用默认配置
            self.monitored_stocks = ['HK.00700', 'HK.09988', 'US.AAPL']
    
    async def _initialize_data_managers(self) -> None:
        """初始化数据管理器"""
        try:
            # 主动建立富途连接
            try:
                self.logger.info("正在连接富途API...")
                loop = asyncio.get_event_loop()
                
                # 在线程池中执行连接操作
                connect_success = await loop.run_in_executor(
                    None, 
                    self.futu_market.client.connect
                )
                
                if connect_success:
                    self.connection_status = ConnectionStatus.CONNECTED
                    self.logger.info("富途API连接成功")
                else:
                    self.connection_status = ConnectionStatus.DISCONNECTED
                    self.logger.warning("富途API连接失败")
                    
            except Exception as e:
                self.connection_status = ConnectionStatus.ERROR
                self.logger.error(f"富途API连接失败: {e}")
            
            # 初始化数据流管理器
            if hasattr(self.data_flow_manager, 'initialize'):
                await self.data_flow_manager.initialize()
            
        except Exception as e:
            self.logger.error(f"数据管理器初始化失败: {e}")
            self.connection_status = ConnectionStatus.ERROR
    
    async def _attempt_reconnect(self) -> bool:
        """尝试重新连接富途API"""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self.logger.error(f"超过最大重连次数 {self._max_reconnect_attempts}")
            return False
            
        self._reconnect_attempts += 1
        self.logger.info(f"尝试重连富途API (第 {self._reconnect_attempts} 次)")
        
        try:
            # 关闭旧连接
            if hasattr(self.futu_market, 'close'):
                self.futu_market.close()
            
            # 等待一段时间后重新创建连接
            await asyncio.sleep(2.0)
            
            # 重新创建富途市场实例
            self.futu_market = FutuMarket()
            self.futu_market._is_shared_instance = True
            
            # 检查新连接状态
            loop = asyncio.get_event_loop()
            connection_state = await loop.run_in_executor(
                None, 
                self.futu_market.get_connection_state
            )
            
            if connection_state[0]:
                self.connection_status = ConnectionStatus.CONNECTED
                self._reconnect_attempts = 0  # 重置重连计数
                self.logger.info("富途API重连成功")
                
                # 重新加载用户分组数据
                await self._load_user_groups()
                return True
            else:
                self.connection_status = ConnectionStatus.DISCONNECTED
                self.logger.warning(f"富途API重连失败: {connection_state[1]}")
                return False
                
        except Exception as e:
            self.logger.error(f"重连过程中出错: {e}")
            self.connection_status = ConnectionStatus.ERROR
            return False
    
    async def _load_default_stocks(self) -> None:
        """加载默认股票到表格"""
        if self.stock_table:
            # 清空现有数据
            self.stock_table.clear()
            
            # 添加股票行
            for stock_code in self.monitored_stocks:
                self.stock_table.add_row(
                    stock_code,
                    "加载中...",
                    "0.00",
                    "0.00%",
                    "0",
                    "未更新"
                )
        
        self.logger.info(f"加载默认股票列表: {self.monitored_stocks}")
    
    async def _load_user_groups(self) -> None:
        """加载用户分组数据"""
        if not self.group_table:
            self.logger.warning("group_table 未初始化，跳过加载用户分组")
            return
            
        try:
            # 在线程池中执行同步的富途API调用
            loop = asyncio.get_event_loop()
            user_groups = await loop.run_in_executor(
                None, 
                self.futu_market.get_user_security_group,
                "CUSTOM"  # 获取自定义分组
            )
            
            # 清空现有数据
            self.group_table.clear()
            
            # 添加分组数据到表格
            # 处理不同类型的返回数据
            processed_groups = []
            if user_groups is not None:
                import pandas as pd
                if isinstance(user_groups, pd.DataFrame):
                    if not user_groups.empty:
                        # DataFrame转换为字典列表
                        processed_groups = user_groups.to_dict('records')
                elif isinstance(user_groups, dict):
                    # 单个字典转换为列表
                    processed_groups = [user_groups]
                elif isinstance(user_groups, list):
                    # 已经是列表格式
                    processed_groups = user_groups
                    
            if processed_groups:
                self.logger.info(f"获取到 {len(processed_groups)} 个分组数据")
                
                for i, group in enumerate(processed_groups):
                    try:
                        if isinstance(group, dict):
                            # 富途API返回的字典格式
                            group_name = group.get('group_name', f'分组{i+1}')
                            stock_list = group.get('stock_list', [])
                            stock_count = len(stock_list) if stock_list else 0
                            group_type = group.get('group_type', 'CUSTOM')
                            
                            self.group_table.add_row(
                                group_name,
                                str(stock_count),
                                group_type
                            )
                            self.logger.debug(f"添加分组: {group_name}, 股票数: {stock_count}")
                            
                        elif isinstance(group, (list, tuple)) and len(group) >= 2:
                            # 可能的元组格式 (group_name, stock_list)
                            group_name = str(group[0])
                            stock_count = len(group[1]) if isinstance(group[1], (list, tuple)) else 0
                            
                            self.group_table.add_row(
                                group_name,
                                str(stock_count),
                                "CUSTOM"
                            )
                            self.logger.debug(f"添加分组(元组): {group_name}, 股票数: {stock_count}")
                            
                        else:
                            # 其他格式，作为分组名处理
                            group_name = str(group)
                            self.group_table.add_row(
                                group_name,
                                "未知",
                                "CUSTOM"
                            )
                            self.logger.debug(f"添加分组(字符串): {group_name}")
                            
                    except Exception as e:
                        self.logger.warning(f"处理分组数据失败: {e}, 数据: {group}")
                        continue
                        
                # 如果没有成功添加任何分组，显示默认信息
                if self.group_table.row_count == 0:
                    self.group_table.add_row("数据解析失败", "0", "ERROR")
                    
            else:
                # 添加默认提示行
                self.group_table.add_row("暂无分组", "0", "-")
                self.logger.info("未获取到分组数据，显示默认提示")
            
            self.logger.info(f"加载用户分组完成，共 {len(processed_groups)} 个分组")
            
        except Exception as e:
            self.logger.warning(f"加载用户分组失败: {e}")
            # API调用失败时不更新连接状态，只显示错误信息
            if self.group_table:
                self.group_table.clear()
                self.group_table.add_row(
                    "加载失败",
                    "0",
                    "ERROR"
                )
    
    
    
    async def _start_data_refresh(self) -> None:
        """启动数据刷新"""
        try:
            # 判断市场状态并设置刷新模式
            market_status = await self._detect_market_status()
            
            if market_status == MarketStatus.OPEN:
                self.refresh_mode = "实时模式"
                # 启动实时数据订阅
                await self._start_realtime_subscription()
            else:
                self.refresh_mode = "快照模式"
                # 启动快照数据刷新
                await self._start_snapshot_refresh()
            
            self.logger.info(f"数据刷新启动: {self.refresh_mode}")
            
            # 更新状态显示
            await self._update_status_display()
            
        except Exception as e:
            self.logger.error(f"启动数据刷新失败: {e}")
    
    async def _detect_market_status(self) -> MarketStatus:
        """检测市场状态"""
        try:
            # 简化的市场状态检测
            current_time = datetime.now()
            hour = current_time.hour
            
            # 简单判断：9:30-16:00为开盘时间
            if 9 <= hour < 16:
                return MarketStatus.OPEN
            else:
                return MarketStatus.CLOSE
                
        except Exception as e:
            self.logger.error(f"检测市场状态失败: {e}")
            return MarketStatus.CLOSE
    
    async def _start_realtime_subscription(self) -> None:
        """启动实时数据订阅"""
        try:
            if self.connection_status == ConnectionStatus.CONNECTED:
                # 订阅实时数据
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    None,
                    self.futu_market.subscribe,
                    self.monitored_stocks,
                    ["QUOTE"],  # 订阅类型：实时报价
                    True,       # is_first_push
                    True        # is_unlimit_push
                )
                if success:
                    self.logger.info("实时数据订阅启动")
                else:
                    raise Exception("订阅失败")
        except Exception as e:
            self.logger.error(f"实时数据订阅失败: {e}")
            # 降级到快照模式
            await self._start_snapshot_refresh()
    
    async def _start_snapshot_refresh(self) -> None:
        """启动快照数据刷新"""
        # 创建定时刷新任务
        self.refresh_timer = asyncio.create_task(self._snapshot_refresh_loop())
        self.logger.info("快照数据刷新启动")
    
    async def _snapshot_refresh_loop(self) -> None:
        """快照数据刷新循环"""
        while True:
            try:
                await self._refresh_stock_data()
                await asyncio.sleep(10)  # 10秒刷新一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"快照数据刷新错误: {e}")
                await asyncio.sleep(30)  # 错误时延长间隔
    
    async def _refresh_stock_data(self) -> None:
        """刷新股票数据"""
        try:
            # 直接调用API获取实时行情数据
            loop = asyncio.get_event_loop()
            market_snapshots = await loop.run_in_executor(
                None,
                self.futu_market.get_market_snapshot,
                self.monitored_stocks
            )
            
            # 转换数据格式并更新
            if market_snapshots:
                # 更新连接状态为已连接
                self.connection_status = ConnectionStatus.CONNECTED
                
                for snapshot in market_snapshots:
                    # 修复：snapshot现在是MarketSnapshot对象，不是字典
                    if hasattr(snapshot, 'code'):
                        stock_code = snapshot.code
                        stock_info = self._convert_snapshot_to_stock_data(snapshot)
                        self.stock_data[stock_code] = stock_info
                
                # 更新界面
                await self._update_stock_table()
                await self._update_stock_info()
                await self._update_status_display()
                
                self.logger.info("股票数据刷新成功")
            else:
                # API调用返回空数据，可能是连接问题
                self.connection_status = ConnectionStatus.DISCONNECTED
                await self._update_status_display()
                self.logger.warning("API调用返回空数据，可能存在连接问题")
            
        except Exception as e:
            # API调用失败，更新连接状态
            self.connection_status = ConnectionStatus.ERROR
            await self._update_status_display()
            self.logger.error(f"刷新股票数据失败: {e}")
    
    def _convert_snapshot_to_stock_data(self, snapshot) -> StockData:
        """将富途快照数据转换为标准StockData格式"""
        try:
            # 修复：处理MarketSnapshot对象而不是字典
            if hasattr(snapshot, '__dict__'):
                # 如果是MarketSnapshot对象，使用正确的属性名
                code = getattr(snapshot, 'code', '')
                name = ''  # MarketSnapshot可能没有股票名称，需要单独获取
                current_price = float(getattr(snapshot, 'last_price', 0))  # 使用last_price
                prev_close = float(getattr(snapshot, 'prev_close_price', 0))
                volume = int(getattr(snapshot, 'volume', 0))
            else:
                # 如果是字典，使用原有逻辑
                code = snapshot.get('code', '')
                name = snapshot.get('stock_name', '')
                current_price = float(snapshot.get('cur_price', 0))
                prev_close = float(snapshot.get('prev_close_price', 0))
                volume = int(snapshot.get('volume', 0))
            
            # 计算涨跌幅
            change_rate = 0.0
            if prev_close > 0:
                change_rate = ((current_price - prev_close) / prev_close) * 100
            
            return StockData(
                code=code,
                name=name or code,  # 如果没有名称，使用代码
                current_price=current_price,
                change_rate=change_rate,
                volume=volume,
                market_status=MarketStatus.OPEN,
                last_update=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"转换股票数据时发生错误: {e}")
            # 错误处理也要适配对象和字典两种情况
            fallback_code = ''
            fallback_name = ''
            try:
                if hasattr(snapshot, '__dict__'):
                    fallback_code = getattr(snapshot, 'code', '')
                    fallback_name = fallback_code  # 使用代码作为名称
                else:
                    fallback_code = snapshot.get('code', '')
                    fallback_name = snapshot.get('stock_name', '')
            except:
                pass
                
            return StockData(
                code=fallback_code,
                name=fallback_name or fallback_code,
                current_price=0.0,
                change_rate=0.0,
                volume=0,
                market_status=MarketStatus.CLOSE,
                last_update=datetime.now()
            )
    
    async def _on_realtime_data_received(self, data: Dict[str, Any]) -> None:
        """处理实时数据回调"""
        try:
            # 处理实时推送数据
            stock_code = data.get('stock_code')
            if stock_code in self.monitored_stocks:
                # 更新股票数据
                stock_info = StockData(
                    code=stock_code,
                    name=data.get('name', ''),
                    current_price=data.get('price', 0.0),
                    change_rate=data.get('change_rate', 0.0),
                    volume=data.get('volume', 0),
                    market_status=MarketStatus.OPEN,
                    last_update=datetime.now()
                )
                
                self.stock_data[stock_code] = stock_info
                
                # 更新界面
                await self._update_stock_table()
                await self._update_stock_info()
                
        except Exception as e:
            self.logger.error(f"处理实时数据失败: {e}")
    
    async def _update_stock_table(self) -> None:
        """更新股票表格"""
        if not self.stock_table:
            return
            
        try:
            # 更新表格数据
            for row_index, stock_code in enumerate(self.monitored_stocks):
                stock_info = self.stock_data.get(stock_code)
                
                if stock_info:
                    # 格式化数据
                    price_str = f"{stock_info.current_price:.2f}"
                    change_str = f"{stock_info.change_rate:.2f}%"
                    volume_str = f"{stock_info.volume:,}"
                    time_str = stock_info.last_update.strftime("%H:%M:%S")
                    
                    # 更新行数据
                    self.stock_table.update_cell(row_index, 1, stock_info.name)
                    self.stock_table.update_cell(row_index, 2, price_str)
                    self.stock_table.update_cell(row_index, 3, change_str)
                    self.stock_table.update_cell(row_index, 4, volume_str)
                    self.stock_table.update_cell(row_index, 5, time_str)
                    
        except Exception as e:
            self.logger.error(f"更新股票表格失败: {e}")
    
    async def _update_stock_info(self) -> None:
        """更新股票信息面板"""
        if not self.stock_info_panel or not self.current_stock_code:
            return
            
        try:
            stock_info = self.stock_data.get(self.current_stock_code)
            if stock_info:
                # 确定涨跌颜色
                change_color = "green" if stock_info.change_rate > 0 else "red" if stock_info.change_rate < 0 else "white"
                change_symbol = "▲" if stock_info.change_rate > 0 else "▼" if stock_info.change_rate < 0 else "■"
                
                # 市场状态颜色
                market_color = "green" if stock_info.market_status == MarketStatus.OPEN else "yellow"
                
                # 构建美化的信息文本
                info_text = f"""[bold white]股票代码:[/bold white] [bold cyan]{stock_info.code}[/bold cyan]
[bold white]股票名称:[/bold white] [bold]{stock_info.name}[/bold]

[bold white]当前价格:[/bold white] [bold yellow]{stock_info.current_price:.2f}[/bold yellow]
[bold white]涨跌幅:[/bold white] [{change_color}]{change_symbol} {stock_info.change_rate:.2f}%[/{change_color}]
[bold white]成交量:[/bold white] [cyan]{stock_info.volume:,}[/cyan]

[bold white]市场状态:[/bold white] [{market_color}]{stock_info.market_status.value}[/{market_color}]
[bold white]更新时间:[/bold white] [dim]{stock_info.last_update.strftime('%H:%M:%S')}[/dim]

[dim]操作提示：
• Enter: 进入分析界面
• D: 删除此股票
• R: 刷新数据[/dim]"""
                
                self.stock_info_panel.update(info_text)
            
        except Exception as e:
            self.logger.error(f"更新股票信息失败: {e}")
    
    # 事件处理方法
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件"""
        try:
            # 判断是哪个表格的选择事件
            if event.data_table.id == "stock_table":
                # 股票表格选择
                row_index = event.cursor_row
                if 0 <= row_index < len(self.monitored_stocks):
                    self.current_stock_code = self.monitored_stocks[row_index]
                    await self._update_stock_info()
                    self.logger.info(f"选择股票: {self.current_stock_code}")
            elif event.data_table.id == "group_table":
                # 分组表格选择
                await self._handle_group_selection(event.cursor_row)
        except Exception as e:
            self.logger.error(f"处理行选择事件失败: {e}")
    
    async def _handle_group_selection(self, row_index: int) -> None:
        """处理分组选择事件"""
        try:
            if not self.group_table:
                return
                
            # 获取选中分组的信息
            group_row = self.group_table.get_row_at(row_index)
            if not group_row:
                return
                
            group_name = str(group_row[0])  # 分组名称
            
            if group_name in ["暂无分组", "加载失败", "连接未建立", "数据错误"]:
                # 显示提示信息
                if self.group_stocks_content:
                    self.group_stocks_content.update("[dim]无可用数据[/dim]")
                return
            
            # 直接尝试获取分组股票，不检查连接状态
            
            # 获取分组中的股票列表
            loop = asyncio.get_event_loop()
            group_stocks = await loop.run_in_executor(
                None,
                self.futu_market.get_user_security,
                group_name
            )
            
            # 更新分组股票显示
            if self.group_stocks_content:
                if group_stocks:
                    stock_list_text = f"[bold yellow]{group_name} - 股票列表[/bold yellow]\n\n"
                    for i, stock in enumerate(group_stocks[:10]):  # 最多显示10只股票
                        if isinstance(stock, dict):
                            stock_code = stock.get('code', 'Unknown')
                            stock_name = stock.get('name', '')
                            stock_list_text += f"{i+1}. {stock_code} {stock_name}\n"
                        else:
                            stock_list_text += f"{i+1}. {stock}\n"
                    
                    if len(group_stocks) > 10:
                        stock_list_text += f"\n[dim]... 还有 {len(group_stocks) - 10} 只股票[/dim]"
                    
                    self.group_stocks_content.update(stock_list_text)
                else:
                    self.group_stocks_content.update(f"[yellow]{group_name}[/yellow]\n\n[dim]该分组暂无股票[/dim]")
            
            self.logger.info(f"选择分组: {group_name}, 包含 {len(group_stocks) if group_stocks else 0} 只股票")
            
        except Exception as e:
            self.logger.error(f"处理分组选择失败: {e}")
            if self.group_stocks_content:
                self.group_stocks_content.update("[red]加载分组股票失败[/red]")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        try:
            if event.button.id == "btn_add":
                await self.action_add_stock()
            elif event.button.id == "btn_delete":
                await self.action_delete_stock()
            elif event.button.id == "btn_refresh":
                await self.action_refresh()
        except Exception as e:
            self.logger.error(f"处理按钮事件失败: {e}")
    
    # 动作方法
    async def action_add_stock(self) -> None:
        """添加股票动作"""
        # TODO: 实现添加股票对话框
        self.logger.info("添加股票功能待实现")
    
    async def action_delete_stock(self) -> None:
        """删除股票动作"""
        if self.current_stock_code and self.current_stock_code in self.monitored_stocks:
            # TODO: 实现确认对话框
            self.monitored_stocks.remove(self.current_stock_code)
            await self._load_default_stocks()
            await self._update_status_display()
            self.logger.info(f"删除股票: {self.current_stock_code}")
    
    async def action_refresh(self) -> None:
        """手动刷新动作"""
        self.logger.info("开始手动刷新数据...")
        
        # 直接执行数据刷新，不检查连接状态
        await self._refresh_stock_data()
        
        # 同时刷新用户分组数据
        await self._load_user_groups()
        
        self.logger.info("手动刷新数据和分组信息完成")
    
    async def action_help(self) -> None:
        """显示帮助动作"""
        # TODO: 实现帮助对话框
        self.logger.info("帮助功能待实现")
    
    async def action_go_back(self) -> None:
        """返回主界面动作"""
        # 切换到主界面标签页
        tabs = self.query_one(TabbedContent)
        tabs.active = "main"
    
    async def action_switch_tab(self) -> None:
        """切换标签页动作"""
        tabs = self.query_one(TabbedContent)
        if tabs.active == "main":
            tabs.active = "analysis"
        else:
            tabs.active = "main"
    
    async def action_enter_analysis(self) -> None:
        """进入分析界面动作"""
        if self.current_stock_code:
            # 切换到分析标签页
            tabs = self.query_one(TabbedContent)
            tabs.active = "analysis"
            
            # 更新分析界面内容
            await self._update_analysis_interface()
            
            self.logger.info(f"进入分析界面: {self.current_stock_code}")
    
    async def _update_analysis_interface(self) -> None:
        """更新分析界面内容"""
        if not self.current_stock_code:
            return
            
        try:
            # 更新图表面板
            if self.chart_panel:
                chart_text = f"""[bold blue]{self.current_stock_code} K线图表[/bold blue]

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
                ai_text = f"""[bold green]{self.current_stock_code} AI智能分析[/bold green]

[dim]分析维度：
• 技术指标分析 (MA, RSI, MACD)
• 买卖信号推荐
• 支撑位和阻力位
• 风险评估等级[/dim]

[yellow]正在生成AI分析报告...[/yellow]"""
                self.ai_analysis_panel.update(ai_text)
            
        except Exception as e:
            self.logger.error(f"更新分析界面失败: {e}")
    
    async def action_quit(self) -> None:
        """退出应用动作"""
        self.logger.info("应用程序正在退出...")
        
        # 设置优雅退出标志
        self._is_quitting = True
        
        try:
            # 1. 立即停止所有定时器和循环任务
            if self.refresh_timer:
                self.refresh_timer.cancel()
                self.refresh_timer = None
                self.logger.info("刷新定时器已停止")
            
            # 2. 取消所有异步任务
            try:
                # 获取当前事件循环中的所有任务
                loop = asyncio.get_event_loop()
                pending_tasks = [task for task in asyncio.all_tasks(loop) 
                               if not task.done() and task != asyncio.current_task()]
                
                if pending_tasks:
                    self.logger.info(f"取消 {len(pending_tasks)} 个待处理任务")
                    for task in pending_tasks:
                        if hasattr(task, 'get_name') and 'refresh' in task.get_name():
                            task.cancel()
                    
                    # 等待任务取消完成
                    await asyncio.wait_for(
                        asyncio.gather(*pending_tasks, return_exceptions=True),
                        timeout=1.0  # 缩短到1秒
                    )
                    self.logger.info("异步任务取消完成")
            except asyncio.TimeoutError:
                self.logger.warning("部分异步任务取消超时")
            except Exception as e:
                self.logger.warning(f"取消异步任务时出错: {e}")
            
            # 3. 清理数据流管理器
            try:
                if hasattr(self.data_flow_manager, 'cleanup'):
                    await asyncio.wait_for(
                        self.data_flow_manager.cleanup(),
                        timeout=1.5  # 缩短到1.5秒
                    )
                    self.logger.info("数据流管理器清理完成")
            except asyncio.TimeoutError:
                self.logger.warning("数据流管理器清理超时")
            except Exception as e:
                self.logger.warning(f"数据流管理器清理失败: {e}")
            
            # 4. 关闭富途连接
            try:
                if hasattr(self.futu_market, 'client') and self.futu_market.client:
                    # 在线程池中执行同步的关闭操作
                    loop = asyncio.get_event_loop()
                    await asyncio.wait_for(
                        loop.run_in_executor(None, self.futu_market.client.disconnect),
                        timeout=1.5  # 缩短到1.5秒
                    )
                    self.logger.info("富途连接关闭完成")
            except asyncio.TimeoutError:
                self.logger.warning("富途连接关闭超时")
            except Exception as e:
                self.logger.warning(f"富途连接关闭失败: {e}")
            
            # 5. 保存配置（最低优先级）
            try:
                await self._save_config_async()
                self.logger.info("配置保存完成")
            except Exception as e:
                self.logger.warning(f"配置保存失败: {e}")
            
        except Exception as e:
            self.logger.error(f"退出过程中发生错误: {e}")
        finally:
            # 6. 优雅地退出应用
            self.logger.info("准备退出应用")
            try:
                # 使用 Textual 的标准退出方法
                self.exit(return_code=0)
            except Exception as e:
                self.logger.error(f"应用退出失败: {e}")
                # 如果标准退出失败，尝试其他方式
                try:
                    # 设置退出标志让主循环自然结束
                    if hasattr(self, '_exit_flag'):
                        self._exit_flag = True
                    # 发送退出信号
                    import signal
                    import os
                    os.kill(os.getpid(), signal.SIGTERM)
                except:
                    # 最后的手段：使用 sys.exit() 而不是 os._exit()
                    import sys
                    self.logger.warning("使用 sys.exit() 退出")
                    sys.exit(0)

    async def _save_config_async(self):
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
                    timeout=1.0  # 缩短到1秒
                )
        except Exception as e:
            self.logger.error(f"配置保存异常: {e}")
            raise
    
    async def _cleanup_resources(self) -> None:
        """清理资源"""
        try:
            cleanup_tasks = []
            
            # 断开富途连接
            if self.futu_market:
                loop = asyncio.get_event_loop()
                cleanup_task = loop.run_in_executor(None, self._cleanup_futu_market)
                cleanup_tasks.append(cleanup_task)
            
            # 停止数据流管理器
            if self.data_flow_manager and hasattr(self.data_flow_manager, 'cleanup'):
                cleanup_tasks.append(self.data_flow_manager.cleanup())
            
            # 并发执行清理任务，但设置总超时
            if cleanup_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*cleanup_tasks, return_exceptions=True),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("部分清理任务超时")
            
            self.logger.info("资源清理完成")
            
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
            # 继续退出过程，不让异常阻止程序退出
    
    def _cleanup_futu_market(self) -> None:
        """清理富途市场连接"""
        try:
            # 只调用一次close方法，FutuModuleBase.close()已经包含了完整的清理流程
            if hasattr(self.futu_market, 'close'):
                self.futu_market.close()
                self.logger.info("富途市场连接已清理")
        except Exception as e:
            self.logger.warning(f"清理富途市场连接时出错: {e}")
    
    async def _update_status_display(self) -> None:
        """更新状态栏显示"""
        try:
            # 构建状态信息
            connection_status = "🟢 已连接" if self.connection_status == ConnectionStatus.CONNECTED else "🔴 未连接"
            market_status = "📈 开盘" if self.market_status == MarketStatus.OPEN else "📉 闭市"
            refresh_info = f"🔄 {self.refresh_mode}"
            stock_count = f"📊 监控{len(self.monitored_stocks)}只股票"
            
            # 更新应用标题
            self.title = f"Decidra股票监控 | {connection_status} | {market_status} | {refresh_info} | {stock_count}"
            
        except Exception as e:
            self.logger.error(f"更新状态显示失败: {e}")


def main():
    """主函数"""
    app = MonitorApp()
    app.run()


if __name__ == "__main__":
    main()