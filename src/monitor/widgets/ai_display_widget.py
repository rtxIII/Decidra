"""
AI建议显示组件
专门用于展示AI分析建议和用户交互操作

主要功能:
- 实时AI建议显示
- 建议分类管理（技术分析、基本面分析、风险评估）
- 置信度可视化显示
- 用户交互操作（接受、忽略、保存）
- 建议状态管理和持久化
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass
import json
import os
import uuid

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical, Container
from textual.widgets import Static, Button, Select
from textual.reactive import reactive
from textual.message import Message

from utils import logger


class SuggestionType(Enum):
    """建议类型枚举"""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental" 
    RISK = "risk"
    GENERAL = "general"


class SuggestionStatus(Enum):
    """建议状态枚举"""
    NEW = "new"
    ACCEPTED = "accepted"
    IGNORED = "ignored"
    SAVED = "saved"


@dataclass
class AIDisplayItem:
    """AI建议显示项数据结构"""
    suggestion_id: str
    suggestion_type: SuggestionType
    title: str
    content: str
    confidence: float  # 0.0-1.0
    timestamp: datetime
    status: SuggestionStatus = SuggestionStatus.NEW
    stock_code: str = ""
    action_buttons: List[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.action_buttons is None:
            if self.status == SuggestionStatus.NEW:
                self.action_buttons = ['accept', 'ignore', 'save']
            else:
                self.action_buttons = []

    @property
    def color_code(self) -> str:
        """根据建议类型返回颜色代码"""
        color_map = {
            SuggestionType.TECHNICAL: "green",
            SuggestionType.FUNDAMENTAL: "blue", 
            SuggestionType.RISK: "yellow",
            SuggestionType.GENERAL: "cyan"
        }
        return color_map.get(self.suggestion_type, "default")

    @property
    def type_icon(self) -> str:
        """根据建议类型返回图标"""
        icon_map = {
            SuggestionType.TECHNICAL: "🟢",
            SuggestionType.FUNDAMENTAL: "🔵",
            SuggestionType.RISK: "🟡", 
            SuggestionType.GENERAL: "⚪"
        }
        return icon_map.get(self.suggestion_type, "•")

    @property
    def confidence_stars(self) -> str:
        """根据置信度返回星级显示"""
        star_count = int(self.confidence * 5)
        full_stars = "⭐" * star_count
        empty_stars = "☆" * (5 - star_count)
        return full_stars + empty_stars

    @property
    def status_display(self) -> str:
        """状态显示文本"""
        status_map = {
            SuggestionStatus.NEW: "[最新]",
            SuggestionStatus.ACCEPTED: "[已执行]",
            SuggestionStatus.IGNORED: "[已忽略]",
            SuggestionStatus.SAVED: "[已保存]"
        }
        return status_map.get(self.status, "")


@dataclass 
class AIDisplayConfig:
    """AI显示配置"""
    max_display_items: int = 10
    auto_refresh_interval: int = 30
    confidence_threshold: float = 0.5
    show_ignored_items: bool = False
    default_filter: str = "all"
    enable_animations: bool = True


class SuggestionCard(Container):
    """单个建议卡片组件"""
    
    DEFAULT_CSS = """
    SuggestionCard {
        height: 6;
        margin: 1 0;
        padding: 1;
        border: solid $accent;
        background: $surface;
    }
    
    SuggestionCard.-new { 
        border-left: thick $success;
    }
    
    SuggestionCard.-accepted { 
        border-left: thick $primary;
    }
    
    SuggestionCard.-ignored { 
        border-left: thick $text-muted;
        opacity: 0.7;
    }
    
    SuggestionCard.-saved { 
        border-left: thick $warning;
    }
    
    SuggestionCard .suggestion-header {
        height: 1;
        width: 1fr;
    }
    
    SuggestionCard .suggestion-content {
        height: 2;
        width: 1fr;
        text-wrap: true;
    }
    
    SuggestionCard .suggestion-footer {
        height: 1;
        width: 1fr;
        layout: horizontal;
    }
    
    SuggestionCard .confidence-info {
        width: 1fr;
        color: $text-muted;
    }
    
    SuggestionCard .action-buttons {
        dock: right;
        layout: horizontal;
        width: auto;
    }
    
    SuggestionCard .action-buttons Button {
        width: 8;
        height: 1;
        margin-left: 1;
    }
    
    SuggestionCard .confidence-stars { 
        color: $warning;
    }
    """
    
    class SuggestionAction(Message):
        """建议操作消息"""
        def __init__(self, suggestion_id: str, action: str):
            super().__init__()
            self.suggestion_id = suggestion_id
            self.action = action

    def __init__(self, item: AIDisplayItem, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.add_class(f"-{item.status.value}")
    
    def compose(self) -> ComposeResult:
        """组合建议卡片"""
        # 头部信息
        header_text = f"{self.item.type_icon} {self.item.status_display} {self.item.title} {self.item.confidence_stars}"
        yield Static(header_text, classes="suggestion-header")
        
        # 建议内容
        yield Static(self.item.content, classes="suggestion-content")
        
        # 底部信息和操作按钮
        with Horizontal(classes="suggestion-footer"):
            confidence_text = f"置信度: {self.item.confidence:.0%} | {self.item.timestamp.strftime('%H:%M:%S')}"
            if self.item.status != SuggestionStatus.NEW:
                confidence_text += f" | 状态: {self.item.status.value} ✓"
            yield Static(confidence_text, classes="confidence-info")
            
            # 操作按钮
            if self.item.action_buttons:
                with Horizontal(classes="action-buttons"):
                    for action in self.item.action_buttons:
                        button_text, button_id = self._get_button_config(action)
                        yield Button(button_text, id=f"{action}_{self.item.suggestion_id}", 
                                   variant="primary" if action == "accept" else "default")
    
    def _get_button_config(self, action: str) -> tuple[str, str]:
        """获取按钮配置"""
        button_map = {
            'accept': ("✅接受", "accept"),
            'ignore': ("❌忽略", "ignore"),
            'save': ("💾保存", "save")
        }
        return button_map.get(action, (action, action))
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        if not button_id:
            return
            
        # 解析按钮ID获取动作和建议ID
        parts = button_id.split('_', 1)
        if len(parts) == 2:
            action, suggestion_id = parts
            if suggestion_id == self.item.suggestion_id:
                self.post_message(self.SuggestionAction(suggestion_id, action))


class AIDisplayWidget(ScrollableContainer):
    """AI建议显示组件"""
    
    DEFAULT_CSS = """
    AIDisplayWidget {
        height: 100%;
        background: $surface;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }
    
    AIDisplayWidget:focus {
        border: heavy $accent;
    }
    
    AIDisplayWidget .suggestion-container {
        layout: vertical;
        height: auto;
        width: 1fr;
    }
    
    AIDisplayWidget .filter-bar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
        border-bottom: solid $border;
        layout: horizontal;
    }
    
    AIDisplayWidget .filter-bar Select {
        width: 15;
        margin-right: 1;
    }
    
    AIDisplayWidget .filter-bar Button {
        width: 8;
        margin-right: 1;
    }
    
    AIDisplayWidget .empty-state {
        height: 5;
        text-align: center;
        color: $text-muted;
        margin: 2;
    }
    """
    
    # 响应式属性
    suggestions: reactive[List[AIDisplayItem]] = reactive([], layout=True)
    current_filter: reactive[str] = reactive("all")
    max_items: reactive[int] = reactive(10)
    
    class SuggestionAccepted(Message):
        """建议被接受消息"""
        def __init__(self, suggestion_id: str):
            super().__init__()
            self.suggestion_id = suggestion_id
    
    class SuggestionIgnored(Message):
        """建议被忽略消息"""
        def __init__(self, suggestion_id: str):
            super().__init__()
            self.suggestion_id = suggestion_id
    
    class SuggestionSaved(Message):
        """建议被保存消息"""
        def __init__(self, suggestion_id: str):
            super().__init__()
            self.suggestion_id = suggestion_id

    def __init__(self, config: AIDisplayConfig = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or AIDisplayConfig()
        self.logger = logger.get_logger("ai_display_widget")
        self.suggestion_cards: Dict[str, SuggestionCard] = {}
        self._mounted = False
        
        # 数据存储
        self._data_dir = os.path.join(".runtime", "ai_data")
        self._ensure_data_directory()
    
    async def on_mount(self) -> None:
        """组件挂载时的初始化"""
        self._mounted = True
        self.logger.info("AI显示组件已挂载")
    
    def _ensure_data_directory(self) -> None:
        """确保数据目录存在"""
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            os.makedirs(os.path.join(self._data_dir, "suggestions"), exist_ok=True)
        except Exception as e:
            self.logger.error(f"创建AI数据目录失败: {e}")
    
    def compose(self) -> ComposeResult:
        """组合AI显示组件"""
        # 过滤工具栏
        with Horizontal(classes="filter-bar"):
            # 类型过滤器
            type_options = [
                ("全部", "all"),
                ("技术分析", "technical"), 
                ("基本面", "fundamental"),
                ("风险评估", "risk"),
                ("通用", "general")
            ]
            yield Select(type_options, value="all", id="type_filter")
            
            # 清空按钮
            yield Button("清空", id="clear_button")
        
        # 建议显示容器
        with Vertical(classes="suggestion-container", id="suggestion_container"):
            # 空状态提示
            yield Static("暂无AI建议\n\n💡 使用AI助手功能\n开始获取智能建议", 
                        classes="empty-state", id="empty_state")
    
    async def add_suggestion(self, suggestion: AIDisplayItem) -> None:
        """添加新的AI建议"""
        try:
            # 检查是否已存在
            if suggestion.suggestion_id in [s.suggestion_id for s in self.suggestions]:
                self.logger.debug(f"建议已存在，跳过: {suggestion.suggestion_id}")
                return
            
            # 添加到建议列表
            new_suggestions = list(self.suggestions)
            new_suggestions.insert(0, suggestion)  # 新建议插入顶部
            
            # 限制最大数量
            if len(new_suggestions) > self.max_items:
                new_suggestions = new_suggestions[:self.max_items]
            
            self.suggestions = new_suggestions
            
            # 保存到本地存储
            await self._save_suggestion(suggestion)
            
            self.logger.info(f"添加AI建议: {suggestion.title} (置信度: {suggestion.confidence:.0%})")
            
            # 如果组件未挂载，手动触发刷新
            if hasattr(self, '_mounted') and self._mounted:
                await self._refresh_display()
            
        except Exception as e:
            self.logger.error(f"添加AI建议失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    async def update_suggestion_status(self, suggestion_id: str, status: SuggestionStatus) -> None:
        """更新建议状态"""
        try:
            updated_suggestions = []
            for suggestion in self.suggestions:
                if suggestion.suggestion_id == suggestion_id:
                    # 创建新的建议对象，更新状态
                    updated_suggestion = AIDisplayItem(
                        suggestion_id=suggestion.suggestion_id,
                        suggestion_type=suggestion.suggestion_type,
                        title=suggestion.title,
                        content=suggestion.content,
                        confidence=suggestion.confidence,
                        timestamp=suggestion.timestamp,
                        status=status,
                        stock_code=suggestion.stock_code
                    )
                    updated_suggestions.append(updated_suggestion)
                    
                    # 保存更新
                    await self._save_suggestion(updated_suggestion)
                else:
                    updated_suggestions.append(suggestion)
            
            self.suggestions = updated_suggestions
            self.logger.info(f"更新建议状态: {suggestion_id} -> {status.value}")
            
        except Exception as e:
            self.logger.error(f"更新建议状态失败: {e}")
    
    async def watch_suggestions(self, suggestions: List[AIDisplayItem]) -> None:
        """建议列表变化时重新渲染"""
        await self._refresh_display()
    
    async def _refresh_display(self) -> None:
        """刷新显示"""
        try:
            # 获取过滤后的建议
            filtered_suggestions = self._get_filtered_suggestions()
            
            # 查找容器和空状态组件
            try:
                container = self.query_one("#suggestion_container")
                empty_state = self.query_one("#empty_state")
            except Exception as query_error:
                self.logger.error(f"查找UI组件失败: {query_error}")
                return
            
            # 移除所有建议卡片
            for card in self.suggestion_cards.values():
                try:
                    if card.parent:
                        await card.remove()
                except Exception:
                    pass  # 忽略移除失败的情况
            self.suggestion_cards.clear()
            
            # 显示空状态或建议
            if filtered_suggestions:
                empty_state.display = False
                
                # 添加新的建议卡片
                for suggestion in filtered_suggestions:
                    try:
                        card = SuggestionCard(suggestion)
                        self.suggestion_cards[suggestion.suggestion_id] = card
                        await container.mount(card)
                    except Exception as mount_error:
                        self.logger.error(f"挂载建议卡片失败: {mount_error}")
            else:
                empty_state.display = True
            
            self.logger.debug(f"刷新显示完成，显示 {len(filtered_suggestions)} 个建议")
                
        except Exception as e:
            self.logger.error(f"刷新显示失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _get_filtered_suggestions(self) -> List[AIDisplayItem]:
        """获取过滤后的建议"""
        filtered = list(self.suggestions)
        
        # 类型过滤
        if self.current_filter != "all":
            filtered = [s for s in filtered if s.suggestion_type.value == self.current_filter]
        
        # 置信度过滤
        filtered = [s for s in filtered if s.confidence >= self.config.confidence_threshold]
        
        # 是否显示已忽略的项目
        if not self.config.show_ignored_items:
            filtered = [s for s in filtered if s.status != SuggestionStatus.IGNORED]
        
        return filtered
    
    async def on_select_changed(self, event: Select.Changed) -> None:
        """处理过滤器变化"""
        if event.select.id == "type_filter":
            self.current_filter = event.value
            await self._refresh_display()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "clear_button":
            await self.clear_suggestions()
    
    async def on_suggestion_card_suggestion_action(self, event: SuggestionCard.SuggestionAction) -> None:
        """处理建议操作"""
        suggestion_id = event.suggestion_id
        action = event.action
        
        try:
            if action == "accept":
                await self.update_suggestion_status(suggestion_id, SuggestionStatus.ACCEPTED)
                self.post_message(self.SuggestionAccepted(suggestion_id))
            elif action == "ignore":
                await self.update_suggestion_status(suggestion_id, SuggestionStatus.IGNORED)
                self.post_message(self.SuggestionIgnored(suggestion_id))
            elif action == "save":
                await self.update_suggestion_status(suggestion_id, SuggestionStatus.SAVED)
                self.post_message(self.SuggestionSaved(suggestion_id))
                
        except Exception as e:
            self.logger.error(f"处理建议操作失败: {e}")
    
    async def clear_suggestions(self) -> None:
        """清空所有建议"""
        self.suggestions = []
        self.logger.info("清空所有AI建议")
    
    def get_suggestion_count(self) -> int:
        """获取当前显示的建议数量"""
        return len(self._get_filtered_suggestions())
    
    def set_filter(self, filter_type: str) -> None:
        """设置建议筛选类型"""
        self.current_filter = filter_type
    
    async def _save_suggestion(self, suggestion: AIDisplayItem) -> None:
        """保存建议到本地存储"""
        try:
            date_str = suggestion.timestamp.strftime("%Y-%m-%d")
            file_path = os.path.join(self._data_dir, "suggestions", f"{date_str}.json")
            
            # 读取现有数据
            suggestions_data = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    suggestions_data = json.load(f)
            
            # 更新或添加建议
            suggestion_dict = {
                'suggestion_id': suggestion.suggestion_id,
                'suggestion_type': suggestion.suggestion_type.value,
                'title': suggestion.title,
                'content': suggestion.content,
                'confidence': suggestion.confidence,
                'timestamp': suggestion.timestamp.isoformat(),
                'status': suggestion.status.value,
                'stock_code': suggestion.stock_code
            }
            
            # 查找现有建议并更新，或添加新建议
            found = False
            for i, existing in enumerate(suggestions_data):
                if existing.get('suggestion_id') == suggestion.suggestion_id:
                    suggestions_data[i] = suggestion_dict
                    found = True
                    break
            
            if not found:
                suggestions_data.append(suggestion_dict)
            
            # 保存数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(suggestions_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"保存建议失败: {e}")
    
    def export_suggestions(self, format: str = "json") -> str:
        """导出建议数据"""
        try:
            if format == "json":
                suggestions_data = []
                for suggestion in self.suggestions:
                    suggestions_data.append({
                        'suggestion_id': suggestion.suggestion_id,
                        'suggestion_type': suggestion.suggestion_type.value,
                        'title': suggestion.title,
                        'content': suggestion.content,
                        'confidence': suggestion.confidence,
                        'timestamp': suggestion.timestamp.isoformat(),
                        'status': suggestion.status.value,
                        'stock_code': suggestion.stock_code
                    })
                return json.dumps(suggestions_data, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            self.logger.error(f"导出建议失败: {e}")
            return ""


# 便捷函数
def create_ai_suggestion_from_response(user_input: str, ai_response: str, stock_code: str = "") -> AIDisplayItem:
    """从AI回复创建建议项"""
    suggestion_type = _classify_suggestion_type(user_input)
    confidence = _calculate_confidence(ai_response)
    title = _extract_title(ai_response)
    content = _extract_key_points(ai_response)
    
    return AIDisplayItem(
        suggestion_id=str(uuid.uuid4()),
        suggestion_type=suggestion_type,
        title=title,
        content=content,
        confidence=confidence,
        timestamp=datetime.now(),
        stock_code=stock_code
    )


def _classify_suggestion_type(user_input: str) -> SuggestionType:
    """根据用户输入分类建议类型"""
    technical_keywords = ['RSI', 'MACD', '技术分析', '图表', '趋势', '均线', 'KDJ']
    fundamental_keywords = ['财报', '估值', 'PE', 'PB', '基本面', '市值', 'ROE']
    risk_keywords = ['风险', '回调', '止损', '仓位', '预警', '控制']
    
    input_lower = user_input.lower()
    if any(keyword in input_lower for keyword in technical_keywords):
        return SuggestionType.TECHNICAL
    elif any(keyword in input_lower for keyword in fundamental_keywords):
        return SuggestionType.FUNDAMENTAL
    elif any(keyword in input_lower for keyword in risk_keywords):
        return SuggestionType.RISK
    else:
        return SuggestionType.GENERAL


def _calculate_confidence(ai_response: str) -> float:
    """根据AI回复内容计算置信度"""
    confidence_indicators = ['建议', '推荐', '应该', '可以考虑', '明确']
    uncertainty_indicators = ['可能', '或许', '不确定', '需要观察', '谨慎']
    
    confidence_score = 0.6  # 基础分数
    for indicator in confidence_indicators:
        if indicator in ai_response:
            confidence_score += 0.1
    for indicator in uncertainty_indicators:
        if indicator in ai_response:
            confidence_score -= 0.1
    
    return max(0.1, min(1.0, confidence_score))


def _extract_title(ai_response: str) -> str:
    """从AI回复中提取标题"""
    lines = ai_response.strip().split('\n')
    if lines:
        # 取第一行作为标题，限制长度
        title = lines[0].strip()
        if len(title) > 30:
            title = title[:27] + "..."
        return title
    return "AI建议"


def _extract_key_points(ai_response: str) -> str:
    """从AI回复中提取关键要点"""
    # 简化处理，限制长度
    content = ai_response.strip()
    if len(content) > 100:
        content = content[:97] + "..."
    return content