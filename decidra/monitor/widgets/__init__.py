"""
Monitor Widgets Module
监控界面小部件模块

提供用于股票监控系统的自定义Textual组件。
"""

# Tab组件 - 自定义标签页组件
from .tab import ContentTab, TabbedContent, TabPane

# 对话框组件
from .dialog import ConfirmDialog
from .auto_dialog import WindowInputDialog
from .window_dialog import (
    WindowConfirmDialog, 
    WindowInputDialog as WindowInputDialogAdvanced,
    CommonDialogs,
    WindowDialogWithInput
)

# 信息面板组件
from .line_panel import (
    InfoType, 
    InfoLevel, 
    InfoMessage, 
    InfoBuffer, 
    InfoDisplay, 
    InfoFilterBar, 
    InfoPanel
)

# 辅助组件
from .help import HelpScreen
from .progress import ProgressBar
from .spinner import SpinnerWidget
from .topbar import TopBar
from .highlighter import LogHighlighter

# 导出所有可用组件
__all__ = [
    # Tab组件
    "ContentTab",
    "TabbedContent", 
    "TabPane",
    
    # 对话框组件
    "ConfirmDialog",
    "WindowInputDialog",
    "WindowConfirmDialog",
    "WindowInputDialogAdvanced", 
    "CommonDialogs",
    "WindowDialogWithInput",
    
    # 信息面板组件
    "InfoType",
    "InfoLevel", 
    "InfoMessage",
    "InfoBuffer",
    "InfoDisplay",
    "InfoFilterBar",
    "InfoPanel",
    
    # 辅助组件
    "HelpScreen",
    "ProgressBar",
    "SpinnerWidget", 
    "TopBar",
    "LogHighlighter",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Decidra Team"
__description__ = "Custom Textual widgets for stock monitoring system"