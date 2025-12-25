from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


@dataclass
class AIRequest(ABC):
    """AI请求基类 - 统一所有AI请求的基础接口"""
    stock_code: str
    user_input: str  # 用户原始输入或问题
    context: Dict[str, Any] = field(default_factory=dict)
    language: str = 'zh-CN'

    @abstractmethod
    def get_request_type(self) -> str:
        """获取请求类型标识"""
        pass

    def get_stock_name(self) -> str:
        """从上下文中获取股票名称"""
        return self.context.get('stock_name', '未知')

    def get_basic_info(self) -> Dict[str, Any]:
        """获取基础信息"""
        return self.context.get('basic_info', {})

    def get_realtime_quote(self) -> Dict[str, Any]:
        """获取实时报价"""
        return self.context.get('realtime_quote', {})

    def get_technical_indicators(self) -> Dict[str, Any]:
        """获取技术指标"""
        return self.context.get('technical_indicators', {})

    def get_capital_flow(self) -> Dict[str, Any]:
        """获取资金流向"""
        return self.context.get('capital_flow', {})

    def get_orderbook(self) -> Dict[str, Any]:
        """获取五档买卖盘数据"""
        return self.context.get('orderbook', {})


@dataclass
class AIAnalysisRequest(AIRequest):
    """AI分析请求 - 用于股票技术/基本面分析"""
    analysis_type: str = 'comprehensive'  # 'technical', 'fundamental', 'comprehensive'

    def get_request_type(self) -> str:
        return 'analysis'


@dataclass
class AITradingAdviceRequest(AIRequest):
    """AI交易建议请求 - 用于生成可执行的交易建议"""
    available_funds: float = 0.0
    current_position: str = "无持仓"
    risk_preference: str = "中等"  # '保守', '中等', '激进'

    def get_request_type(self) -> str:
        return 'trading_advice'

    def get_available_funds(self) -> float:
        """获取可用资金"""
        return self.context.get('available_funds', self.available_funds)

    def get_current_position(self) -> str:
        """获取当前持仓"""
        return self.context.get('current_position', self.current_position)


@dataclass
class AIAnalysisResponse:
    """AI分析响应"""
    request_id: str
    stock_code: str
    analysis_type: str
    content: str
    key_points: List[str]
    recommendation: str
    confidence_score: float
    risk_level: str
    timestamp: datetime
