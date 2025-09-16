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
    from monitor.widgets.thinking_animation import ThinkingAnimation
    AI_MODULES_AVAILABLE = True
except ImportError:
    create_claude_client = None
    WindowInputDialog = None
    ThinkingAnimation = None
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
        border-left: thick $error;
    }
    
    InfoDisplay.warning {
        background: rgba(255, 255, 0, 0.1);
        border-left: thick $warning;
    }
    
    InfoDisplay.info {
        border-left: thick $primary;
    }
    
    InfoDisplay.debug {
        opacity: 0.7;
        border-left: thick $text-muted;
    }
    
    InfoDisplay.stock-data {
        background: rgba(0, 255, 0, 0.05);
        border-left: thick $success;
    }
    
    InfoDisplay.trade-info {
        background: rgba(255, 215, 0, 0.1);
        border-left: thick $secondary;
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


class InfoPanel(Widget):
    """专业信息面板组件 - 参考toolong双面板设计"""

    DEFAULT_CSS = """
    InfoPanel {
        layout: horizontal;
        background: $panel;
        border: solid $border;
        border-title-color: $text;
        border-title-background: $surface;
        height: 1fr;
        width: 1fr;
    }

    InfoPanel:focus {
        border: heavy $accent;
    }

    InfoPanel .left-panel {
        width: 1fr;  /* 50% */
        height: 1fr;
        background: $surface;
        border-right: solid $border;
    }

    InfoPanel .right-panel {
        width: 1fr;  /* 50% */
        height: 1fr;
        background: $panel;
    }

    InfoPanel .panel-title {
        height: 1;
        dock: top;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
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
        
        # 新增AI建议管理器
        self.ai_display_widget = None
        self.ai_suggestions = []  # AI建议缓存
        self.thinking_animation = None  # 思考动画组件
        
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
    
    async def on_mount(self) -> None:
        """组件挂载时初始化"""
        # 重构后的InfoPanel不再包含AI显示组件
        # AI功能已移至独立的AIDisplayWidget组件中
        self.ai_display_widget = None
        self.logger.info("InfoPanel双面板组件初始化完成")
    
    def compose(self) -> ComposeResult:
        """组合信息面板 - 左右分栏设计"""
        # 左侧面板 - 信息选择区域 (50%)
        with Vertical(classes="left-panel", id="left_panel"):
            yield Static("📋 信息列表", classes="panel-title")
            yield InfoFilterBar(id="filter_bar")
            yield InfoMessageList(id="info_message_list", buffer=self.buffer)
            yield Static("就绪", classes="stats-bar", id="stats_bar")

        # 右侧面板 - 详细信息显示区域 (50%)
        with Vertical(classes="right-panel", id="right_panel"):
            yield Static("📄 详细信息", classes="panel-title")
            yield InfoDetailView(id="info_detail_view")
    
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
            self.post_message(self.InfoAdded(message))
        except (AttributeError, TypeError):
            # 在测试环境中可能没有post_message方法
            pass
    
    async def refresh_display(self) -> None:
        """刷新显示 - 适配双面板设计"""
        try:
            # 获取过滤后的消息
            filtered_messages = self._get_filtered_messages()

            # 刷新左侧消息列表
            message_list = self.query_one("#info_message_list", InfoMessageList)
            await message_list.refresh_messages(filtered_messages)

            # 更新统计信息
            await self._update_stats()

        except Exception as e:
            self.logger.error(f"刷新显示失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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
        try:
            self.buffer.clear()

            # 清空左侧消息列表
            message_list = self.query_one("#info_message_list", InfoMessageList)
            await message_list.refresh_messages([])

            # 重置右侧详情视图
            detail_view = self.query_one("#info_detail_view", InfoDetailView)
            await detail_view.query("*").remove()
            await detail_view.mount(Static("选择左侧消息查看详细信息", classes="detail-content", id="empty_detail"))

            await self._update_stats()
            self.logger.info("Info panel cleared")
        except Exception as e:
            self.logger.error(f"清空信息面板失败: {e}")

    async def on_info_message_list_message_selected(self, event: InfoMessageList.MessageSelected) -> None:
        """处理消息选择事件"""
        try:
            # 获取右侧详情视图组件
            detail_view = self.query_one("#info_detail_view", InfoDetailView)
            # 更新详情显示
            await detail_view.update_detail(event.message)
            self.logger.info(f"选择消息并更新详情: {event.message.content[:50]}...")
        except Exception as e:
            self.logger.error(f"处理消息选择事件失败: {e}")
    
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
            
            # 显示思考动画
            await self._start_thinking_animation()
            
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
            
            # 停止思考动画
            await self._stop_thinking_animation()
            
            # 显示AI回复
            await self.add_info(
                content=f"🤖 AI回复:\n{ai_response}",
                info_type=InfoType.LOG,
                level=InfoLevel.INFO,
                source="AI助手"
            )
            
            
        except Exception as e:
            # 确保停止动画
            await self._stop_thinking_animation()
            
            self.logger.error(f"处理AI请求失败: {e}")
            await self.add_info(
                content=f"AI处理失败: {str(e)}",
                info_type=InfoType.ERROR,
                level=InfoLevel.ERROR,
                source="AI助手"
            )
    
    def _extract_stock_code(self, user_input: str) -> str:
        """从用户输入中提取股票代码"""
        import re
        
        # 匹配常见的股票代码格式
        patterns = [
            r'([A-Z]{2}\.[0-9]{5})',  # HK.00700
            r'([A-Z]{2}\.[A-Z]{3,4})',  # US.AAPL
            r'([SH|SZ]\.[0-9]{6})',  # SH.600000, SZ.000001
            r'([0-9]{6})',  # 000001, 600000
            r'([A-Z]{3,4})'  # AAPL
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.upper())
            if match:
                return match.group(1)
        
        return ""
    
    # AI建议事件处理方法 - 为兼容性保留
    async def on_ai_display_widget_suggestion_accepted(self, event) -> None:
        """处理AI建议被接受事件 - 兼容性方法"""
        try:
            suggestion_id = getattr(event, 'suggestion_id', 'unknown')
            await self.add_info(
                content=f"✅ AI建议已接受: {suggestion_id[:8]}...",
                info_type=InfoType.USER_ACTION,
                level=InfoLevel.INFO,
                source="用户操作"
            )
            self.logger.info(f"用户接受了AI建议: {suggestion_id}")
        except Exception as e:
            self.logger.debug(f"AI建议接受事件处理失败（重构后正常）: {e}")

    async def on_ai_display_widget_suggestion_ignored(self, event) -> None:
        """处理AI建议被忽略事件 - 兼容性方法"""
        try:
            suggestion_id = getattr(event, 'suggestion_id', 'unknown')
            await self.add_info(
                content=f"❌ AI建议已忽略: {suggestion_id[:8]}...",
                info_type=InfoType.USER_ACTION,
                level=InfoLevel.INFO,
                source="用户操作"
            )
            self.logger.info(f"用户忽略了AI建议: {suggestion_id}")
        except Exception as e:
            self.logger.debug(f"AI建议忽略事件处理失败（重构后正常）: {e}")

    async def on_ai_display_widget_suggestion_saved(self, event) -> None:
        """处理AI建议被保存事件 - 兼容性方法"""
        try:
            suggestion_id = getattr(event, 'suggestion_id', 'unknown')
            await self.add_info(
                content=f"💾 AI建议已保存: {suggestion_id[:8]}...",
                info_type=InfoType.USER_ACTION,
                level=InfoLevel.INFO,
                source="用户操作"
            )
            self.logger.info(f"用户保存了AI建议: {suggestion_id}")
        except Exception as e:
            self.logger.debug(f"AI建议保存事件处理失败（重构后正常）: {e}")
    
    async def _start_thinking_animation(self) -> None:
        """启动思考动画"""
        try:
            if not AI_MODULES_AVAILABLE or ThinkingAnimation is None:
                # 如果动画组件不可用，使用静态文本
                await self.add_info(
                    content="🤔 AI正在思考中...",
                    info_type=InfoType.LOG,
                    level=InfoLevel.INFO,
                    source="AI助手"
                )
                return
            
            # 创建思考动画组件
            self.thinking_animation = ThinkingAnimation()
            self.thinking_animation.add_class("log")  # 添加日志样式类
            self.thinking_animation.add_class("info")  # 添加信息级别样式类
            
            # 适配新的双面板结构 - 将动画挂载到消息列表
            try:
                # 尝试新的结构
                container = self.query_one("#info_message_list")
                await container.mount(self.thinking_animation)
            except Exception:
                # 兼容旧结构或降级处理
                self.logger.warning("无法找到消息容器，使用静态文本代替动画")
                await self.add_info(
                    content="🤔 AI正在思考中...",
                    info_type=InfoType.LOG,
                    level=InfoLevel.INFO,
                    source="AI助手"
                )
                return
            
            # 启动动画
            await self.thinking_animation.start_animation()
            
            # 自动滚动到底部
            if self.auto_scroll:
                self.scroll_end(animate=False)
                
        except Exception as e:
            self.logger.error(f"启动思考动画失败: {e}")
            # 降级到静态文本
            await self.add_info(
                content="🤔 AI正在思考中...",
                info_type=InfoType.LOG,
                level=InfoLevel.INFO,
                source="AI助手"
            )
    
    async def _stop_thinking_animation(self) -> None:
        """停止思考动画"""
        try:
            if self.thinking_animation:
                # 停止动画
                await self.thinking_animation.stop_animation()
                
                # 从界面中移除动画组件
                if self.thinking_animation.parent:
                    await self.thinking_animation.remove()
                
                self.thinking_animation = None
                
                self.logger.debug("思考动画已停止并清理")
                
        except Exception as e:
            self.logger.error(f"停止思考动画失败: {e}")


class MessageItem(Vertical):
    """单条消息组件"""

    def __init__(self, message: InfoMessage, **kwargs):
        message_id = f"msg_{id(message)}"
        super().__init__(id=message_id, classes=f"message-item {message.level.value}", **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        """组合消息组件"""
        # 消息头部
        time_str = self.message.timestamp.strftime("%H:%M:%S")
        type_str = self.message.info_type.value.upper()
        header_text = f"[{time_str}] {type_str}"
        if self.message.source:
            header_text += f" ({self.message.source})"

        yield Static(header_text, classes="message-header")

        # 消息内容（截断长消息）
        content = self.message.content
        if len(content) > 100:
            content = content[:97] + "..."

        yield Static(content, classes="message-content")


class InfoMessageList(ScrollableContainer):
    """信息消息列表组件 - 参考toolong的LogLines"""

    DEFAULT_CSS = """
    InfoMessageList {
        background: $surface;
        height: 1fr;
        width: 1fr;
        overflow-y: auto;
        scrollbar-gutter: stable;
        padding: 1;
    }

    InfoMessageList:focus {
        border: solid $accent;
    }

    InfoMessageList .message-item {
        height: auto;
        min-height: 3;
        width: 1fr;
        padding: 0 1;
        margin: 0;
        border: solid $border;
        background: $surface;
    }

    InfoMessageList .message-item:hover {
        background: $surface-lighten-1;
    }

    InfoMessageList .message-item.selected {
        background: $primary-darken-1;
        border: solid $accent;
    }

    InfoMessageList .message-item.error {
        border-left: solid $error;
    }

    InfoMessageList .message-item.warning {
        border-left: solid $warning;
    }

    InfoMessageList .message-item.info {
        border-left: solid $success;
    }

    InfoMessageList .message-item.debug {
        border-left: solid $panel;
        opacity: 0.8;
    }

    InfoMessageList .message-header {
        height: 1;
        text-style: bold;
    }

    InfoMessageList .message-content {
        height: 1;
        color: $text-muted;
        text-wrap: wrap;
    }
    """

    class MessageSelected(Message):
        """消息选择事件"""
        def __init__(self, message: InfoMessage):
            super().__init__()
            self.message = message

    def __init__(self, buffer: InfoBuffer, **kwargs):
        """初始化消息列表"""
        super().__init__(**kwargs)
        self.buffer = buffer
        self.selected_message: Optional[InfoMessage] = None
        self.message_widgets: Dict[str, Widget] = {}
        self.logger = logger.get_logger("info_message_list")

    def compose(self) -> ComposeResult:
        """组合消息列表"""
        with Vertical():
            yield Static("暂无消息", classes="empty-state", id="empty_state")

    async def refresh_messages(self, filtered_messages: List[InfoMessage]) -> None:
        """刷新消息列表"""
        try:
            # 清空现有消息组件
            await self.query(".message-item").remove()
            self.message_widgets.clear()

            empty_state = self.query_one("#empty_state")

            if filtered_messages:
                empty_state.display = False

                # 只显示最新的消息（限制数量避免性能问题）
                display_messages = filtered_messages[-100:]  # 最多显示100条

                for message in display_messages:
                    message_id = f"msg_{id(message)}"
                    message_widget = MessageItem(message)
                    self.message_widgets[message_id] = message_widget
                    await self.mount(message_widget)

                self.logger.debug(f"刷新消息列表: {len(display_messages)} 条消息")
            else:
                empty_state.display = True

            # 滚动到底部显示最新消息
            self.scroll_end(animate=True)

        except Exception as e:
            self.logger.error(f"刷新消息列表失败: {e}")


    async def on_click(self, event) -> None:
        """处理点击事件"""
        # 寻找被点击的消息项
        clicked_widget = event.widget
        while clicked_widget and not clicked_widget.classes or "message-item" not in clicked_widget.classes:
            clicked_widget = clicked_widget.parent
            if not clicked_widget:
                return

        # 找到对应的消息
        message_id = clicked_widget.id
        if message_id in self.message_widgets:
            widget = self.message_widgets[message_id]
            # 获取对应的消息对象
            for message in self.buffer.messages:
                if f"msg_{id(message)}" == message_id:
                    await self.select_message(message, widget)
                    break

    async def select_message(self, message: InfoMessage, widget: Widget) -> None:
        """选择消息"""
        # 更新选中状态
        if self.selected_message:
            # 移除之前选中项的选中样式
            for msg_widget in self.message_widgets.values():
                msg_widget.remove_class("selected")

        # 添加新选中项的样式
        widget.add_class("selected")
        self.selected_message = message

        # 发送选择事件
        self.post_message(self.MessageSelected(message))

        self.logger.info(f"选中消息: {message.content[:50]}...")


class InfoDetailView(ScrollableContainer):
    """信息详情视图组件 - 参考toolong的LinePanel"""

    DEFAULT_CSS = """
    InfoDetailView {
        background: $panel;
        height: 1fr;
        width: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    InfoDetailView:focus {
        border: solid $accent;
    }

    InfoDetailView .detail-header {
        height: auto;
        padding: 0 0 1 0;
        text-style: bold;
        border-bottom: solid $border;
        margin-bottom: 1;
    }

    InfoDetailView .detail-section {
        height: auto;
        padding: 1 0;
        margin: 1 0;
    }

    InfoDetailView .detail-content {
        height: auto;
        padding: 1;
        background: $surface;
        border: solid $border;
        margin: 1 0;
    }

    InfoDetailView .detail-metadata {
        height: auto;
        color: $text-muted;
        border-top: solid $border;
        padding: 1 0 0 0;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs):
        """初始化详情视图"""
        super().__init__(**kwargs)
        self.current_message: Optional[InfoMessage] = None
        self.logger = logger.get_logger("info_detail_view")

    def compose(self) -> ComposeResult:
        """组合详情视图"""
        with Vertical():
            yield Static("选择左侧消息查看详细信息", classes="detail-content", id="empty_detail")

    async def update_detail(self, message: InfoMessage) -> None:
        """更新详情显示"""
        try:
            self.current_message = message

            # 清空当前内容
            await self.query("*").remove()

            with self.app.batch_update():
                # 标题
                level_icon = self._get_level_icon(message.level)
                type_icon = self._get_type_icon(message.info_type)
                title = f"{level_icon} {type_icon} {message.info_type.value.upper()}"
                await self.mount(Static(title, classes="detail-header"))

                # 消息内容
                await self.mount(Static("消息内容:", classes="detail-section"))
                await self.mount(Static(message.content, classes="detail-content"))

                # 如果有附加数据，显示为JSON
                if message.data:
                    try:
                        await self.mount(Static("附加数据:", classes="detail-section"))
                        json_content = JSON.from_data(message.data)
                        await self.mount(Static(json_content, classes="detail-content"))
                    except Exception:
                        await self.mount(Static(f"数据: {str(message.data)}", classes="detail-content"))

                # 元数据
                metadata_text = self._format_metadata(message)
                await self.mount(Static(metadata_text, classes="detail-metadata"))

            self.logger.info(f"更新消息详情: {message.content[:50]}...")

        except Exception as e:
            self.logger.error(f"更新详情显示失败: {e}")

    def _get_level_icon(self, level: InfoLevel) -> str:
        """获取级别图标"""
        level_icons = {
            InfoLevel.DEBUG: "🔍",
            InfoLevel.INFO: "ℹ️",
            InfoLevel.WARNING: "⚠️",
            InfoLevel.ERROR: "❌",
            InfoLevel.CRITICAL: "🚨",
        }
        return level_icons.get(level, "•")

    def _get_type_icon(self, info_type: InfoType) -> str:
        """获取类型图标"""
        type_icons = {
            InfoType.LOG: "📝",
            InfoType.STOCK_DATA: "📈",
            InfoType.TRADE_INFO: "💰",
            InfoType.PERFORMANCE: "⚡",
            InfoType.API_STATUS: "🔗",
            InfoType.USER_ACTION: "👤",
            InfoType.ERROR: "❌",
            InfoType.WARNING: "⚠️",
        }
        return type_icons.get(info_type, "•")

    def _format_metadata(self, message: InfoMessage) -> str:
        """格式化元数据"""
        metadata = []

        # 基本信息
        metadata.append(f"消息ID: {id(message)}")
        metadata.append(f"消息类型: {message.info_type.value}")
        metadata.append(f"消息级别: {message.level.value}")
        metadata.append(f"时间戳: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

        if message.source:
            metadata.append(f"消息源: {message.source}")

        # 消息统计
        metadata.append(f"内容长度: {len(message.content)} 字符")

        if message.data:
            metadata.append(f"附加数据: {len(str(message.data))} 字符")

        return "\n".join(metadata)


# 向后兼容的类名
LinePanel = InfoPanel
LineDisplay = InfoDisplay