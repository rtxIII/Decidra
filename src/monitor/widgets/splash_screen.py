"""
Decidra启动页面组件
基于Textual框架的启动界面实现，提供品牌展示、系统状态检查和自动跳转功能
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import os

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Center
from textual.widgets import Static, ProgressBar, Button
from textual.reactive import reactive
from textual.message import Message

from utils.global_vars import get_logger


class SplashScreen(Container):
    """Decidra启动页面组件，支持自动跳转到主界面"""
    
    DEFAULT_CSS = """
    
    SplashScreen {
        align: center middle;
        background: #0a0a0a;
        padding: 2;
        width: 100%;
        height: 100%;
    }
    
    .main-container {
        align: center middle;
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    .logo-container {
        text-align: center;
        margin: 1;
        padding: 2;
        background: #1a0d26;
        border: thick #ff00ff;
        border-title-color: #00ffff;
        width: 100%;

        overflow: auto;
    }
    
    .logo-text {
        opacity: 0;
        color: #ff00ff;
        text-style: bold;
        margin: 0;
        text-align: center;
    }
    
    
    .version-text {
        color: #ff6b9d;
        text-style: italic;
        margin: 1 0;
        text-align: center;
    }
    
    .glitch-text {
        color: #39ff14;
        text-style: bold;
        margin: 1 0;
        text-align: center;
    }
    
    .status-container {
        height: 20%;
        width: 100%;
        margin: 1;
        padding: 2;
        background: #0a0514;
        border: round #00ffff;
        border-title-color: #ff00ff;
    }
    
    .status-item {
        margin: 0 1;
        height: 1;
        color: #00ffff;
        text-align: center;
    }
    
    .status-success {
        color: #39ff14;
    }
    
    .status-error {
        color: #ff073a;
    }
    
    .status-warning {
        color: #ffb347;
    }
    
    .progress-container {
        height: 20%;
        width: 100%;
        margin: 1;
        padding: 2;
        background: #1a0d26;
        border: round #ff00ff;
        min-width: 60;
    }
    
    #loading_progress {
        width: 100%;
        color: #ff00ff;
        background: #0a0514;
    }
    
    #loading_progress > #bar {
        width: 100%;
    }
    
    #loading_progress > Bar {
        width: 100%;
    }
    
    #loading_progress Bar > .bar--bar {
        width: 100%;
        color: #ff00ff;
        background: #ff00ff 30%;
    }
    
    #loading_progress Bar > .bar--complete {
        width: 100%;
        color: #39ff14;
    }
    
    .countdown-text {
        color: #ff6b9d;
        text-align: center;
        margin: 1;
        text-style: bold;
        width: 100%;
    }
    
    .help-text {
        color: #7fffd4;
        text-align: center;
        margin: 1;
        width: 100%;
    }
    
    .action-buttons {
        width: 100%;
        margin: 1;
        text-align: center;
    }
    
    Button {
        margin: 0 2;
        min-width: 15;
        background: #1a0d26;
        color: #39ff14;
        border: solid #ff00ff;
    }
    
    """
    
    # 系统状态
    system_status: reactive[Dict[str, str]] = reactive({})
    loading_progress: reactive[float] = reactive(0.0)
    loading_message: reactive[str] = reactive("初始化中...")
    is_loading: reactive[bool] = reactive(True)
    countdown: reactive[int] = reactive(5)
    
    class StatusComplete(Message):
        """系统状态检查完成消息"""
        def __init__(self, status: Dict[str, str]) -> None:
            self.status = status
            super().__init__()
    
    class AutoJumpRequested(Message):
        """请求自动跳转到主界面"""
        pass
    
    class ActionSelected(Message):
        """用户选择操作消息"""
        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()
    
    def __init__(self, auto_jump_delay: int = 0, **kwargs):
        """
        初始化启动页面
        
        Args:
            auto_jump_delay: 自动跳转延迟时间(秒)
        """
        super().__init__(**kwargs)
        self.logger = get_logger(__name__)
        self.auto_jump_delay = auto_jump_delay
        self.check_task: Optional[asyncio.Task] = None
        self.countdown_task: Optional[asyncio.Task] = None
        self.jump_cancelled = False
        
    def compose(self) -> ComposeResult:
        """构建启动页面UI"""
        with Container(classes="main-container"):
            with Vertical():
                # Logo区域
                with Container(classes="logo-container"):
                    #yield Static(self._get_logo_text(), classes="logo-text")
                    yield Static("▼ DECIDRA ▼", classes="status-item")
                    yield Static(self._get_logo_text(),  id="logo_text", classes="logo-text")


                
                # 进度条区域
                with Container(classes="progress-container"):
                    yield Static("▼ SYSTEM STATUS CHECK ▼", classes="status-item")
                    yield Static("⟡ FUTU API: SCANNING...", id="futu_status", classes="status-item")
                    yield Static("⟡ CONFIG FILES: SCANNING...", id="config_status", classes="status-item")  
                    yield Static("⟡ MARKET STATUS: SCANNING...", id="market_status", classes="status-item")
                    yield ProgressBar(total=100, show_eta=False, id="loading_progress")
                    yield Static("◈ INITIALIZING NEURAL NETWORKS... ◈", id="loading_message", classes="help-text")
                
                # 倒计时显示
                yield Static("", id="countdown_display", classes="countdown-text")
                
                # 快捷键提示
                yield Static(
                    "◢ [#ff00ff]Enter[/] JACK IN | [#00ffff]Space[/] ENTER | [#ff073a]Q[/] DISCONNECT ◣",
                    classes="help-text"
                )
    
    def _get_logo_text(self) -> str:
        """获取ASCII艺术Logo"""
        return """
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢩⢋⠟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢣⢃⣎⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣻⢟⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢣⢏⢎⣿⣿⡟⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣿⣶⣿⢟⡿⣿⣿⣿⣿⣿⡿⣿⣿⣿⡿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⡞⡜⣿⣿⡟⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣿⣴⣿⣿⣿⡿⣿⡿⣿⣿⣿⣷⢹⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⡞⡼⣼⣿⡿⣜⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣯⣟⡽⣿⣧⣿⣿⣿⡿⡇⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢡⣾⡽⣿⣿⣿⣵⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⠀⠀⠐⠶⢶⣾⣿⣿⣿⣿⡿⠿⠛⠉⣼⣿⣯⣿⣿⣯⡇⣇⢹
⣿⣿⣿⣿⣿⣿⣿⣿⠟⣸⣿⣟⠇⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⣠⠴⠶⠿⠿⠿⠿⣿⣾⣿⣭⣍⣀⠀⢀⣠⣾⣿⡿⠿⣿⣿⣿⡇⢃⣿
⣿⣿⣿⣿⣿⣿⡿⢋⣾⣿⣿⣿⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠉⢀⠀⣀⣀⣀⣀⣀⠀⠉⠙⠿⢿⣿⡷⠀⠉⠉⣉⣀⣀⣉⣿⣿⣇⣼⣿
⣿⣿⣿⣿⣿⡿⡱⣿⣿⣿⣿⠇⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⣀⣴⣾⠿⢟⣿⣿⣿⣿⣿⣶⡄⠀⠀⠈⠀⠀⠀⠼⠿⠿⠟⠛⣿⣿⣿⣿⣿
⣿⣿⣿⡿⢫⢎⣾⣿⣿⣿⡿⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠹⣏⠁⠀⣾⣿⣿⣿⣿⡎⢳⠀⠀⠀⠀⠀⠀⠀⣤⣴⣶⣶⣤⣷⣿⣿⣿⣿
⣿⣿⣿⣴⢷⣿⣿⣿⣿⣿⢡⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀⠀⠙⠳⣤⣘⢿⣿⣻⠝⠀⡾⠀⠀⠀⠀⠀⠀⣾⣿⣿⠘⣿⣿⢿⣿⣿⣿⣿
⣿⣿⡯⣼⣻⣿⣿⣿⣿⡏⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠒⠒⠚⠁⠀⠀⠀⠀⠀⣸⡿⡿⣿⣸⣿⡿⢿⣿⣿⣿⣿
⣿⣿⣿⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠓⠯⠯⠵⣿⣿⡇⣿⣿⣿⣿⣿
⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⢠⣿⡿⢸⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣳⠀⠀⣾⣿⠇⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⡼⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⢤⣀⠀⠀⡨⢁⣾⣿⣿⢰⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⢿⢱⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠒⠉⢠⣾⣿⣿⡿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣯⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡿⣖⡋⠭⢭⣙⣖⡆⠀⣴⣿⣿⣿⣟⣾⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣽⣬⣿⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠢⡀⠉⠉⠻⣿⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣏⡾⡹⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠑⠒⢚⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⢷⢷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠈⣴⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⢏⡞⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⢀⢞⣿⣿⣿⣷⣶⣄⣀⡀⠀⠀⣀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣴⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣤⣀⠀⠀⠏⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣏⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⡻⢿⣿⣾⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠀⠀⠀⠀⠀⠀⠉⠙⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣤⣤⣤⣤⣴⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
        """
    
    async def on_mount(self) -> None:
        """组件挂载时启动系统检查"""
        self.logger.info("启动页面已挂载，开始系统状态检查")
        self.check_task = asyncio.create_task(self._perform_system_check())
        logo_text = self.query_one("#logo_text", Static)
        logo_text.styles.animate("opacity", value=1, duration=2.0)
    
    async def _perform_system_check(self) -> None:
        """执行系统状态检查"""
        try:
            status = {}
            
            # 步骤1: 检查配置文件
            await self._update_progress(25, "◈ SCANNING CONFIG FILES... ◈")
            await asyncio.sleep(0.5)
            status['config'] = await self._check_config_status()
            self._update_status_display('config_status', status['config'])
            
            # 步骤2: 检查富途API
            await self._update_progress(50, "◈ CONNECTING TO FUTU API... ◈")
            await asyncio.sleep(1.0)
            status['futu'] = await self._check_futu_status()
            self._update_status_display('futu_status', status['futu'])
            
            # 步骤3: 检查市场状态
            await self._update_progress(75, "◈ ANALYZING MARKET STATUS... ◈")
            await asyncio.sleep(0.5)
            status['market'] = await self._check_market_status()
            self._update_status_display('market_status', status['market'])
            
            # 步骤4: 完成初始化
            await self._update_progress(100, "◢◤ NEURAL NETWORK READY ◥◣")
            await asyncio.sleep(0.5)
            
            # 更新系统状态
            self.system_status = status
            self.is_loading = False
            
            
            # 发送完成消息
            self.post_message(self.StatusComplete(status))
            
            # 启动自动跳转倒计时
            self.countdown_task = asyncio.create_task(self._start_auto_jump_countdown())
            
        except Exception as e:
            self.logger.error(f"系统状态检查失败: {e}")
            await self._update_progress(100, f"检查失败: {e}")
            self.is_loading = False
    
    async def _start_auto_jump_countdown(self) -> None:
        """启动自动跳转倒计时"""
        try:
            self.countdown = self.auto_jump_delay
            countdown_widget = self.query_one("#countdown_display", Static)
            
            while self.countdown >= 0 and not self.jump_cancelled:
                countdown_widget.update(
                    f"◢◤ JACK IN {self.countdown} SECONDS... [ABORT WITH SPACE] ◥◣"
                )
                await asyncio.sleep(1)
                self.countdown -= 1
            
            if not self.jump_cancelled:
                countdown_widget.update("◢◤ JACKING INTO THE MATRIX... ◥◣")
                await asyncio.sleep(0.5)
                self.post_message(self.AutoJumpRequested())
            else:
                countdown_widget.update("◢◤ CONNECTION ABORTED ◥◣")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"倒计时失败: {e}")
    
    async def _update_progress(self, progress: float, message: str) -> None:
        """更新进度和消息"""
        self.loading_progress = progress
        self.loading_message = message
        
        # 更新UI显示
        try:
            progress_bar = self.query_one("#loading_progress", ProgressBar)
            progress_bar.progress = progress
            
            message_widget = self.query_one("#loading_message", Static)
            message_widget.update(message)
        except Exception as e:
            self.logger.warning(f"更新进度显示失败: {e}")
    
    def _update_status_display(self, widget_id: str, status: str) -> None:
        """更新状态显示"""
        try:
            widget = self.query_one(f"#{widget_id}", Static) 
            
            if status.startswith("✅"):
                widget.update(status)
                widget.add_class("status-success")
            elif status.startswith("❌"):
                widget.update(status)
                widget.add_class("status-error")
            elif status.startswith("⚠️"):
                widget.update(status)
                widget.add_class("status-warning")
            else:
                widget.update(f"⟡ {status}")
        except Exception as e:
            self.logger.warning(f"更新状态显示失败: {e}")
    
    async def _check_config_status(self) -> str:
        """检查配置文件状态"""
        try:
            from utils.global_vars import get_config_manager

            if get_config_manager is None:
                return "⚠️ CONFIG: MANAGER OFFLINE"

            config_manager = get_config_manager()
            validation = config_manager.validate_config()

            if validation.is_valid:
                return "✅ CONFIG: NEURAL LINK ONLINE"
            else:
                return f"⚠️ CONFIG: {len(validation.errors)} ERRORS DETECTED"
                
        except Exception:
            return f"❌ CONFIG: SYSTEM FAILURE"
    
    async def _check_futu_status(self) -> str:
        """检查富途API连接状态"""
        try:
            from api.futu import create_client
            
            if create_client is None:
                return "❌ FUTU API: MODULE NOT FOUND"
            
            return "✅ FUTU API: NEURAL INTERFACE READY"
            
        except Exception:
            return f"❌ FUTU API: CONNECTION LOST"
    
    async def _check_market_status(self) -> str:
        """检查市场状态"""
        try:
            now = datetime.now()
            hour = now.hour
            weekday = now.weekday()
            
            if weekday >= 5:
                return "⚠️ MARKET: CLOSED (WEEKEND)"
            elif 9 <= hour < 16:
                return "✅ MARKET: TRADING ACTIVE"
            else:
                return "⚠️ MARKET: AFTER HOURS"
                
        except Exception:
            return f"❌ MARKET: DATA CORRUPTED"
    
    async def on_key(self, event) -> None:
        """处理按键事件"""
        if event.key == "enter":
                self._cancel_auto_jump()
                self.post_message(self.AutoJumpRequested())
        elif event.key == "space":
                self._cancel_auto_jump()
                self.post_message(self.AutoJumpRequested())
    
    def _cancel_auto_jump(self) -> None:
        """取消自动跳转"""
        self.jump_cancelled = True
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
        
        try:
            countdown_widget = self.query_one("#countdown_display", Static)
            countdown_widget.update("◢◤ CONNECTION ABORTED BY USER ◥◣")
        except Exception:
            pass
    
    def on_unmount(self) -> None:
        """组件卸载时清理资源"""
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
        self.logger.info("启动页面已卸载")