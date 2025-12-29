"""
监控系统基础数据模型
包含监控界面所需的所有数据类和枚举类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


# ==================== 枚举类型定义 ====================

class MarketStatus(Enum):
    """市场状态枚举"""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    PRE_MARKET = "PRE_MARKET"
    AFTER_MARKET = "AFTER_MARKET"


class SignalType(Enum):
    """交易信号枚举"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ColorStyle(Enum):
    """颜色样式枚举"""
    GREEN = "green"
    RED = "red"
    GRAY = "gray"
    WHITE = "white"
    YELLOW = "yellow"


class ConnectionStatus(Enum):
    """连接状态枚举"""
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    ERROR = "Error"


# ==================== 核心数据模型 ====================

@dataclass
class StockData:
    """股票实时数据模型"""
    code: str                    # 股票代码 (如: "HK.00700")
    name: str                    # 股票名称 (如: "腾讯控股")
    current_price: float         # 当前价格
    open_price: float           # 开盘价
    prev_close: float           # 昨收价
    change_rate: float          # 涨跌幅 (小数形式，如0.025表示2.5%)
    change_amount: float        # 涨跌额
    volume: int                 # 成交量
    turnover: float             # 成交额
    high_price: float           # 最高价
    low_price: float            # 最低价
    update_time: datetime       # 更新时间
    market_status: MarketStatus # 市场状态
    
    def __post_init__(self):
        """数据验证"""
        if self.current_price <= 0:
            raise ValueError(f"当前价格必须大于0: {self.current_price}")
        if self.volume < 0:
            raise ValueError(f"成交量不能为负数: {self.volume}")



@dataclass 
class TechnicalIndicators:
    """技术指标数据模型"""
    stock_code: str
    # 移动平均线
    ma5: Optional[float] = None
    ma10: Optional[float] = None  
    ma20: Optional[float] = None
    # RSI指标
    rsi14: Optional[float] = None
    rsi_signal: SignalType = SignalType.HOLD
    # MACD指标
    macd_line: Optional[float] = None
    signal_line: Optional[float] = None
    histogram: Optional[float] = None
    macd_signal: SignalType = SignalType.HOLD
    
    def __post_init__(self):
        """数据验证"""
        if self.rsi14 is not None and (self.rsi14 < 0 or self.rsi14 > 100):
            raise ValueError(f"RSI值必须在0-100之间: {self.rsi14}")


@dataclass
class MonitorConfig:
    """监控配置模型"""
    watch_list: List[str] = field(default_factory=list)  # 监控股票列表
    refresh_interval: int = 5    # 刷新间隔(秒)
    max_history_days: int = 30   # 历史数据保存天数
    indicators_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "ma": True, "rsi": True, "macd": True
    })
    
    def __post_init__(self):
        """配置验证"""
        if self.refresh_interval < 1:
            raise ValueError(f"刷新间隔必须大于0: {self.refresh_interval}")
        if self.max_history_days < 1:
            raise ValueError(f"历史数据天数必须大于0: {self.max_history_days}")


# ==================== UI数据模型 ====================

@dataclass
class TableRowData:
    """表格行数据模型"""
    stock_code: str
    stock_name: str
    current_price: str          # 格式化后的价格字符串
    change_rate: str            # 格式化后的涨跌幅 "+2.5%" 
    change_amount: str          # 格式化后的涨跌额 "+1.25"
    volume: str                 # 格式化后的成交量 "1.2M"
    update_time: str            # 格式化后的时间 "14:30:15"
    color_style: ColorStyle     # rich颜色样式
    is_selected: bool = False   # 是否被选中
    
    def __post_init__(self):
        """数据验证"""
        if not self.stock_code:
            raise ValueError("股票代码不能为空")
        if not self.stock_name:
            raise ValueError("股票名称不能为空")


@dataclass
class IndicatorDisplayData:
    """指标显示数据模型"""
    stock_code: str
    ma_text: str                # "MA5: 500.2  MA10: 498.5  MA20: 495.8"
    rsi_text: str               # "RSI: 65.2 [HOLD]"
    macd_text: str              # "MACD: 2.1  Signal: 1.8  [BUY]"
    ma_color: ColorStyle        # 根据价格与均线关系确定颜色
    rsi_color: ColorStyle       # 根据RSI值确定颜色
    macd_color: ColorStyle      # 根据MACD信号确定颜色


@dataclass  
class StatusBarData:
    """状态栏数据模型"""
    connection_status: ConnectionStatus
    last_update: str           # "Last update: 14:30:15"
    selected_stock: str        # "Selected: HK.00700"
    help_text: str = "Press 'h' for help, 'q' to quit"  # 默认帮助信息


class UIEventData:
    """界面事件数据"""
    KEY_QUIT = "q"
    KEY_REFRESH = "r" 
    KEY_ADD_STOCK = "n"
    KEY_DELETE_STOCK = "m"
    KEY_HELP = "h"
    KEY_UP = "up"
    KEY_DOWN = "down"
    KEY_ENTER = "enter"
    
    # 所有可用按键列表
    VALID_KEYS = {
        KEY_QUIT, KEY_REFRESH, KEY_ADD_STOCK, KEY_DELETE_STOCK, 
        KEY_HELP, KEY_UP, KEY_DOWN, KEY_ENTER
    }
    
    @classmethod
    def is_valid_key(cls, key: str) -> bool:
        """验证按键是否有效"""
        return key in cls.VALID_KEYS


# ==================== 数据处理相关模型 ====================

@dataclass
class DataUpdateResult:
    """数据更新结果"""
    success: bool
    stock_data: Dict[str, StockData]
    indicators_data: Dict[str, TechnicalIndicators]
    error_message: Optional[str] = None
    update_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CacheStats:
    """缓存统计信息"""
    cached_stocks: int
    total_memory_mb: float
    oldest_data: str
    cache_hit_rate: float
    api_calls_per_minute: int
    error_rate: float


@dataclass
class PerformanceMetrics:
    """性能指标"""
    api_call_count: int = 0
    api_response_time: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cache_hit_rate: float = 0.0
    error_count: int = 0
    
    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        return sum(self.api_response_time) / len(self.api_response_time) if self.api_response_time else 0.0
    
    def get_current_memory_usage(self) -> float:
        """获取当前内存使用量"""
        return self.memory_usage[-1] if self.memory_usage else 0.0


class ErrorCode:
    """错误代码定义"""
    NETWORK_ERROR = "E001"
    API_LIMIT_ERROR = "E002"
    PERMISSION_ERROR = "E003"
    DATA_ERROR = "E004"
    VALIDATION_ERROR = "E005"
    
    ERROR_MESSAGES = {
        "E001": "网络连接失败，正在重试...",
        "E002": "API请求频率限制，等待中...",
        "E003": "API权限不足，请检查配置",
        "E004": "数据格式错误，跳过此次更新",
        "E005": "数据验证失败，请检查数据源"
    }
    
    @classmethod
    def get_message(cls, error_code: str) -> str:
        """获取错误信息"""
        return cls.ERROR_MESSAGES.get(error_code, "未知错误")