#!/usr/bin/env python3
"""
AI快捷对话框组件

提供快捷问题按钮 + 自定义输入的组合对话框
用户可以点击预设问题或输入自定义问题
"""

from typing import Optional
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input
from textual.containers import Horizontal, Vertical, Grid, Center


class AIQuickDialog(ModalScreen):
    """AI快捷对话框 - 预设问题 + 自定义输入

    每次打开时自动获取当前选中的股票信息
    """

    DEFAULT_CSS = """
    AIQuickDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }

    .ai-quick-dialog-window {
        width: 80;
        height: auto;
        min-height: 30;
        max-height: 40;
        background: $surface;
        border: thick $primary;
        border-title-color: $text;
        border-title-background: $primary;
        border-title-style: bold;
        padding: 2;
        margin: 1;
        overflow-y: auto;
    }

    .ai-dialog-header {
        height: auto;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .ai-dialog-subtitle {
        height: auto;
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    .quick-questions-section {
        layout: vertical;
        height: auto;
        margin-bottom: 1;
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    .section-title {
        height: auto;
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }

    .quick-buttons-grid {
        layout: grid;
        grid-size: 2 3;  /* 2列3行 */
        grid-gutter: 1;
        height: auto;
    }

    .quick-button {
        width: 100%;
        height: 3;
        min-width: 0;
        padding: 0 1;
        text-overflow: ellipsis;
    }

    .custom-input-section {
        layout: vertical;
        height: auto;
        margin-bottom: 1;
        border: solid $success;
        padding: 1;
        background: $panel;
    }

    .custom-input-field {
        width: 100%;
        margin-bottom: 0;
        border: solid $primary;
    }

    .custom-input-field:focus {
        border: solid $accent;
    }

    .action-button-row {
        layout: horizontal;
        height: 3;
        align: center middle;
        margin-top: 0;
    }

    .action-button-row Button {
        margin: 0 1;
        min-width: 12;
        height: 3;
    }

    .ai-quick-dialog-window:focus-within {
        border: thick $accent;
    }
    """

    BINDINGS = [
        Binding("enter", "submit_custom", "提交自定义问题", priority=True),
        Binding("escape", "cancel", "取消", priority=True),
        Binding("1", "quick_question_1", "快捷问题1"),
        Binding("2", "quick_question_2", "快捷问题2"),
        Binding("3", "quick_question_3", "快捷问题3"),
        Binding("4", "quick_question_4", "快捷问题4"),
        Binding("5", "quick_question_5", "快捷问题5"),
        Binding("6", "quick_question_6", "快捷问题6"),
    ]

    def __init__(
        self,
        stock_code: str = "",
        stock_name: str = "",
        dialog_id: Optional[str] = None
    ) -> None:
        """初始化AI快捷对话框

        Args:
            stock_code: 当前股票代码
            stock_name: 当前股票名称
            dialog_id: 对话框唯一标识
        """
        super().__init__()

        self.dialog_id = dialog_id

        # 存储股票信息
        self.stock_code = stock_code
        self.stock_name = stock_name

        # 预设快捷问题列表（初始为空，在 compose 后生成）
        self.quick_questions: list[str] = []

        # 组件引用
        self._input_widget: Optional[Input] = None

    def compose(self) -> ComposeResult:
        """构建AI快捷对话框UI"""
        # 生成问题列表
        self._generate_questions()

        with Vertical(classes="ai-quick-dialog-window") as dialog_window:
            dialog_window.border_title = "💻 AI 智能助手"

            # 标题区域
            if self.stock_name:
                yield Static(
                    f"当前股票: {self.stock_code} {self.stock_name}",
                    classes="ai-dialog-header"
                )
            else:
                yield Static(
                    "AI 智能投资助手",
                    classes="ai-dialog-header"
                )

            yield Static(
                "选择快捷问题或输入自定义问题",
                classes="ai-dialog-subtitle"
            )

            # 快捷问题区域
            with Vertical(classes="quick-questions-section"):
                yield Static("📌 快捷问题（点击或按数字键1-6）", classes="section-title")

                # 问题按钮网格
                with Grid(classes="quick-buttons-grid"):
                    for idx, question in enumerate(self.quick_questions, 1):
                        yield Button(
                            f"{question}",
                            id=f"quick_{idx}",
                            classes="quick-button",
                            variant="primary"
                        )

            # 自定义输入区域
            with Vertical(classes="custom-input-section"):
                yield Static("✏️ 自定义问题", classes="section-title")

                yield Input(
                    placeholder="输入您的问题，按 Enter 提交...",
                    classes="custom-input-field",
                    id="custom_input"
                )

            # 操作按钮行
            with Center():
                with Horizontal(classes="action-button-row"):
                    yield Button(
                        "提交",
                        variant="success",
                        id="submit_btn"
                    )
                    yield Button(
                        "取消",
                        variant="error",
                        id="cancel_btn"
                    )

    def on_mount(self) -> None:
        """组件挂载时自动聚焦到输入框"""
        try:
            self._input_widget = self.query_one("#custom_input", Input)
            # 默认聚焦到自定义输入框
            self._input_widget.focus()
        except Exception:
            pass

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id
        self.log.debug(f"button_id = {button_id}")
        self.log.debug(f"button label = {event.button.label}")

        if button_id == "submit_btn":
            self.log.debug(f"识别为提交按钮")
            self.action_submit_custom()
        elif button_id == "cancel_btn":
            self.log.debug(f"识别为取消按钮")
            self.action_cancel()
        elif button_id and button_id.startswith("quick_"):
            self.log.debug(f"识别为快捷问题按钮: {button_id}")

            # 快捷问题按钮
            try:
                idx = int(button_id.split("_")[1]) - 1
                self.log.debug(f"解析到索引: {idx}")
                if 0 <= idx < len(self.quick_questions):
                    question = self.quick_questions[idx]
                    self.log.debug(f"提交问题: {question}")
                    self._submit_question(question)
                else:
                    self.log.error(f"索引越界: {idx}, 问题数量: {len(self.quick_questions)}")
            except (ValueError, IndexError) as e:
                self.log.error(f"快捷问题索引错误: {e}")
        else:
            self.log.warning(f"未识别的按钮ID: {button_id}")

    @on(Input.Submitted, "#custom_input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车提交"""
        event.stop()
        self.action_submit_custom()

    def action_submit_custom(self) -> None:
        """提交自定义问题"""
        if not self._input_widget:
            return

        custom_question = self._input_widget.value.strip()

        if not custom_question:
            # 如果自定义输入为空，提示用户
            self._input_widget.placeholder = "⚠️ 请输入问题或选择快捷问题..."
            return

        self._submit_question(custom_question)

    def action_cancel(self) -> None:
        """取消操作"""
        self.dismiss(None)

    # 快捷键绑定的快捷问题方法
    def action_quick_question_1(self) -> None:
        """快捷问题1"""
        self._submit_question(self.quick_questions[0])

    def action_quick_question_2(self) -> None:
        """快捷问题2"""
        self._submit_question(self.quick_questions[1])

    def action_quick_question_3(self) -> None:
        """快捷问题3"""
        self._submit_question(self.quick_questions[2])

    def action_quick_question_4(self) -> None:
        """快捷问题4"""
        self._submit_question(self.quick_questions[3])

    def action_quick_question_5(self) -> None:
        """快捷问题5"""
        self._submit_question(self.quick_questions[4])

    def action_quick_question_6(self) -> None:
        """快捷问题6"""
        self._submit_question(self.quick_questions[5])

    def _submit_question(self, question: str) -> None:
        """提交问题并关闭对话框

        Args:
            question: 要提交的问题
        """
        self.dismiss(question)

    def _generate_questions(self) -> None:
        """根据当前股票信息生成预设问题"""
        stock_display = self.stock_name if self.stock_name else "该股"
        self.quick_questions = [
            f"分析{stock_display}投资价值",
            f"{stock_display}买卖建议",
            "技术指标信号分析",
            "短期买入建仓",
            "同行业股票对比",
            "主力资金流向"
        ]
