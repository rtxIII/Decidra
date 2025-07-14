from dataclasses import dataclass
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical, Center


class ConfirmDialog(Widget, can_focus_children=True):
    """确认对话框组件
    
    用于显示确认信息并等待用户确认或取消的对话框
    """
    
    DEFAULT_CSS = """
    ConfirmDialog {
        layout: vertical;
        dock: top; 
        padding: 2;                       
        width: 60%;
        height: auto;
        max-height: 50%;
        display: none;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        margin: 2 10;
        
        &.visible {
            display: block;
        }
        
        .message-content {
            height: auto;
            text-align: center;
            padding: 1 2;
            color: $text;
        }
        
        .button-container {
            layout: horizontal;
            height: auto;
            margin-top: 1;
        }
        
        .button-container Button {
            margin: 0 1;
            min-width: 12;
        }
        
        Button.-confirm {
            background: $success;
            color: $text;
        }
        
        Button.-cancel {
            background: $error;
            color: $text;
        }
    }    
    """

    DEFAULT_CLASSES = "float"
    BORDER_TITLE = "确认"

    # 键盘绑定
    BINDINGS = [
        Binding("enter", "confirm", "确认", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
        Binding("y", "confirm", "确认"),
        Binding("n", "cancel", "取消"),
    ]

    @dataclass
    class Confirm(Message):
        """确认消息"""
        confirmed: bool = True

    class Cancel(Message):
        """取消消息"""
        pass

    def __init__(self, message: str, title: Optional[str] = None, 
                 confirm_text: str = "确认", cancel_text: str = "取消") -> None:
        """初始化确认对话框
        
        Args:
            message: 要显示的确认信息
            title: 对话框标题，默认为"确认"
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
        """
        super().__init__()
        
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self._dialog_title = title

    def compose(self) -> ComposeResult:
        """构建确认对话框UI"""
        # 消息显示区域
        yield Static(self.message, classes="message-content")
        
        # 按钮容器 - 使用Center容器确保居中
        with Center():
            with Horizontal(classes="button-container"):
                yield Button(self.confirm_text, variant="success", id="confirm-btn")
                yield Button(self.cancel_text, variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        """组件挂载时的初始化"""
        # 设置标题
        if self._dialog_title:
            self.border_title = self._dialog_title
        
        # 自动聚焦到确认按钮
        try:
            confirm_btn = self.query_one("#confirm-btn", Button)
            confirm_btn.focus()
        except Exception:
            pass

    @on(Button.Pressed, "#confirm-btn")
    def on_confirm_pressed(self, event: Button.Pressed) -> None:
        """处理确认按钮点击"""
        event.stop()
        self.action_confirm()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        """处理取消按钮点击"""
        event.stop()
        self.action_cancel()

    def action_confirm(self) -> None:
        """确认操作"""
        self.post_message(self.Confirm(confirmed=True))

    def action_cancel(self) -> None:
        """取消操作"""
        self.post_message(self.Cancel())

    def allow_focus_children(self) -> bool:
        """只有在可见时才允许子组件获得焦点"""
        return self.has_class("visible")

    def show(self) -> None:
        """显示对话框"""
        self.add_class("visible")
        # 聚焦到确认按钮
        try:
            confirm_btn = self.query_one("#confirm-btn", Button)
            confirm_btn.focus()
        except Exception:
            pass

    def hide(self) -> None:
        """隐藏对话框"""
        self.remove_class("visible")