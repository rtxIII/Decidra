
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any

# 订单相关常量定义
ORDER_TYPES = [
    ("NORMAL", "限价单"),
    ("MARKET", "市价单"),
    ("STOP", "止损单"),
    ("STOP_LIMIT", "止损限价单"),
    ("ABSOLUTE_LIMIT", "绝对限价单"),
    ("AUCTION", "竞价单"),
    ("AUCTION_LIMIT", "竞价限价单"),
    ("SPECIAL_LIMIT", "特别限价单")
]

TRD_SIDES = [
    ("BUY", "买入"),
    ("SELL", "卖出")
]

TRD_ENVS = [
    ("SIMULATE", "模拟环境"),
    ("REAL", "真实环境")
]

MARKETS = [
    ("HK", "港股"),
    ("US", "美股"),
    ("CN", "A股")
]

TIME_IN_FORCE = [
    ("DAY", "当日有效"),
    ("GTC", "撤销前有效"),
    ("IOC", "立即成交或撤销"),
    ("FOK", "全额成交或撤销")
]


# 数据结构定义
@dataclass
class OrderData:
    """订单数据结构"""
    code: str                           # 股票代码
    price: float                        # 价格
    qty: int                           # 数量
    order_type: str = "NORMAL"         # 订单类型
    trd_side: str = "BUY"             # 交易方向
    trd_env: str = "SIMULATE"         # 交易环境
    market: str = "HK"                # 市场
    aux_price: Optional[float] = None  # 辅助价格
    time_in_force: str = "DAY"        # 有效期
    remark: str = ""                  # 备注


@dataclass
class ModifyOrderData:
    """改单数据结构"""
    order_id: str                      # 订单ID
    price: Optional[float] = None      # 新价格
    qty: Optional[int] = None          # 新数量
    aux_price: Optional[float] = None  # 新辅助价格

