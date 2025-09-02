"""
专业信息输出框架
适用于金融监控应用的多功能信息显示组件

主要功能:
- 多种信息类型支持 (日志、股票数据、交易信息、性能指标等)
- 分级显示系统 (ERROR、WARNING、INFO、DEBUG)
- 实时滚动更新和缓冲区管理
- 过滤和搜索功能
- 与项目logger系统集成
- 专业的金融数据显示样式
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
from collections import deque

from rich.json import JSON
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Label, Static, Input, Button, Select
from textual.reactive import reactive
from textual.message import Message

from utils import logger

# 导入AI相关模块
try:
    from modules.ai.claude_ai_client import create_claude_client
    from monitor.widgets.window_dialog import WindowInputDialog
    AI_MODULES_AVAILABLE = True
except ImportError:
    create_claude_client = None
    WindowInputDialog = None
    AI_MODULES_AVAILABLE = False


class InfoType(Enum):
    """信息类型枚举"""
    LOG = "log"                    # 系统日志
    STOCK_DATA = "stock_data"      # 股票数据
    TRADE_INFO = "trade_info"      # 交易信息
    PERFORMANCE = "performance"    # 性能指标
    API_STATUS = "api_status"      # API状态
    USER_ACTION = "user_action"    # 用户操作
    ERROR = "error"                # 错误信息
    WARNING = "warning"            # 警告信息


class InfoLevel(Enum):
    """信息级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class InfoMessage:
    """信息消息数据类"""
    content: str
    info_type: InfoType
    level: InfoLevel
    timestamp: datetime
    source: str = ""
    data: Optional[Dict[str, Any]] = None
    formatted_text: Optional[Text] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.formatted_text is None:
            self.formatted_text = self._format_message()
    
    def _format_message(self) -> Text:
        """格式化消息文本"""
        # 时间戳格式化
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        # 根据信息类型和级别选择颜色和图标
        color, icon = self._get_style()
        
        # 构建格式化文本
        text = Text()
        text.append(f"[{time_str}] ", style="dim")
        text.append(f"{icon} ", style=color)
        text.append(f"[{self.info_type.value.upper()}] ", style=f"bold {color}")
        text.append(self.content, style=color if self.level in [InfoLevel.ERROR, InfoLevel.WARNING] else "default")
        
        if self.source:
            text.append(f" ({self.source})", style="dim")
        
        return text
    
    def _get_style(self) -> tuple[str, str]:
        """获取样式和图标"""
        style_map = {
            InfoLevel.DEBUG: ("blue", "🔍"),
            InfoLevel.INFO: ("green", "ℹ️"),
            InfoLevel.WARNING: ("yellow", "⚠️"),
            InfoLevel.ERROR: ("red", "❌"),
            InfoLevel.CRITICAL: ("bold red", "🚨"),
        }
        
        # 根据信息类型调整样式
        type_icons = {
            InfoType.STOCK_DATA: "📈",
            InfoType.TRADE_INFO: "💰",
            InfoType.PERFORMANCE: "⚡",
            InfoType.API_STATUS: "🔗",
            InfoType.USER_ACTION: "👤",
        }
        
        color, _ = style_map.get(self.level, ("default", "•"))
        icon = type_icons.get(self.info_type, style_map.get(self.level, ("default", "•"))[1])
        
        return color, icon


class InfoBuffer:
    """信息缓冲区管理器"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化缓冲区
        
        Args:
            max_size: 最大存储消息数量
        """
        self.max_size = max_size
        self.messages: deque[InfoMessage] = deque(maxlen=max_size)
        self.filters: Dict[str, Callable[[InfoMessage], bool]] = {}
        self.logger = logger.get_logger("info_buffer")
    
    def add_message(self, message: InfoMessage) -> None:
        """添加新消息"""
        self.messages.append(message)
        self.logger.debug(f"Added message: {message.info_type.value} - {message.content[:50]}...")
    
    def get_filtered_messages(self, 
                            info_types: Optional[List[InfoType]] = None,
                            levels: Optional[List[InfoLevel]] = None,
                            time_range: Optional[tuple[datetime, datetime]] = None,
                            search_text: Optional[str] = None) -> List[InfoMessage]:
        """
        获取过滤后的消息列表
        
        Args:
            info_types: 信息类型过滤
            levels: 级别过滤
            time_range: 时间范围过滤 (start, end)
            search_text: 搜索文本
        """
        filtered = list(self.messages)
        
        # 类型过滤
        if info_types:
            filtered = [msg for msg in filtered if msg.info_type in info_types]
        
        # 级别过滤
        if levels:
            filtered = [msg for msg in filtered if msg.level in levels]
        
        # 时间范围过滤
        if time_range:
            start_time, end_time = time_range
            filtered = [msg for msg in filtered if start_time <= msg.timestamp <= end_time]
        
        # 文本搜索
        if search_text:
            search_lower = search_text.lower()
            filtered = [msg for msg in filtered 
                       if search_lower in msg.content.lower() or 
                          search_lower in msg.source.lower()]
        
        return filtered
    
    def clear(self) -> None:
        """清空缓冲区"""
        self.messages.clear()
        self.logger.info("Info buffer cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓冲区统计信息"""
        stats = {
            "total": len(self.messages),
            "by_type": {},
            "by_level": {}
        }
        
        for msg in self.messages:
            # 按类型统计
            type_name = msg.info_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            # 按级别统计
            level_name = msg.level.value
            stats["by_level"][level_name] = stats["by_level"].get(level_name, 0) + 1
        
        return stats


class InfoDisplay(Widget):
    """单条信息显示组件"""
    
    DEFAULT_CSS = """
    InfoDisplay {
        height: auto;
        width: 1fr;
        padding: 0 1;
        margin: 0;
    }
    
    InfoDisplay Label {
        width: 1fr;
        height: auto;
    }
    
    InfoDisplay.error {
        background: rgba(255, 0, 0, 0.1);
        border-left: thick red;
    }
    
    InfoDisplay.warning {
        background: rgba(255, 255, 0, 0.1);
        border-left: thick yellow;
    }
    
    InfoDisplay.info {
        border-left: thick blue;
    }
    
    InfoDisplay.debug {
        opacity: 0.7;
        border-left: thick gray;
    }
    
    InfoDisplay.stock-data {
        background: rgba(0, 255, 0, 0.05);
        border-left: thick green;
    }
    
    InfoDisplay.trade-info {
        background: rgba(255, 215, 0, 0.1);
        border-left: thick gold;
    }
    """
    
    def __init__(self, message: InfoMessage, **kwargs):
        """初始化信息显示组件"""
        super().__init__(**kwargs)
        self.message = message
        
        # 设置CSS类
        self.add_class(message.level.value)
        self.add_class(message.info_type.value.replace("_", "-"))
    
    def compose(self) -> ComposeResult:
        """组合组件"""
        # 处理JSON数据
        if self.message.data and self.message.info_type == InfoType.STOCK_DATA:
            try:
                yield Static(JSON.from_data(self.message.data), expand=True)
                return
            except Exception:
                pass
        
        # 处理多行文本
        if isinstance(self.message.formatted_text, Text):
            yield Label(self.message.formatted_text)
        else:
            yield Label(self.message.content)


class InfoFilterBar(Horizontal):
    """信息过滤工具栏"""
    
    DEFAULT_CSS = """
    InfoFilterBar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
        border-bottom: solid $border;
    }
    
    InfoFilterBar Input {
        width: 1fr;
        margin-right: 1;
    }
    
    InfoFilterBar Select {
        width: 15;
        margin-right: 1;
    }
    
    InfoFilterBar Button {
        width: 8;
        margin-right: 1;
    }
    
    InfoFilterBar #ai_button {
        width: 8;
        margin-right: 1;
        background: $primary;
        color: $text;
    }
    
    InfoFilterBar #ai_button:hover {
        background: $primary-lighten-2;
    }
    """
    
    class FilterChanged(Message):
        """过滤条件改变消息"""
        def __init__(self, filters: Dict[str, Any]):
            super().__init__()
            self.filters = filters
    
    def __init__(self, **kwargs):
        """初始化过滤工具栏"""
        super().__init__(**kwargs)
        self.current_filters = {}
    
    def compose(self) -> ComposeResult:
        """组合过滤工具栏"""
        # 搜索输入框
        yield Input(placeholder="搜索信息...", id="search_input")
        
        # AI交互按钮
        if AI_MODULES_AVAILABLE:
            yield Button("💻 AI", id="ai_button", variant="primary")
        
        # 类型选择器
        type_options = [("全部", "all")] + [(t.value, t.value) for t in InfoType]
        yield Select(type_options, value="all", id="type_select")
        
        # 级别选择器
        level_options = [("全部", "all")] + [(l.value, l.value) for l in InfoLevel]
        yield Select(level_options, value="all", id="level_select")
        
        # 清空按钮
        yield Button("清空", id="clear_button")
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """搜索框内容改变"""
        if event.input.id == "search_input":
            self.current_filters["search"] = event.value
            self.post_message(self.FilterChanged(self.current_filters))
    
    async def on_select_changed(self, event: Select.Changed) -> None:
        """选择器改变"""
        if event.select.id == "type_select":
            self.current_filters["type"] = event.value if event.value != "all" else None
        elif event.select.id == "level_select":
            self.current_filters["level"] = event.value if event.value != "all" else None
        
        self.post_message(self.FilterChanged(self.current_filters))
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击"""
        if event.button.id == "clear_button":
            self.current_filters["clear"] = True
            self.post_message(self.FilterChanged(self.current_filters))
        elif event.button.id == "ai_button":
            await self._handle_ai_interaction()
    
    async def _handle_ai_interaction(self) -> None:
        """处理AI交互"""
        if not AI_MODULES_AVAILABLE:
            # 如果AI模块不可用，发送错误消息
            self.current_filters["ai_error"] = "AI功能不可用，请检查相关模块安装。"
            self.post_message(self.FilterChanged(self.current_filters))
            return
        
        # 发送AI交互请求，由InfoPanel处理具体的对话框显示和AI调用
        self.current_filters["show_ai_dialog"] = True
        self.post_message(self.FilterChanged(self.current_filters))


class InfoPanel(ScrollableContainer):
    """专业信息面板组件"""
    
    DEFAULT_CSS = """
    InfoPanel {
        background: $panel;
        overflow-y: auto;
        overflow-x: hidden;
        border: solid $border;
        border-title-color: $text;
        border-title-background: $surface;
        scrollbar-gutter: stable;
    }
    
    InfoPanel:focus {
        border: heavy $accent;
    }
    
    InfoPanel .info-container {
        layout: vertical;
        height: auto;
        width: 1fr;
    }
    
    InfoPanel .stats-bar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        text-align: center;
    }
    """
    
    # 响应式属性
    auto_scroll = reactive(True)
    max_display_count = reactive(500)
    
    class InfoAdded(Message):
        """信息添加消息"""
        def __init__(self, message: InfoMessage):
            super().__init__()
            self.message = message
    
    class AIRequestMessage(Message):
        """AI请求消息"""
        def __init__(self, user_input: str):
            super().__init__()
            self.user_input = user_input
    
    def __init__(self, title: str = "信息输出", **kwargs):
        """初始化信息面板"""
        super().__init__(**kwargs)
        self.border_title = title
        
        # 初始化组件
        self.buffer = InfoBuffer()
        self.logger = logger.get_logger("info_panel")
        self.current_filters = {}
        self.display_widgets: List[InfoDisplay] = []
        
        # 与项目logger系统集成
        self._setup_logger_handler()
    
    @property
    def _app_instance(self):
        """获取app实例，兼容测试环境"""
        return getattr(self, '_app', None) or self.app
    
    def _setup_logger_handler(self) -> None:
        """设置logger处理器，自动捕获项目日志"""
        # 这里可以添加自定义的logging handler来捕获系统日志
        pass
    
    def compose(self) -> ComposeResult:
        """组合信息面板"""
        # 过滤工具栏
        yield InfoFilterBar(id="filter_bar")
        
        # 信息显示容器
        with Vertical(classes="info-container", id="info_container"):
            pass
        
        # 统计信息栏
        yield Static("就绪", classes="stats-bar", id="stats_bar")
    
    async def on_info_filter_bar_filter_changed(self, event: InfoFilterBar.FilterChanged) -> None:
        """处理过滤条件改变"""
        self.current_filters = event.filters
        
        if "clear" in event.filters:
            await self.clear_all()
            return
        
        # 处理AI错误信息
        if "ai_error" in event.filters:
            await self.add_info(
                content=event.filters["ai_error"],
                info_type=InfoType.ERROR,
                level=InfoLevel.ERROR,
                source="AI助手"
            )
            return
        
        # 处理显示AI对话框请求
        if "show_ai_dialog" in event.filters:
            await self._show_ai_dialog()
            return
        
        await self.refresh_display()
    
    async def add_info(self, 
                      content: str,
                      info_type: InfoType,
                      level: InfoLevel = InfoLevel.INFO,
                      source: str = "",
                      data: Optional[Dict[str, Any]] = None) -> None:
        """
        添加信息
        
        Args:
            content: 信息内容
            info_type: 信息类型
            level: 信息级别
            source: 信息源
            data: 附加数据
        """
        message = InfoMessage(
            content=content,
            info_type=info_type,
            level=level,
            timestamp=datetime.now(),
            source=source,
            data=data
        )
        
        self.buffer.add_message(message)
        await self.refresh_display()
        
        # 发送消息，处理测试环境
        try:
            await self.post_message(self.InfoAdded(message))
        except (AttributeError, TypeError):
            # 在测试环境中可能没有post_message方法
            pass
    
    async def refresh_display(self) -> None:
        """刷新显示"""
        # 获取过滤后的消息
        filtered_messages = self._get_filtered_messages()
        
        # 限制显示数量，只显示最新的消息
        display_messages = filtered_messages[-self.max_display_count:]
        
        # 批量更新
        with self._app_instance.batch_update():
            # 清空现有显示
            container = self.query_one("#info_container")
            await container.query(InfoDisplay).remove()
            
            # 添加新的显示组件
            for message in display_messages:
                info_display = InfoDisplay(message)
                await container.mount(info_display)
        
        # 更新统计信息
        await self._update_stats()
        
        # 自动滚动到底部
        if self.auto_scroll:
            self.scroll_end(animate=False)
    
    def _get_filtered_messages(self) -> List[InfoMessage]:
        """获取过滤后的消息"""
        # 转换过滤条件
        info_types = None
        if self.current_filters.get("type"):
            try:
                info_types = [InfoType(self.current_filters["type"])]
            except ValueError:
                pass
        
        levels = None
        if self.current_filters.get("level"):
            try:
                levels = [InfoLevel(self.current_filters["level"])]
            except ValueError:
                pass
        
        search_text = self.current_filters.get("search")
        
        return self.buffer.get_filtered_messages(
            info_types=info_types,
            levels=levels,
            search_text=search_text
        )
    
    async def _update_stats(self) -> None:
        """更新统计信息"""
        stats = self.buffer.get_stats()
        filtered_count = len(self._get_filtered_messages())
        
        stats_text = f"总计: {stats['total']} | 显示: {filtered_count}"
        
        # 添加错误和警告计数
        if "error" in stats["by_level"]:
            stats_text += f" | 错误: {stats['by_level']['error']}"
        if "warning" in stats["by_level"]:
            stats_text += f" | 警告: {stats['by_level']['warning']}"
        
        stats_bar = self.query_one("#stats_bar")
        stats_bar.update(stats_text)
    
    async def clear_all(self) -> None:
        """清空所有信息"""
        self.buffer.clear()
        
        with self._app_instance.batch_update():
            container = self.query_one("#info_container")
            await container.query(InfoDisplay).remove()
        
        await self._update_stats()
        self.logger.info("Info panel cleared")
    
    # 便捷方法
    async def log_debug(self, content: str, source: str = "") -> None:
        """添加调试日志"""
        await self.add_info(content, InfoType.LOG, InfoLevel.DEBUG, source)
    
    async def log_info(self, content: str, source: str = "") -> None:
        """添加信息日志"""
        await self.add_info(content, InfoType.LOG, InfoLevel.INFO, source)
    
    async def log_warning(self, content: str, source: str = "") -> None:
        """添加警告日志"""
        await self.add_info(content, InfoType.LOG, InfoLevel.WARNING, source)
    
    async def log_error(self, content: str, source: str = "") -> None:
        """添加错误日志"""
        await self.add_info(content, InfoType.LOG, InfoLevel.ERROR, source)
    
    async def add_stock_data(self, content: str, data: Dict[str, Any], source: str = "") -> None:
        """添加股票数据"""
        await self.add_info(content, InfoType.STOCK_DATA, InfoLevel.INFO, source, data)
    
    async def add_trade_info(self, content: str, data: Dict[str, Any] = None, source: str = "") -> None:
        """添加交易信息"""
        await self.add_info(content, InfoType.TRADE_INFO, InfoLevel.INFO, source, data)
    
    async def add_performance_info(self, content: str, data: Dict[str, Any] = None, source: str = "") -> None:
        """添加性能信息"""
        await self.add_info(content, InfoType.PERFORMANCE, InfoLevel.INFO, source, data)
    
    async def _show_ai_dialog(self) -> None:
        """显示AI对话框并处理用户交互"""
        if not AI_MODULES_AVAILABLE:
            await self.add_info(
                content="AI功能不可用，请检查相关模块安装。",
                info_type=InfoType.ERROR,
                level=InfoLevel.ERROR,
                source="AI助手"
            )
            return
        
        def handle_submit(value: str):
            """处理提交回调"""
            # 添加调试日志
            self.logger.info(f"AI对话框提交回调被触发，用户输入: {value}")
            
            if value and value.strip():
                # 直接调用处理方法而不是发送消息
                self.logger.debug(f"[DEBUG] 直接调用_process_ai_request: {value.strip()}")
                import asyncio
                # 创建异步任务来处理AI请求
                asyncio.create_task(self._process_ai_request(value.strip()))
        
        def handle_cancel():
            """处理取消回调"""
            # 记录取消操作，使用简单的同步方式
            pass
        
        try:
            # 创建AI输入对话框，使用回调方式
            ai_dialog = WindowInputDialog(
                message="请输入您想要咨询的问题:",
                title="💻 AI 智能助手",
                placeholder="例如: 请分析一下腾讯这只股票的投资价值...",
                submit_text="提交",
                cancel_text="取消",
                dialog_id="ai_input_dialog",
                submit_callback=handle_submit,
                cancel_callback=handle_cancel
            )
            
            # 使用push_screen而不是push_screen_wait
            self.app.push_screen(ai_dialog)
            
        except Exception as e:
            self.logger.error(f"显示AI对话框失败: {e}")
            await self.add_info(
                content=f"AI对话框显示失败: {str(e)}",
                info_type=InfoType.ERROR,
                level=InfoLevel.ERROR,
                source="AI助手"
            )
    
    async def on_ai_request_message(self, message: AIRequestMessage) -> None:
        """处理AI请求消息"""
        self.logger.info(f"收到AI请求消息: {message.user_input}")
        # 直接调用处理方法
        await self._process_ai_request(message.user_input)
    
    async def _process_ai_request(self, user_input: str) -> None:
        """处理AI请求并显示响应"""
        self.logger.info(f"开始处理AI请求: {user_input}")
        
        if not user_input.strip():
            self.logger.debug(f"[DEBUG] 用户输入为空，返回")
            return
        
        try:
            # 显示用户问题
            await self.add_info(
                content=f"用户提问: {user_input}",
                info_type=InfoType.USER_ACTION,
                level=InfoLevel.INFO,
                source="用户"
            )
            
            # 显示正在思考的提示
            await self.add_info(
                content="🤔 AI正在思考中...",
                info_type=InfoType.LOG,
                level=InfoLevel.INFO,
                source="AI助手"
            )
            
            # 创建AI客户端并获取响应
            ai_client = await create_claude_client()
            if not ai_client.is_available():
                await self.add_info(
                    content="AI服务暂不可用，请稍后重试。",
                    info_type=InfoType.ERROR,
                    level=InfoLevel.ERROR,
                    source="AI助手"
                )
                return
            
            # 调用AI进行对话
            ai_response = await ai_client.chat_with_ai(user_input)
            
            # 显示AI回复
            await self.add_info(
                content=f"🤖 AI回复:\n{ai_response}",
                info_type=InfoType.LOG,
                level=InfoLevel.INFO,
                source="AI助手"
            )
            
        except Exception as e:
            self.logger.error(f"处理AI请求失败: {e}")
            await self.add_info(
                content=f"AI处理失败: {str(e)}",
                info_type=InfoType.ERROR,
                level=InfoLevel.ERROR,
                source="AI助手"
            )


# 向后兼容的类名
LinePanel = InfoPanel
LineDisplay = InfoDisplay