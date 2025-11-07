from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AIAnalysisRequest:
    """AI分析请求"""
    stock_code: str
    analysis_type: str  # 'technical', 'fundamental', 'comprehensive'
    data_context: Dict[str, Any]
    user_question: Optional[str] = None
    language: str = 'zh-CN'


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
