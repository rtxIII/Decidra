#!/usr/bin/env python3
"""
窗口化确认对话框组件
基于textual-window设计模式的确认对话框
"""

from dataclasses import dataclass
from typing import Optional, Callable

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical, Center


class WindowConfirmDialog(ModalScreen):
    """窗口化确认对话框
    
    基于ModalScreen实现的窗口式确认对话框，提供更好的用户体验
    """
    
    DEFAULT_CSS = """
    WindowConfirmDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    
    .dialog-window {
        width: 50;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        border-title-background: $primary;
        border-title-style: bold;
        padding: 1 2;
        margin: 2;
    }
    
    .dialog-content {
        layout: vertical;
        height: auto;
    }
    
    .message-content {
        height: auto;
        text-align: center;
        padding: 1 0;
        color: $text;
        margin-bottom: 1;
    }
    
    .button-row {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    
    .confirm-button {
        background: $success;
        color: $text;
    }
    
    .cancel-button {
        background: $error;
        color: $text;
    }
    
    .dialog-window:focus-within {
        border: thick $accent;
    }
    """
    
    # 键盘绑定
    BINDINGS = [
        Binding("enter", "confirm", "确认", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
        Binding("y", "confirm", "确认"),
        Binding("n", "cancel", "取消"),
        Binding("ctrl+c", "cancel", "取消"),
    ]

    @dataclass
    class Result(Message):
        """对话框结果消息"""
        confirmed: bool
        dialog_id: Optional[str] = None

    def __init__(
        self, 
        message: str, 
        title: Optional[str] = None,
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        dialog_id: Optional[str] = None,
        confirm_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None
    ) -> None:
        """初始化窗口化确认对话框
        
        Args:
            message: 要显示的确认信息
            title: 对话框标题，默认为"确认"
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            dialog_id: 对话框唯一标识
            confirm_callback: 确认回调函数
            cancel_callback: 取消回调函数
        """
        super().__init__()
        
        self.message = message
        self.title = title or "确认"
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.dialog_id = dialog_id
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback

    def compose(self) -> ComposeResult:
        """构建窗口化确认对话框UI"""
        with Vertical(classes="dialog-window") as dialog_window:
            dialog_window.border_title = self.title
            
            with Vertical(classes="dialog-content"):
                # 消息显示区域
                yield Static(self.message, classes="message-content")
                
                # 按钮行
                with Center():
                    with Horizontal(classes="button-row"):
                        yield Button(
                            self.confirm_text, 
                            variant="success", 
                            classes="confirm-button",
                            id="confirm-btn"
                        )
                        yield Button(
                            self.cancel_text, 
                            variant="error", 
                            classes="cancel-button",
                            id="cancel-btn"
                        )

    def on_mount(self) -> None:
        """组件挂载时自动聚焦到确认按钮"""
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
        # 执行回调函数
        if self.confirm_callback:
            try:
                self.confirm_callback()
            except Exception as e:
                # 安全地记录错误，如果没有app则跳过
                try:
                    self.app.log.error(f"确认回调执行失败: {e}")
                except:
                    # 在测试环境或没有app的情况下，忽略日志错误
                    pass
        
        # 发送结果消息
        self.post_message(self.Result(confirmed=True, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(True)

    def action_cancel(self) -> None:
        """取消操作"""
        # 执行回调函数
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                # 安全地记录错误，如果没有app则跳过
                try:
                    self.app.log.error(f"取消回调执行失败: {e}")
                except:
                    # 在测试环境或没有app的情况下，忽略日志错误
                    pass
        
        # 发送结果消息
        self.post_message(self.Result(confirmed=False, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(False)


# 便利函数，用于快速创建和显示确认对话框
async def show_confirm_dialog(
    app,
    message: str,
    title: Optional[str] = None,
    confirm_text: str = "确认",
    cancel_text: str = "取消",
    dialog_id: Optional[str] = None,
    confirm_callback: Optional[Callable] = None,
    cancel_callback: Optional[Callable] = None
) -> bool:
    """显示确认对话框并等待用户响应
    
    Args:
        app: Textual应用实例
        message: 确认消息
        title: 对话框标题
        confirm_text: 确认按钮文本
        cancel_text: 取消按钮文本
        dialog_id: 对话框ID
        confirm_callback: 确认回调
        cancel_callback: 取消回调
        
    Returns:
        bool: True表示用户确认，False表示用户取消
    """
    dialog = WindowConfirmDialog(
        message=message,
        title=title,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        dialog_id=dialog_id,
        confirm_callback=confirm_callback,
        cancel_callback=cancel_callback
    )
    
    result = await app.push_screen_wait(dialog)
    return bool(result)


# 预定义的常用对话框
class CommonDialogs:
    """常用对话框集合"""
    
    @staticmethod
    async def confirm_delete(app, item_name: str = "此项目") -> bool:
        """删除确认对话框"""
        return await show_confirm_dialog(
            app,
            message=f"确定要删除 {item_name} 吗？\n\n[red]警告：此操作不可撤销！[/red]",
            title="删除确认",
            confirm_text="删除",
            cancel_text="取消"
        )
    
    @staticmethod
    async def confirm_save(app, changes_desc: str = "当前更改") -> bool:
        """保存确认对话框"""
        return await show_confirm_dialog(
            app,
            message=f"确定要保存 {changes_desc} 吗？\n\n所有修改将被永久保存。",
            title="保存确认",
            confirm_text="保存",
            cancel_text="取消"
        )
    
    @staticmethod
    async def confirm_exit(app) -> bool:
        """退出确认对话框"""
        return await show_confirm_dialog(
            app,
            message="确定要退出应用程序吗？\n\n未保存的更改将丢失。",
            title="退出确认",
            confirm_text="退出",
            cancel_text="继续使用"
        )
    
    @staticmethod
    async def confirm_action(app, action_name: str, description: str = "") -> bool:
        """通用操作确认对话框"""
        message = f"确定要执行 {action_name} 吗？"
        if description:
            message += f"\n\n{description}"
            
        return await show_confirm_dialog(
            app,
            message=message,
            title="操作确认",
            confirm_text="执行",
            cancel_text="取消"
        ) 