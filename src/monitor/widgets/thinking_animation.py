"""
AI思考动画组件
提供动态的思考状态显示效果
"""

import asyncio
from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive


class ThinkingAnimation(Widget):
    """AI思考动画组件"""
    
    DEFAULT_CSS = """
    ThinkingAnimation {
        height: auto;
        width: 1fr;
        text-align: center;
    }
    
    ThinkingAnimation .thinking-text {
        color: $primary;
        text-style: bold;
    }
    
    ThinkingAnimation .thinking-dots {
        color: $accent;
        text-style: italic;
    }
    """
    
    # 动画状态
    is_active = reactive(False)
    animation_frame = reactive(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_task = None
        
        # 动画帧序列
        self.thinking_frames = [
            "🤔 AI正在思考中",
            "🤔 AI正在思考中.",
            "🤔 AI正在思考中..",
            "🤔 AI正在思考中...",
            "🧠 AI正在分析中",
            "🧠 AI正在分析中.",
            "🧠 AI正在分析中..",
            "🧠 AI正在分析中...",
            "⚡ AI正在生成回复",
            "⚡ AI正在生成回复.",
            "⚡ AI正在生成回复..",
            "⚡ AI正在生成回复...",
            "✨ AI正在整理思路",
            "✨ AI正在整理思路.",
            "✨ AI正在整理思路..",
            "✨ AI正在整理思路..."
        ]
        
        # 旋转符号序列
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        
        # 思考符号序列
        self.brain_frames = ["🧠", "💭", "🤔", "💡"]
        
    def compose(self) -> ComposeResult:
        """组合思考动画组件"""
        yield Static("", classes="thinking-text", id="thinking_display")
    
    async def start_animation(self) -> None:
        """启动思考动画"""
        if self.is_active:
            return
            
        self.is_active = True
        self.animation_task = asyncio.create_task(self._animation_loop())
    
    async def stop_animation(self) -> None:
        """停止思考动画"""
        self.is_active = False
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None
    
    async def _animation_loop(self) -> None:
        """动画循环"""
        frame_index = 0
        spinner_index = 0
        brain_index = 0
        
        try:
            while self.is_active:
                # 组合动画效果
                thinking_text = self.thinking_frames[frame_index % len(self.thinking_frames)]
                spinner = self.spinner_frames[spinner_index % len(self.spinner_frames)]
                brain = self.brain_frames[brain_index % len(self.brain_frames)]
                
                # 根据时间选择不同的动画样式
                cycle = frame_index // len(self.thinking_frames)
                
                if cycle % 3 == 0:
                    # 标准文本动画
                    display_text = thinking_text
                elif cycle % 3 == 1:
                    # 旋转符号 + 文本
                    display_text = f"{spinner} AI正在深度思考中..."
                else:
                    # 脑子符号动画
                    display_text = f"{brain} AI正在处理您的问题..."
                
                # 更新显示
                display = self.query_one("#thinking_display", Static)
                display.update(display_text)
                
                # 更新索引
                frame_index += 1
                spinner_index += 1
                brain_index += 1
                
                # 动画间隔
                await asyncio.sleep(0.5)  # 500ms间隔
                
        except asyncio.CancelledError:
            pass
        except Exception:
            # 发生错误时显示静态文本
            try:
                display = self.query_one("#thinking_display", Static)
                display.update("🤔 AI正在思考中...")
            except:
                pass
    
    async def on_unmount(self) -> None:
        """组件卸载时停止动画"""
        await self.stop_animation()


class PulsingText(Static):
    """脉搏式文本动画"""
    
    DEFAULT_CSS = """
    PulsingText {
        text-align: center;
    }
    
    PulsingText.-pulse-1 {
        color: $primary;
        text-style: bold;
    }
    
    PulsingText.-pulse-2 {
        color: $accent;
        text-style: bold italic;
    }
    
    PulsingText.-pulse-3 {
        color: $success;
        text-style: bold underline;
    }
    """
    
    def __init__(self, text: str = "🤔 AI正在思考中...", **kwargs):
        super().__init__(text, **kwargs)
        self.original_text = text
        self.is_pulsing = False
        self.pulse_task = None
    
    async def start_pulse(self) -> None:
        """开始脉搏动画"""
        if self.is_pulsing:
            return
            
        self.is_pulsing = True
        self.pulse_task = asyncio.create_task(self._pulse_loop())
    
    async def stop_pulse(self) -> None:
        """停止脉搏动画"""
        self.is_pulsing = False
        if self.pulse_task:
            self.pulse_task.cancel()
            try:
                await self.pulse_task
            except asyncio.CancelledError:
                pass
        
        # 恢复原始样式
        self.remove_class("-pulse-1", "-pulse-2", "-pulse-3")
    
    async def _pulse_loop(self) -> None:
        """脉搏循环"""
        pulse_states = ["-pulse-1", "-pulse-2", "-pulse-3", "-pulse-2"]
        
        try:
            while self.is_pulsing:
                for state in pulse_states:
                    if not self.is_pulsing:
                        break
                    
                    # 移除所有脉搏样式
                    self.remove_class("-pulse-1", "-pulse-2", "-pulse-3")
                    # 添加当前状态
                    self.add_class(state)
                    
                    await asyncio.sleep(0.8)  # 800ms间隔
                    
        except asyncio.CancelledError:
            pass
    
    async def on_unmount(self) -> None:
        """组件卸载时清理"""
        await self.stop_pulse()