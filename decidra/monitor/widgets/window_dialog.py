#!/usr/bin/env python3
"""
窗口化确认对话框组件
基于textual-window设计模式的确认对话框
"""

from dataclasses import dataclass
from typing import Optional, Callable, Any, Union

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static, Button, Input
from textual.containers import Horizontal, Vertical, Center
from textual.validation import Function, ValidationResult, Validator


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


class WindowInputDialog(ModalScreen):
    """窗口化输入对话框
    
    基于ModalScreen实现的窗口式输入对话框，支持用户输入各种数据
    """
    
    DEFAULT_CSS = """
    WindowInputDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    
    .input-dialog-window {
        width: 60;
        height: auto;
        max-height: 25;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        border-title-background: $primary;
        border-title-style: bold;
        padding: 1 2;
        margin: 2;
    }
    
    .input-dialog-content {
        layout: vertical;
        height: auto;
    }
    
    .input-message-content {
        height: auto;
        text-align: left;
        padding: 1 0;
        color: $text;
        margin-bottom: 1;
    }
    
    .input-field {
        width: 100%;
        margin-bottom: 1;
        border: solid $primary;
    }
    
    .input-field:focus {
        border: solid $accent;
    }
    
    .error-message {
        height: auto;
        color: $error;
        text-align: left;
        padding: 0 0 1 0;
        display: none;
    }
    
    .error-message.visible {
        display: block;
    }
    
    .input-button-row {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    .input-button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    
    .input-dialog-window:focus-within {
        border: thick $accent;
    }
    """
    
    # 键盘绑定
    BINDINGS = [
        Binding("enter", "submit", "提交", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
        Binding("ctrl+c", "cancel", "取消"),
    ]

    @dataclass
    class InputResult(Message):
        """输入对话框结果消息"""
        submitted: bool
        value: Optional[str] = None
        dialog_id: Optional[str] = None

    def __init__(
        self, 
        message: str, 
        title: Optional[str] = None,
        placeholder: str = "",
        default_value: str = "",
        input_type: str = "text",
        password: bool = False,
        submit_text: str = "确认",
        cancel_text: str = "取消",
        dialog_id: Optional[str] = None,
        validator: Optional[Validator] = None,
        required: bool = True,
        submit_callback: Optional[Callable[[str], None]] = None,
        cancel_callback: Optional[Callable] = None
    ) -> None:
        """初始化窗口化输入对话框
        
        Args:
            message: 要显示的提示信息
            title: 对话框标题，默认为"输入"
            placeholder: 输入框占位符文本
            default_value: 默认输入值
            input_type: 输入类型 ("text", "number", "email" 等)
            password: 是否为密码输入
            submit_text: 提交按钮文本
            cancel_text: 取消按钮文本
            dialog_id: 对话框唯一标识
            validator: 输入验证器
            required: 是否必填
            submit_callback: 提交回调函数
            cancel_callback: 取消回调函数
        """
        super().__init__()
        
        self.message = message
        self.title = title or "输入"
        self.placeholder = placeholder
        self.default_value = default_value
        self.input_type = input_type
        self.password = password
        self.submit_text = submit_text
        self.cancel_text = cancel_text
        self.dialog_id = dialog_id
        self.validator = validator
        self.required = required
        self.submit_callback = submit_callback
        self.cancel_callback = cancel_callback
        
        self._input_widget: Optional[Input] = None
        self._error_widget: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """构建窗口化输入对话框UI"""
        with Vertical(classes="input-dialog-window") as dialog_window:
            dialog_window.border_title = self.title
            
            with Vertical(classes="input-dialog-content"):
                # 消息显示区域
                yield Static(self.message, classes="input-message-content")
                
                # 输入字段
                yield Input(
                    value=self.default_value,
                    placeholder=self.placeholder,
                    password=self.password,
                    validators=[self.validator] if self.validator else None,
                    classes="input-field",
                    id="input-field"
                )
                
                # 错误消息区域
                yield Static("", classes="error-message", id="error-message")
                
                # 按钮行
                with Center():
                    with Horizontal(classes="input-button-row"):
                        yield Button(
                            self.submit_text, 
                            variant="success", 
                            classes="confirm-button",
                            id="submit-btn"
                        )
                        yield Button(
                            self.cancel_text, 
                            variant="error", 
                            classes="cancel-button",
                            id="cancel-btn"
                        )

    def on_mount(self) -> None:
        """组件挂载时自动聚焦到输入框"""
        try:
            self._input_widget = self.query_one("#input-field", Input)
            self._error_widget = self.query_one("#error-message", Static)
            self._input_widget.focus()
        except Exception:
            pass

    @on(Input.Changed, "#input-field")
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入变化，实时验证"""
        self._clear_error()

    @on(Input.Submitted, "#input-field")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车提交"""
        event.stop()
        self.action_submit()

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

    def _validate_input(self) -> bool:
        """验证输入值"""
        if not self._input_widget:
            return False
            
        value = self._input_widget.value.strip()
        
        # 检查必填
        if self.required and not value:
            self._show_error("此字段为必填项")
            return False
        
        # 检查自定义验证器
        if self.validator and value:
            try:
                # 如果有验证器，手动验证
                if hasattr(self.validator, 'validate'):
                    result = self.validator.validate(value)
                    if not result.is_valid:
                        error_msg = "输入格式不正确"
                        if hasattr(result, 'failure_descriptions') and result.failure_descriptions:
                            error_msg = result.failure_descriptions[0]
                        self._show_error(error_msg)
                        return False
            except Exception as e:
                self._show_error(f"验证失败: {str(e)}")
                return False
        
        return True

    def _show_error(self, message: str) -> None:
        """显示错误消息"""
        if self._error_widget:
            self._error_widget.update(message)
            self._error_widget.add_class("visible")

    def _clear_error(self) -> None:
        """清除错误消息"""
        if self._error_widget:
            self._error_widget.remove_class("visible")
            self._error_widget.update("")

    def action_submit(self) -> None:
        """提交操作"""
        if not self._validate_input():
            return
            
        value = self._input_widget.value.strip() if self._input_widget else ""
        
        # 执行回调函数
        if self.submit_callback:
            try:
                self.submit_callback(value)
            except Exception as e:
                # 安全地记录错误，如果没有app则跳过
                try:
                    self.app.log.error(f"提交回调执行失败: {e}")
                except:
                    # 在测试环境或没有app的情况下，忽略日志错误
                    pass
        
        # 发送结果消息
        self.post_message(self.InputResult(submitted=True, value=value, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(value)

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
        self.post_message(self.InputResult(submitted=False, value=None, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(None)


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


# 便利函数，用于快速创建和显示输入对话框
async def show_input_dialog(
    app,
    message: str,
    title: Optional[str] = None,
    placeholder: str = "",
    default_value: str = "",
    input_type: str = "text",
    password: bool = False,
    submit_text: str = "确认",
    cancel_text: str = "取消",
    dialog_id: Optional[str] = None,
    validator: Optional[Validator] = None,
    required: bool = True,
    submit_callback: Optional[Callable[[str], None]] = None,
    cancel_callback: Optional[Callable] = None
) -> Optional[str]:
    """显示输入对话框并等待用户响应
    
    Args:
        app: Textual应用实例
        message: 提示消息
        title: 对话框标题
        placeholder: 输入框占位符
        default_value: 默认值
        input_type: 输入类型
        password: 是否为密码输入
        submit_text: 提交按钮文本
        cancel_text: 取消按钮文本
        dialog_id: 对话框ID
        validator: 验证器
        required: 是否必填
        submit_callback: 提交回调
        cancel_callback: 取消回调
        
    Returns:
        Optional[str]: 用户输入的值，如果取消则返回None
    """
    dialog = WindowInputDialog(
        message=message,
        title=title,
        placeholder=placeholder,
        default_value=default_value,
        input_type=input_type,
        password=password,
        submit_text=submit_text,
        cancel_text=cancel_text,
        dialog_id=dialog_id,
        validator=validator,
        required=required,
        submit_callback=submit_callback,
        cancel_callback=cancel_callback
    )
    
    result = await app.push_screen_wait(dialog)
    return result


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
    
    # 输入对话框
    @staticmethod
    async def input_text(app, prompt: str, title: str = "文本输入", **kwargs) -> Optional[str]:
        """文本输入对话框"""
        return await show_input_dialog(
            app,
            message=prompt,
            title=title,
            input_type="text",
            **kwargs
        )
    
    @staticmethod
    async def input_number(app, prompt: str, title: str = "数字输入", **kwargs) -> Optional[str]:
        """数字输入对话框"""
        # 简单的数字验证器
        def validate_number(value: str) -> ValidationResult:
            try:
                float(value)
                return ValidationResult.success()
            except ValueError:
                return ValidationResult.failure("请输入有效的数字")
        
        return await show_input_dialog(
            app,
            message=prompt,
            title=title,
            input_type="number",
            validator=Function(validate_number),
            **kwargs
        )
    
    @staticmethod
    async def input_password(app, prompt: str = "请输入密码:", title: str = "密码输入", **kwargs) -> Optional[str]:
        """密码输入对话框"""
        return await show_input_dialog(
            app,
            message=prompt,
            title=title,
            password=True,
            **kwargs
        )
    
    @staticmethod
    async def input_filename(app, prompt: str = "请输入文件名:", title: str = "文件名输入", **kwargs) -> Optional[str]:
        """文件名输入对话框"""
        # 文件名验证器
        def validate_filename(value: str) -> ValidationResult:
            import re
            # 检查文件名是否包含非法字符
            if re.search(r'[<>:"/\\|?*]', value):
                return ValidationResult.failure("文件名不能包含以下字符: < > : \" / \\ | ? *")
            if value.strip() != value:
                return ValidationResult.failure("文件名首尾不能包含空格")
            return ValidationResult.success()
        
        return await show_input_dialog(
            app,
            message=prompt,
            title=title,
            validator=Function(validate_filename),
            **kwargs
        )
    
    # 内嵌输入对话框
    @staticmethod
    async def embedded_user_form(app, title: str = "用户信息") -> Optional[dict]:
        """用户信息表单 - 内嵌输入对话框"""
        
        def validate_email(value: str):
            if "@" not in value or "." not in value:
                raise ValueError("请输入有效的邮箱地址")
            return True
        
        def validate_age(value: str):
            try:
                age = int(value)
                if age < 0 or age > 150:
                    raise ValueError("年龄必须在0-150之间")
                return True
            except ValueError:
                raise ValueError("请输入有效的年龄数字")
        
        input_fields = [
            {
                'name': 'name',
                'label': '姓名',
                'placeholder': '请输入您的姓名',
                'required': True
            },
            {
                'name': 'age',
                'label': '年龄',
                'placeholder': '请输入年龄',
                'required': True,
                'validator': Function(validate_age)
            },
            {
                'name': 'email',
                'label': '邮箱',
                'placeholder': '请输入邮箱地址',
                'required': True,
                'validator': Function(validate_email)
            },
            {
                'name': 'phone',
                'label': '电话',
                'placeholder': '请输入手机号码',
                'required': False
            },
            {
                'name': 'address',
                'label': '地址',
                'placeholder': '请输入联系地址',
                'required': False
            }
        ]
        
        return await show_embedded_input_dialog(
            app,
            message="请填写您的个人信息：",
            input_fields=input_fields,
            title=title,
            show_preview=True
        )
    
    @staticmethod
    async def embedded_login_form(app) -> Optional[dict]:
        """登录表单 - 内嵌输入对话框"""
        
        def validate_username(value: str):
            if len(value) < 3:
                raise ValueError("用户名至少3个字符")
            return True
        
        def validate_password(value: str):
            if len(value) < 6:
                raise ValueError("密码至少6个字符")
            return True
        
        input_fields = [
            {
                'name': 'username',
                'label': '用户名',
                'placeholder': '请输入用户名',
                'required': True,
                'validator': Function(validate_username)
            },
            {
                'name': 'password',
                'label': '密码',
                'placeholder': '请输入密码',
                'password': True,
                'required': True,
                'validator': Function(validate_password)
            },
            {
                'name': 'remember',
                'label': '记住我',
                'placeholder': '输入 yes 记住登录状态',
                'required': False,
                'default_value': 'no'
            }
        ]
        
        return await show_embedded_input_dialog(
            app,
            message="请输入您的登录信息：",
            input_fields=input_fields,
            title="用户登录",
            show_preview=False  # 登录表单不显示预览以保护密码
        )


# 为已有的CommonDialogs类动态添加内嵌输入对话框方法
def _add_embedded_methods_to_common_dialogs():
    """动态为CommonDialogs类添加内嵌输入对话框方法"""
    
    @staticmethod
    async def embedded_user_form(app, title: str = "用户信息") -> Optional[dict]:
        """用户信息表单 - 内嵌输入对话框"""
        
        def validate_email(value: str):
            if "@" not in value or "." not in value:
                raise ValueError("请输入有效的邮箱地址")
            return True
        
        def validate_age(value: str):
            try:
                age = int(value)
                if age < 0 or age > 150:
                    raise ValueError("年龄必须在0-150之间")
                return True
            except ValueError:
                raise ValueError("请输入有效的年龄数字")
        
        input_fields = [
            {
                'name': 'name',
                'label': '姓名',
                'placeholder': '请输入您的姓名',
                'required': True
            },
            {
                'name': 'age',
                'label': '年龄',
                'placeholder': '请输入年龄',
                'required': True,
                'validator': Function(validate_age)
            },
            {
                'name': 'email',
                'label': '邮箱',
                'placeholder': '请输入邮箱地址',
                'required': True,
                'validator': Function(validate_email)
            },
            {
                'name': 'phone',
                'label': '电话',
                'placeholder': '请输入手机号码',
                'required': False
            },
            {
                'name': 'address',
                'label': '地址',
                'placeholder': '请输入联系地址',
                'required': False
            }
        ]
        
        return await show_embedded_input_dialog(
            app,
            message="请填写您的个人信息：",
            input_fields=input_fields,
            title=title,
            show_preview=True
        )
    
    @staticmethod
    async def embedded_login_form(app) -> Optional[dict]:
        """登录表单 - 内嵌输入对话框"""
        
        def validate_username(value: str):
            if len(value) < 3:
                raise ValueError("用户名至少3个字符")
            return True
        
        def validate_password(value: str):
            if len(value) < 6:
                raise ValueError("密码至少6个字符")
            return True
        
        input_fields = [
            {
                'name': 'username',
                'label': '用户名',
                'placeholder': '请输入用户名',
                'required': True,
                'validator': Function(validate_username)
            },
            {
                'name': 'password',
                'label': '密码',
                'placeholder': '请输入密码',
                'password': True,
                'required': True,
                'validator': Function(validate_password)
            },
            {
                'name': 'remember',
                'label': '记住我',
                'placeholder': '输入 yes 记住登录状态',
                'required': False,
                'default_value': 'no'
            }
        ]
        
        return await show_embedded_input_dialog(
            app,
            message="请输入您的登录信息：",
            input_fields=input_fields,
            title="用户登录",
            show_preview=False  # 登录表单不显示预览以保护密码
        )
    
    # 将方法动态添加到CommonDialogs类
    CommonDialogs.embedded_user_form = embedded_user_form
    CommonDialogs.embedded_login_form = embedded_login_form

# 执行动态添加
_add_embedded_methods_to_common_dialogs()


class WindowDialogWithInput(ModalScreen):
    """带内嵌输入功能的窗口化对话框
    
    这个对话框可以在对话框内部直接包含输入字段，无需弹出额外的对话框
    """
    
    DEFAULT_CSS = """
    WindowDialogWithInput {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    
    .input-dialog-window-embedded {
        width: 70;
        height: auto;
        max-height: 30;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        border-title-background: $primary;
        border-title-style: bold;
        padding: 1 2;
        margin: 2;
    }
    
    .embedded-dialog-content {
        layout: vertical;
        height: auto;
    }
    
    .embedded-message-content {
        height: auto;
        text-align: left;
        padding: 1 0;
        color: $text;
        margin-bottom: 1;
    }
    
    .embedded-input-section {
        layout: vertical;
        height: auto;
        margin: 1 0;
        border: solid $primary;
        padding: 1;
        background: $panel;
    }
    
    .embedded-input-label {
        height: auto;
        text-align: left;
        color: $accent;
        margin-bottom: 1;
    }
    
    .embedded-input-field {
        width: 100%;
        margin-bottom: 1;
        border: solid $primary;
    }
    
    .embedded-input-field:focus {
        border: solid $accent;
    }
    
    .embedded-error-message {
        height: auto;
        color: $error;
        text-align: left;
        padding: 0 0 1 0;
        display: none;
    }
    
    .embedded-error-message.visible {
        display: block;
    }
    
    .embedded-button-row {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    .embedded-button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    
    .embedded-preview-section {
        layout: vertical;
        height: auto;
        margin: 1 0;
        border: solid $success;
        padding: 1;
        background: $surface;
        display: none;
    }
    
    .embedded-preview-section.visible {
        display: block;
    }
    
    .embedded-preview-label {
        height: auto;
        text-align: left;
        color: $success;
        margin-bottom: 1;
    }
    
    .embedded-preview-content {
        height: auto;
        text-align: left;
        color: $text;
        background: $panel;
        padding: 1;
        border: solid $success;
    }
    
    .input-dialog-window-embedded:focus-within {
        border: thick $accent;
    }
    """
    
    # 键盘绑定
    BINDINGS = [
        Binding("ctrl+enter", "submit", "提交", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
        Binding("ctrl+r", "reset_input", "重置"),
        Binding("ctrl+p", "preview", "预览"),
    ]

    @dataclass
    class EmbeddedResult(Message):
        """内嵌对话框结果消息"""
        submitted: bool
        values: dict = None
        dialog_id: Optional[str] = None

    def __init__(
        self, 
        message: str, 
        input_fields: list,
        title: Optional[str] = None,
        submit_text: str = "确认",
        cancel_text: str = "取消",
        preview_text: str = "预览",
        reset_text: str = "重置",
        dialog_id: Optional[str] = None,
        show_preview: bool = True,
        submit_callback: Optional[Callable[[dict], None]] = None,
        cancel_callback: Optional[Callable] = None
    ) -> None:
        """初始化带内嵌输入的窗口化对话框
        
        Args:
            message: 要显示的提示信息
            input_fields: 输入字段列表，每个元素为字典格式：
                {
                    'name': '字段名',
                    'label': '显示标签',
                    'placeholder': '占位符',
                    'default_value': '默认值',
                    'password': 是否密码字段,
                    'required': 是否必填,
                    'validator': 验证器函数
                }
            title: 对话框标题
            submit_text: 提交按钮文本
            cancel_text: 取消按钮文本
            preview_text: 预览按钮文本
            reset_text: 重置按钮文本
            dialog_id: 对话框唯一标识
            show_preview: 是否显示预览功能
            submit_callback: 提交回调函数
            cancel_callback: 取消回调函数
        """
        super().__init__()
        
        self.message = message
        self.input_fields = input_fields or []
        self.title = title or "输入信息"
        self.submit_text = submit_text
        self.cancel_text = cancel_text
        self.preview_text = preview_text
        self.reset_text = reset_text
        self.dialog_id = dialog_id
        self.show_preview = show_preview
        self.submit_callback = submit_callback
        self.cancel_callback = cancel_callback
        
        self._input_widgets = {}
        self._error_widgets = {}
        self._preview_widget = None

    def compose(self) -> ComposeResult:
        """构建带内嵌输入的对话框UI"""
        with Vertical(classes="input-dialog-window-embedded") as dialog_window:
            dialog_window.border_title = self.title
            
            with Vertical(classes="embedded-dialog-content"):
                # 消息显示区域
                yield Static(self.message, classes="embedded-message-content")
                
                # 为每个输入字段创建输入区域
                for field in self.input_fields:
                    field_name = field.get('name', '')
                    field_label = field.get('label', field_name)
                    
                    with Vertical(classes="embedded-input-section"):
                        # 字段标签
                        yield Static(f"[bold]{field_label}:[/bold]", classes="embedded-input-label")
                        
                        # 输入字段
                        yield Input(
                            value=field.get('default_value', ''),
                            placeholder=field.get('placeholder', ''),
                            password=field.get('password', False),
                            validators=[field['validator']] if field.get('validator') else None,
                            classes="embedded-input-field",
                            id=f"input-{field_name}"
                        )
                        
                        # 错误消息区域
                        yield Static("", classes="embedded-error-message", id=f"error-{field_name}")
                
                # 预览区域
                if self.show_preview:
                    with Vertical(classes="embedded-preview-section", id="preview-section"):
                        yield Static("[bold]输入预览:[/bold]", classes="embedded-preview-label")
                        yield Static("", classes="embedded-preview-content", id="preview-content")
                
                # 按钮行
                with Center():
                    with Horizontal(classes="embedded-button-row"):
                        yield Button(
                            self.submit_text, 
                            variant="success", 
                            classes="confirm-button",
                            id="submit-btn"
                        )
                        if self.show_preview:
                            yield Button(
                                self.preview_text, 
                                variant="primary", 
                                classes="preview-button",
                                id="preview-btn"
                            )
                        yield Button(
                            self.reset_text, 
                            variant="warning", 
                            classes="reset-button",
                            id="reset-btn"
                        )
                        yield Button(
                            self.cancel_text, 
                            variant="error", 
                            classes="cancel-button",
                            id="cancel-btn"
                        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        try:
            # 获取所有输入组件和错误组件的引用
            for field in self.input_fields:
                field_name = field.get('name', '')
                try:
                    self._input_widgets[field_name] = self.query_one(f"#input-{field_name}", Input)
                    self._error_widgets[field_name] = self.query_one(f"#error-{field_name}", Static)
                except:
                    pass
            
            # 获取预览组件引用
            if self.show_preview:
                try:
                    self._preview_widget = self.query_one("#preview-content", Static)
                except:
                    pass
            
            # 聚焦第一个输入字段
            if self._input_widgets:
                first_field = list(self._input_widgets.values())[0]
                first_field.focus()
        except Exception:
            pass

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入变化，清除错误并实时预览"""
        # 找到对应的字段名
        field_name = None
        for name, widget in self._input_widgets.items():
            if widget == event.input:
                field_name = name
                break
        
        if field_name:
            self._clear_error(field_name)
        
        # 如果启用预览，自动更新预览
        if self.show_preview:
            self._update_preview()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车提交"""
        event.stop()
        self.action_submit()

    @on(Button.Pressed, "#submit-btn")
    def on_submit_pressed(self, event: Button.Pressed) -> None:
        """处理提交按钮点击"""
        event.stop()
        self.action_submit()

    @on(Button.Pressed, "#preview-btn")
    def on_preview_pressed(self, event: Button.Pressed) -> None:
        """处理预览按钮点击"""
        event.stop()
        self.action_preview()

    @on(Button.Pressed, "#reset-btn")
    def on_reset_pressed(self, event: Button.Pressed) -> None:
        """处理重置按钮点击"""
        event.stop()
        self.action_reset_input()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        """处理取消按钮点击"""
        event.stop()
        self.action_cancel()

    def _validate_all_inputs(self) -> bool:
        """验证所有输入字段"""
        all_valid = True
        
        for field in self.input_fields:
            field_name = field.get('name', '')
            if field_name not in self._input_widgets:
                continue
                
            widget = self._input_widgets[field_name]
            value = widget.value.strip()
            
            # 检查必填
            if field.get('required', True) and not value:
                self._show_error(field_name, "此字段为必填项")
                all_valid = False
                continue
            
            # 检查自定义验证器
            validator = field.get('validator')
            if validator and value:
                try:
                    if hasattr(validator, 'validate'):
                        result = validator.validate(value)
                        if not result.is_valid:
                            error_msg = "输入格式不正确"
                            if hasattr(result, 'failure_descriptions') and result.failure_descriptions:
                                error_msg = result.failure_descriptions[0]
                            self._show_error(field_name, error_msg)
                            all_valid = False
                    else:
                        # 对于函数式验证器
                        validator(value)
                except Exception as e:
                    self._show_error(field_name, str(e))
                    all_valid = False
        
        return all_valid

    def _show_error(self, field_name: str, message: str) -> None:
        """显示指定字段的错误消息"""
        if field_name in self._error_widgets:
            error_widget = self._error_widgets[field_name]
            error_widget.update(message)
            error_widget.add_class("visible")

    def _clear_error(self, field_name: str) -> None:
        """清除指定字段的错误消息"""
        if field_name in self._error_widgets:
            error_widget = self._error_widgets[field_name]
            error_widget.remove_class("visible")
            error_widget.update("")

    def _clear_all_errors(self) -> None:
        """清除所有错误消息"""
        for field_name in self._error_widgets:
            self._clear_error(field_name)

    def _get_all_values(self) -> dict:
        """获取所有输入字段的值"""
        values = {}
        for field_name, widget in self._input_widgets.items():
            values[field_name] = widget.value.strip()
        return values

    def _update_preview(self) -> None:
        """更新预览内容"""
        if not self._preview_widget:
            return
            
        values = self._get_all_values()
        preview_lines = []
        
        for field in self.input_fields:
            field_name = field.get('name', '')
            field_label = field.get('label', field_name)
            value = values.get(field_name, '')
            
            # 密码字段特殊处理
            if field.get('password', False) and value:
                display_value = "*" * len(value)
            else:
                display_value = value or "[dim]未填写[/dim]"
            
            preview_lines.append(f"{field_label}: {display_value}")
        
        self._preview_widget.update("\n".join(preview_lines))

    def action_submit(self) -> None:
        """提交操作"""
        if not self._validate_all_inputs():
            return
            
        values = self._get_all_values()
        
        # 执行回调函数
        if self.submit_callback:
            try:
                self.submit_callback(values)
            except Exception as e:
                # 安全地记录错误
                try:
                    self.app.log.error(f"提交回调执行失败: {e}")
                except:
                    pass
        
        # 发送结果消息
        self.post_message(self.EmbeddedResult(submitted=True, values=values, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(values)

    def action_preview(self) -> None:
        """预览操作"""
        self._update_preview()
        
        # 显示预览区域
        try:
            preview_section = self.query_one("#preview-section")
            preview_section.add_class("visible")
        except:
            pass

    def action_reset_input(self) -> None:
        """重置所有输入"""
        for field in self.input_fields:
            field_name = field.get('name', '')
            if field_name in self._input_widgets:
                widget = self._input_widgets[field_name]
                widget.value = field.get('default_value', '')
        
        self._clear_all_errors()
        
        # 隐藏预览区域
        try:
            preview_section = self.query_one("#preview-section")
            preview_section.remove_class("visible")
        except:
            pass

    def action_cancel(self) -> None:
        """取消操作"""
        # 执行回调函数
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                try:
                    self.app.log.error(f"取消回调执行失败: {e}")
                except:
                    pass
        
        # 发送结果消息
        self.post_message(self.EmbeddedResult(submitted=False, values=None, dialog_id=self.dialog_id))
        
        # 关闭对话框并返回结果
        self.dismiss(None)


# 便利函数，用于快速创建和显示带内嵌输入的对话框
async def show_embedded_input_dialog(
    app,
    message: str,
    input_fields: list,
    title: Optional[str] = None,
    submit_text: str = "确认",
    cancel_text: str = "取消",
    preview_text: str = "预览",
    reset_text: str = "重置",
    dialog_id: Optional[str] = None,
    show_preview: bool = True,
    submit_callback: Optional[Callable[[dict], None]] = None,
    cancel_callback: Optional[Callable] = None
) -> Optional[dict]:
    """显示带内嵌输入的对话框并等待用户响应
    
    Args:
        app: Textual应用实例
        message: 提示消息
        input_fields: 输入字段配置列表
        title: 对话框标题
        submit_text: 提交按钮文本
        cancel_text: 取消按钮文本
        preview_text: 预览按钮文本
        reset_text: 重置按钮文本
        dialog_id: 对话框ID
        show_preview: 是否显示预览功能
        submit_callback: 提交回调
        cancel_callback: 取消回调
        
    Returns:
        Optional[dict]: 用户输入的所有字段值，如果取消则返回None
    """
    dialog = WindowDialogWithInput(
        message=message,
        input_fields=input_fields,
        title=title,
        submit_text=submit_text,
        cancel_text=cancel_text,
        preview_text=preview_text,
        reset_text=reset_text,
        dialog_id=dialog_id,
        show_preview=show_preview,
        submit_callback=submit_callback,
        cancel_callback=cancel_callback
    )
    
    result = await app.push_screen_wait(dialog)
    return result


# 为已有的CommonDialogs类添加内嵌输入对话框扩展方法 