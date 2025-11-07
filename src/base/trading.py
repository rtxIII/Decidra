from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class TradingOrder:
    """交易订单数据结构"""
    stock_code: str                 # 股票代码 (如: HK.00700)
    action: str                     # 买卖方向: 'buy' 或 'sell'
    quantity: int                   # 交易数量
    price: Optional[float] = None   # 委托价格 (None表示市价)
    order_type: str = 'MARKET'      # 订单类型: 'MARKET', 'NORMAL', 'STOP', 'STOP_LIMIT'
    trigger_price: Optional[float] = None  # 触发价格 (用于止盈止损)
    confidence: float = 0.0         # AI解析置信度 (0-1)
    reasoning: str = ""             # 解析推理过程
    warnings: List[str] = field(default_factory=list)  # 警告信息


@dataclass
class TradingAdvice:
    """AI交易建议数据结构"""
    advice_id: str                  # 建议ID
    user_prompt: str                # 用户原始输入
    stock_code: str                 # 目标股票代码
    stock_name: str                 # 股票名称
    advice_summary: str             # 建议摘要
    detailed_analysis: str          # 详细分析
    recommended_action: str         # 推荐操作: 'buy', 'sell', 'hold', 'wait'
    suggested_orders: List[TradingOrder] = field(default_factory=list)  # 建议的具体订单
    risk_assessment: str = "中"      # 风险评估: '低', '中', '高'
    confidence_score: float = 0.0   # 建议置信度 (0-1)
    expected_return: Optional[str] = None  # 预期收益描述
    risk_factors: List[str] = field(default_factory=list)  # 风险因素
    key_points: List[str] = field(default_factory=list)    # 关键要点
    timestamp: datetime = field(default_factory=datetime.now)  # 生成时间
    expires_at: Optional[datetime] = None  # 建议过期时间
    status: str = "pending"         # 状态: 'pending', 'confirmed', 'executed', 'rejected'

