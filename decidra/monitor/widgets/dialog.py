from dataclasses import dataclass
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, Button, Input, TextArea
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
        
        Center {
            width: 100%;
            height: auto;
            margin-top: 1;
        }
        
        .button-container {
            layout: horizontal;
            height: auto;
            width: auto;
            align: center middle;
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


class InputDialog(Widget, can_focus_children=True):
    """输入对话框组件
    
    用于获取用户文本输入的对话框
    """
    
    DEFAULT_CSS = """
    InputDialog {
        layout: vertical;
        dock: top; 
        padding: 2;                       
        width: 80%;
        height: auto;
        max-height: 60%;
        display: none;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        margin: 2 10;
        
        &.visible {
            display: block;
        }
        
        .input-content {
            layout: vertical;
            height: auto;
            padding: 1 2;
        }
        
        .input-label {
            height: auto;
            text-align: left;
            padding: 0 0 1 0;
            color: $text;
        }
        
        .input-field {
            height: 8;
            width: 100%;
            border: solid $border;
            padding: 1;
        }
        
        Center {
            width: 100%;
            height: auto;
            margin-top: 1;
        }
        
        .button-container {
            layout: horizontal;
            height: auto;
            width: auto;
            align: center middle;
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
    BORDER_TITLE = "输入"

    # 键盘绑定
    BINDINGS = [
        Binding("ctrl+enter", "submit", "提交", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
    ]

    @dataclass
    class Submit(Message):
        """提交消息"""
        text: str = ""

    class Cancel(Message):
        """取消消息"""
        pass

    def __init__(self, prompt: str = "请输入内容:", title: Optional[str] = None, 
                 placeholder: str = "", multiline: bool = True) -> None:
        """初始化输入对话框
        
        Args:
            prompt: 提示信息
            title: 对话框标题，默认为"输入"
            placeholder: 输入框占位符
            multiline: 是否支持多行输入
        """
        super().__init__()
        
        self.prompt = prompt
        self.placeholder = placeholder
        self.multiline = multiline
        self._dialog_title = title
        self.input_text = ""

    def compose(self) -> ComposeResult:
        """构建输入对话框UI"""
        with Vertical(classes="input-content"):
            # 提示信息
            yield Static(self.prompt, classes="input-label")
            
            # 输入框 - 根据multiline选择TextArea或Input
            if self.multiline:
                yield TextArea(
                    classes="input-field", 
                    id="input-field"
                )
            else:
                yield Input(placeholder=self.placeholder,
                           classes="input-field", 
                           id="input-field")
        
        # 按钮容器
        with Center():
            with Horizontal(classes="button-container"):
                yield Button("提交", variant="success", id="submit-btn")
                yield Button("取消", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        """组件挂载时的初始化"""
        # 设置标题
        if self._dialog_title:
            self.border_title = self._dialog_title
        
        # 自动聚焦到输入框
        try:
            input_field = self.query_one("#input-field")
            
            # 如果是TextArea且有占位符文本，设置初始文本
            if self.multiline and hasattr(input_field, 'text') and self.placeholder:
                input_field.text = f"# {self.placeholder}\n\n"
            
            input_field.focus()
        except Exception:
            pass

    @on(Button.Pressed, "#submit-btn")
    def on_submit_pressed(self, event: Button.Pressed) -> None:
        """处理提交按钮点击"""
        event.stop()
        self.action_submit()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        """处理取消按钮点击"""
        event.stop()
        self.action_cancel()

    def action_submit(self) -> None:
        """提交操作"""
        try:
            input_field = self.query_one("#input-field")
            if self.multiline and hasattr(input_field, 'text'):
                text = input_field.text
                # 如果是TextArea，过滤掉占位符文本
                if text.startswith(f"# {self.placeholder}\n\n"):
                    text = text[len(f"# {self.placeholder}\n\n"):]
            elif hasattr(input_field, 'value'):
                text = input_field.value
            else:
                text = ""
            
            self.post_message(self.Submit(text=text.strip()))
        except Exception:
            self.post_message(self.Submit(text=""))

    def action_cancel(self) -> None:
        """取消操作"""
        self.post_message(self.Cancel())

    def allow_focus_children(self) -> bool:
        """只有在可见时才允许子组件获得焦点"""
        return self.has_class("visible")

    def show(self) -> None:
        """显示对话框"""
        self.add_class("visible")
        # 聚焦到输入框
        try:
            input_field = self.query_one("#input-field")
            input_field.focus()
        except Exception:
            pass

    def hide(self) -> None:
        """隐藏对话框"""
        self.remove_class("visible")


class AIInputDialog(InputDialog):
    """AI交互专用输入对话框"""
    
    DEFAULT_CLASSES = "float"
    BORDER_TITLE = "💬 AI 智能助手"

    def __init__(self, **kwargs):
        """初始化AI输入对话框"""
        super().__init__(
            prompt="请输入您想要咨询的问题:",
            title="💬 AI 智能助手",
            placeholder="例如: 请分析一下这只股票的投资价值...",
            multiline=True,
            **kwargs
        )