"""
富途 OpenAPI 基础类定义

包含异常类、数据模型类和配置类等基础定义。
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全地将值转换为浮点数
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
        
    Returns:
        float: 转换后的浮点数
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # 处理常见的无效值
        if value.strip().upper() in ('N/A', 'NA', '', 'NULL', 'NONE'):
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ================== 异常类 ==================

class FutuException(Exception):
    """富途API基础异常"""
    
    def __init__(self, ret_code: int, ret_msg: str, detail: str = ""):
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.detail = detail
        super().__init__(f"FutuError[{ret_code}]: {ret_msg} {detail}".strip())


class FutuConnectException(FutuException):
    """连接异常"""
    pass


class FutuTradeException(FutuException):
    """交易异常"""
    pass


class FutuQuoteException(FutuException):
    """行情异常"""
    pass


# ================== 数据模型 ==================

@dataclass
class StockInfo:
    """股票基础信息 - 对应 get_stock_basicinfo 返回"""
    code: str                    # 股票代码
    name: str                    # 股票名称  
    stock_type: str             # 股票类型
    list_time: str              # 上市时间
    stock_id: int               # 股票ID
    lot_size: int               # 每手股数
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StockInfo':
        """从字典创建StockInfo对象"""
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            stock_type=data.get('stock_type', ''),
            list_time=data.get('list_time', ''),
            stock_id=data.get('stock_id', 0),
            lot_size=data.get('lot_size', 0)
        )


@dataclass  
class KLineData:
    """K线数据 - 对应 get_cur_kline 返回"""
    code: str                   # 股票代码
    time_key: str              # 时间
    open: float                # 开盘价
    close: float               # 收盘价
    high: float                # 最高价
    low: float                 # 最低价
    volume: int                # 成交量
    turnover: float            # 成交额
    pe_ratio: Optional[float] = None   # 市盈率
    turnover_rate: Optional[float] = None  # 换手率
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KLineData':
        """从字典创建KLineData对象"""
        return cls(
            code=data.get('code', ''),
            time_key=data.get('time_key', ''),
            open=safe_float(data.get('open', 0)),
            close=safe_float(data.get('close', 0)),
            high=safe_float(data.get('high', 0)),
            low=safe_float(data.get('low', 0)),
            volume=int(data.get('volume', 0)),
            turnover=safe_float(data.get('turnover', 0)),
            pe_ratio=data.get('pe_ratio'),
            turnover_rate=data.get('turnover_rate')
        )


@dataclass
class StockQuote:
    """股票报价 - 对应 get_stock_quote 返回"""
    code: str                  # 股票代码
    data_date: str            # 数据日期
    data_time: str            # 数据时间
    last_price: float         # 最新价
    open_price: float         # 开盘价
    high_price: float         # 最高价
    low_price: float          # 最低价
    prev_close_price: float   # 昨收价
    volume: int               # 成交量
    turnover: float           # 成交额
    turnover_rate: Optional[float] = None      # 换手率
    suspension: bool = False          # 是否停牌
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StockQuote':
        """从字典创建StockQuote对象"""
        return cls(
            code=data.get('code', ''),
            data_date=data.get('data_date', ''),
            data_time=data.get('data_time', ''),
            last_price=safe_float(data.get('last_price', 0)),
            open_price=safe_float(data.get('open_price', 0)),
            high_price=safe_float(data.get('high_price', 0)),
            low_price=safe_float(data.get('low_price', 0)),
            prev_close_price=safe_float(data.get('prev_close_price', 0)),
            volume=int(data.get('volume', 0)),
            turnover=safe_float(data.get('turnover', 0)),
            turnover_rate=data.get('turnover_rate'),
            suspension=bool(data.get('suspension', False))
        )


@dataclass
class MarketSnapshot:
    """市场快照 - 对应 get_market_snapshot 返回"""
    code: str                  # 股票代码
    update_time: str          # 更新时间
    last_price: float         # 最新价
    open_price: float         # 开盘价
    high_price: float         # 最高价
    low_price: float          # 最低价
    prev_close_price: float   # 昨收价
    volume: int               # 成交量
    turnover: float           # 成交额
    turnover_rate: Optional[float] = None  # 换手率
    amplitude: Optional[float] = None      # 振幅
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MarketSnapshot':
        """从字典创建MarketSnapshot对象"""
        return cls(
            code=data.get('code', ''),
            update_time=data.get('update_time', ''),
            last_price=safe_float(data.get('last_price', 0)),
            open_price=safe_float(data.get('open_price', 0)),
            high_price=safe_float(data.get('high_price', 0)),
            low_price=safe_float(data.get('low_price', 0)),
            prev_close_price=safe_float(data.get('prev_close_price', 0)),
            volume=int(data.get('volume', 0)),
            turnover=safe_float(data.get('turnover', 0)),
            turnover_rate=data.get('turnover_rate'),
            amplitude=data.get('amplitude')
        )


@dataclass
class TickerData:
    """逐笔数据 - 对应 get_rt_ticker 返回"""
    code: str                  # 股票代码
    sequence: int             # 序列号
    time: str                 # 成交时间
    price: float              # 成交价
    volume: int               # 成交量
    turnover: float           # 成交额
    ticker_direction: str     # 买卖方向
    type: str                 # 成交类型
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TickerData':
        """从字典创建TickerData对象"""
        return cls(
            code=data.get('code', ''),
            sequence=int(data.get('sequence', 0)),
            time=data.get('time', ''),
            price=safe_float(data.get('price', 0)),
            volume=int(data.get('volume', 0)),
            turnover=safe_float(data.get('turnover', 0)),
            ticker_direction=data.get('ticker_direction', ''),
            type=data.get('type', '')
        )


@dataclass
class OrderBookData:
    """买卖盘数据 - 对应 get_order_book 返回"""
    code: str                  # 股票代码
    svr_recv_time_bid: str    # 买盘服务器接收时间
    svr_recv_time_ask: str    # 卖盘服务器接收时间
    # 买盘档位 (Bid1-Bid10)
    bid_price_1: float = 0.0
    bid_volume_1: int = 0
    bid_price_2: float = 0.0
    bid_volume_2: int = 0
    bid_price_3: float = 0.0
    bid_volume_3: int = 0
    bid_price_4: float = 0.0
    bid_volume_4: int = 0
    bid_price_5: float = 0.0
    bid_volume_5: int = 0
    bid_price_6: float = 0.0
    bid_volume_6: int = 0
    bid_price_7: float = 0.0
    bid_volume_7: int = 0
    bid_price_8: float = 0.0
    bid_volume_8: int = 0
    bid_price_9: float = 0.0
    bid_volume_9: int = 0
    bid_price_10: float = 0.0
    bid_volume_10: int = 0

    # 卖盘档位 (Ask1-Ask10)  
    ask_price_1: float = 0.0
    ask_volume_1: int = 0
    ask_price_2: float = 0.0
    ask_volume_2: int = 0
    ask_price_3: float = 0.0
    ask_volume_3: int = 0
    ask_price_4: float = 0.0
    ask_volume_4: int = 0
    ask_price_5: float = 0.0
    ask_volume_5: int = 0
    ask_price_6: float = 0.0
    ask_volume_6: int = 0
    ask_price_7: float = 0.0
    ask_volume_7: int = 0
    ask_price_8: float = 0.0
    ask_volume_8: int = 0
    ask_price_9: float = 0.0
    ask_volume_9: int = 0
    ask_price_10: float = 0.0
    ask_volume_10: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OrderBookData':
        """从字典创建OrderBookData对象"""
        return cls(
            code=data.get('code', ''),
            svr_recv_time_bid=data.get('svr_recv_time_bid', ''),
            svr_recv_time_ask=data.get('svr_recv_time_ask', ''),
            bid_price_1=safe_float(data.get('Bid1', 0)),
            bid_volume_1=int(data.get('BidVol1', 0)),
            bid_price_2=safe_float(data.get('Bid2', 0)),
            bid_volume_2=int(data.get('BidVol2', 0)),
            bid_price_3=safe_float(data.get('Bid3', 0)),
            bid_volume_3=int(data.get('BidVol3', 0)),
            bid_price_4=safe_float(data.get('Bid4', 0)),
            bid_volume_4=int(data.get('BidVol4', 0)),
            bid_price_5=safe_float(data.get('Bid5', 0)),
            bid_volume_5=int(data.get('BidVol5', 0)),
            bid_price_6=safe_float(data.get('Bid6', 0)),
            bid_volume_6=int(data.get('BidVol6', 0)),
            bid_price_7=safe_float(data.get('Bid7', 0)),
            bid_volume_7=int(data.get('BidVol7', 0)),
            bid_price_8=safe_float(data.get('Bid8', 0)),
            bid_volume_8=int(data.get('BidVol8', 0)),
            bid_price_9=safe_float(data.get('Bid9', 0)),
            bid_volume_9=int(data.get('BidVol9', 0)),
            bid_price_10=safe_float(data.get('Bid10', 0)),
            bid_volume_10=int(data.get('BidVol10', 0)),
            ask_price_1=safe_float(data.get('Ask1', 0)),
            ask_volume_1=int(data.get('AskVol1', 0)),
            ask_price_2=safe_float(data.get('Ask2', 0)),
            ask_volume_2=int(data.get('AskVol2', 0)),
            ask_price_3=safe_float(data.get('Ask3', 0)),
            ask_volume_3=int(data.get('AskVol3', 0)),
            ask_price_4=safe_float(data.get('Ask4', 0)),
            ask_volume_4=int(data.get('AskVol4', 0)),
            ask_price_5=safe_float(data.get('Ask5', 0)),
            ask_volume_5=int(data.get('AskVol5', 0)),
            ask_price_6=safe_float(data.get('Ask6', 0)),
            ask_volume_6=int(data.get('AskVol6', 0)),
            ask_price_7=safe_float(data.get('Ask7', 0)),
            ask_volume_7=int(data.get('AskVol7', 0)),
            ask_price_8=safe_float(data.get('Ask8', 0)),
            ask_volume_8=int(data.get('AskVol8', 0)),
            ask_price_9=safe_float(data.get('Ask9', 0)),
            ask_volume_9=int(data.get('AskVol9', 0)),
            ask_price_10=safe_float(data.get('Ask10', 0)),
            ask_volume_10=int(data.get('AskVol10', 0))

        )


@dataclass
class RTData:
    """分时数据 - 对应 get_rt_data 返回"""
    code: str                  # 股票代码
    time: str                 # 时间
    is_blank: bool            # 是否为空数据
    opened_mins: int          # 零点到当前多少分钟
    cur_price: float          # 当前价格
    last_close: float         # 昨日收盘价
    avg_price: float          # 平均价格
    volume: int               # 成交量
    turnover: float           # 成交额
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RTData':
        """从字典创建RTData对象"""
        return cls(
            code=data.get('code', ''),
            time=data.get('time', ''),
            is_blank=bool(data.get('is_blank', False)),
            opened_mins=int(data.get('opened_mins', 0)),
            cur_price=safe_float(data.get('cur_price', 0)),
            last_close=safe_float(data.get('last_close', 0)),
            avg_price=safe_float(data.get('avg_price', 0)),
            volume=int(data.get('volume', 0)),
            turnover=safe_float(data.get('turnover', 0))
        )


@dataclass
class AuTypeInfo:
    """复权信息 - 对应 get_autype_list 返回"""
    code: str                  # 股票代码
    ex_div_date: str          # 除权除息日
    split_ratio: float        # 拆股比例
    per_cash_div: float       # 每股现金股息
    per_share_div_ratio: float # 每股派股比例
    per_share_trans_ratio: float # 每股转增股比例
    allot_ratio: float        # 每股配股比例
    allot_price: float        # 配股价
    stk_spo_ratio: float      # 增发比例
    stk_spo_price: float      # 增发价格
    forward_adj_factorA: float # 前复权因子A
    forward_adj_factorB: float # 前复权因子B
    backward_adj_factorA: float # 后复权因子A
    backward_adj_factorB: float # 后复权因子B
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AuTypeInfo':
        """从字典创建AuTypeInfo对象"""
        return cls(
            code=data.get('code', ''),
            ex_div_date=data.get('ex_div_date', ''),
            split_ratio=safe_float(data.get('split_ratio', 0)),
            per_cash_div=safe_float(data.get('per_cash_div', 0)),
            per_share_div_ratio=safe_float(data.get('per_share_div_ratio', 0)),
            per_share_trans_ratio=safe_float(data.get('per_share_trans_ratio', 0)),
            allot_ratio=safe_float(data.get('allot_ratio', 0)),
            allot_price=safe_float(data.get('allot_price', 0)),
            stk_spo_ratio=safe_float(data.get('stk_spo_ratio', 0)),
            stk_spo_price=safe_float(data.get('stk_spo_price', 0)),
            forward_adj_factorA=safe_float(data.get('forward_adj_factorA', 0)),
            forward_adj_factorB=safe_float(data.get('forward_adj_factorB', 0)),
            backward_adj_factorA=safe_float(data.get('backward_adj_factorA', 0)),
            backward_adj_factorB=safe_float(data.get('backward_adj_factorB', 0))
        )


@dataclass
class PlateInfo:
    """板块信息 - 对应 get_plate_list 返回"""
    plate_code: str           # 板块代码
    plate_name: str           # 板块名称
    plate_type: str           # 板块类型
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlateInfo':
        """从字典创建PlateInfo对象"""
        return cls(
            plate_code=data.get('code', ''),
            plate_name=data.get('plate_name', ''),
            plate_type=data.get('plate_type', '')
        )


@dataclass  
class PlateStock:
    """板块股票信息 - 对应 get_plate_stock 返回"""
    code: str                 # 股票代码
    lot_size: int            # 每手股数
    stock_name: str          # 股票名称
    stock_owner: str         # 所属正股的代码
    stock_child_type: str    # 股票子类型
    stock_type: str          # 股票类型
    list_time: str           # 上市时间
    stock_id: int            # 股票ID
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlateStock':
        """从字典创建PlateStock对象"""
        return cls(
            code=data.get('code', ''),
            lot_size=int(data.get('lot_size', 0)),
            stock_name=data.get('stock_name', ''),
            stock_owner=data.get('stock_owner', ''),
            stock_child_type=data.get('stock_child_type', ''),
            stock_type=data.get('stock_type', ''),
            list_time=data.get('list_time', ''),
            stock_id=int(data.get('stock_id', 0))
        )


# ================== 配置类 ==================

@dataclass
class FutuConfig:
    """富途API配置管理类"""
    
    # FutuOpenD连接配置
    host: str = "127.0.0.1"
    port: int = 11111
    
    # 交易密码 (用于unlock_trade)
    trade_pwd: str = ""
    trade_pwd_md5: str = ""
    
    # 默认交易环境
    default_trd_env: str = "SIMULATE"  # SIMULATE / REAL
    
    # 连接超时设置
    timeout: int = 30
    
    # 协议加密设置
    enable_proto_encrypt: bool = False
    
    # 日志设置
    log_level: str = "INFO"
    
    # 其他配置
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    reconnect_interval: int = 5
    
    def __post_init__(self):
        """配置验证和初始化"""
        self._validate_config()
        if self.trade_pwd and not self.trade_pwd_md5:
            self.trade_pwd_md5 = self._generate_md5(self.trade_pwd)
    
    def _validate_config(self):
        """验证配置参数"""
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}. Port must be between 1 and 65535.")
        
        if self.default_trd_env not in ["SIMULATE", "REAL"]:
            raise ValueError(f"Invalid trd_env: {self.default_trd_env}")
        
        if self.timeout <= 0:
            raise ValueError(f"Invalid timeout: {self.timeout}")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError(f"Invalid log_level: {self.log_level}")
    
    @staticmethod
    def _generate_md5(password: str) -> str:
        """生成密码的MD5值"""
        return hashlib.md5(password.encode('utf-8')).hexdigest()
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'FutuConfig':
        """从配置文件加载配置"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 提取futu相关配置
            futu_config = config_data.get('futu', {})
            return cls(**futu_config)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config: {e}")
    
    @classmethod
    def from_env(cls) -> 'FutuConfig':
        """从环境变量加载配置"""
        env_mapping = {
            'FUTU_HOST': 'host',
            'FUTU_PORT': 'port',
            'FUTU_TRADE_PWD': 'trade_pwd',
            'FUTU_TRADE_PWD_MD5': 'trade_pwd_md5',
            'FUTU_TRD_ENV': 'default_trd_env',
            'FUTU_TIMEOUT': 'timeout',
            'FUTU_ENCRYPT': 'enable_proto_encrypt',
            'FUTU_LOG_LEVEL': 'log_level',
        }
        
        config_data = {}
        for env_key, config_key in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 类型转换
                if config_key in ['port', 'timeout', 'max_reconnect_attempts', 'reconnect_interval']:
                    config_data[config_key] = int(env_value)
                elif config_key in ['enable_proto_encrypt', 'auto_reconnect']:
                    config_data[config_key] = env_value.lower() in ['true', '1', 'yes']
                else:
                    config_data[config_key] = env_value
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'host': self.host,
            'port': self.port,
            'trade_pwd': self.trade_pwd,
            'trade_pwd_md5': self.trade_pwd_md5,
            'default_trd_env': self.default_trd_env,
            'timeout': self.timeout,
            'enable_proto_encrypt': self.enable_proto_encrypt,
            'log_level': self.log_level,
            'auto_reconnect': self.auto_reconnect,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'reconnect_interval': self.reconnect_interval,
        }
    
    def save_to_file(self, config_path: Union[str, Path]):
        """保存配置到文件"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {'futu': self.to_dict()}
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)


@dataclass
class MarketState:
    """市场状态信息 - 对应 get_market_state 返回"""
    code: str = ''                  # 股票代码
    market_state: str = 'CLOSE'     # 市场状态
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MarketState':
        """从字典创建MarketState对象"""
        return cls(
            code=data.get('code', ''),
            market_state=data.get('market_state', 'CLOSE')
        )


@dataclass
class GlobalMarketState:
    """全局市场状态信息 - 对应 get_global_state 返回"""
    market_hk: Optional[str] = 'CLOSE'        # 港股市场状态
    market_us: Optional[str] = 'CLOSE'        # 美股市场状态
    market_sh: Optional[str] = 'CLOSE'        # 上海市场状态
    market_sz: Optional[str] = 'CLOSE'        # 深圳市场状态
    market_hkfuture: Optional[str] = 'CLOSE'  # 港股期货状态
    market_usfuture: Optional[str] = 'CLOSE'  # 美股期货状态
    market_sgfuture: Optional[str] = 'CLOSE'  # 新加坡期货状态
    market_jpfuture: Optional[str] = 'CLOSE'  # 日本期货状态
    server_ver: str = ''                      # OpenD版本号
    trd_logined: bool = False                 # 交易服务器登录状态
    qot_logined: bool = False                 # 行情服务器登录状态
    timestamp: float = 0.0                    # 格林威治时间戳
    local_timestamp: float = 0.0              # OpenD机器本地时间戳
    program_status_type: str = ''             # 程序当前状态
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalMarketState':
        """从字典创建GlobalMarketState对象"""
        return cls(
            market_hk=data.get('market_hk', 'CLOSE'),
            market_us=data.get('market_us', 'CLOSE'),
            market_sh=data.get('market_sh', 'CLOSE'),
            market_sz=data.get('market_sz', 'CLOSE'),
            market_hkfuture=data.get('market_hkfuture', 'CLOSE'),
            market_usfuture=data.get('market_usfuture', 'CLOSE'),
            market_sgfuture=data.get('market_sgfuture', 'CLOSE'),
            market_jpfuture=data.get('market_jpfuture', 'CLOSE'),
            server_ver=data.get('server_ver', ''),
            trd_logined=data.get('trd_logined', False),
            qot_logined=data.get('qot_logined', False),
            timestamp=safe_float(data.get('timestamp', 0.0)),
            local_timestamp=safe_float(data.get('local_timestamp', 0.0)),
            program_status_type=data.get('program_status_type', '')
        )


@dataclass
class CapitalFlow:
    """资金流向数据 - 对应 get_capital_flow 返回"""
    code: str                        # 股票代码
    in_flow: float                  # 整体净流入
    main_in_flow: float             # 主力大单净流入
    super_in_flow: float            # 特大单净流入
    big_in_flow: float              # 大单净流入
    mid_in_flow: float              # 中单净流入
    sml_in_flow: float              # 小单净流入
    capital_flow_item_time: str = '' # 开始时间
    last_valid_time: str = ''       # 数据最后有效时间
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CapitalFlow':
        """从字典创建CapitalFlow对象"""
        return cls(
            code=data.get('code', ''),
            in_flow=safe_float(data.get('in_flow', 0)),
            main_in_flow=safe_float(data.get('main_in_flow', 0)),
            super_in_flow=safe_float(data.get('super_in_flow', 0)),
            big_in_flow=safe_float(data.get('big_in_flow', 0)),
            mid_in_flow=safe_float(data.get('mid_in_flow', 0)),
            sml_in_flow=safe_float(data.get('sml_in_flow', 0)),
            capital_flow_item_time=data.get('capital_flow_item_time', ''),
            last_valid_time=data.get('last_valid_time', '')
        )


@dataclass
class CapitalDistribution:
    """资金分布数据 - 对应 get_capital_distribution 返回"""
    code: str                     # 股票代码
    capital_in_super: float      # 流入资金额度，特大单
    capital_in_big: float        # 流入资金额度，大单
    capital_in_mid: float        # 流入资金额度，中单
    capital_in_small: float      # 流入资金额度，小单
    capital_out_super: float     # 流出资金额度，特大单
    capital_out_big: float       # 流出资金额度，大单
    capital_out_mid: float       # 流出资金额度，中单
    capital_out_small: float     # 流出资金额度，小单
    update_time: str             # 更新时间字符串
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CapitalDistribution':
        """从字典创建CapitalDistribution对象"""
        return cls(
            code=data.get('code', ''),
            capital_in_super=safe_float(data.get('capital_in_super', 0)),
            capital_in_big=safe_float(data.get('capital_in_big', 0)),
            capital_in_mid=safe_float(data.get('capital_in_mid', 0)),
            capital_in_small=safe_float(data.get('capital_in_small', 0)),
            capital_out_super=safe_float(data.get('capital_out_super', 0)),
            capital_out_big=safe_float(data.get('capital_out_big', 0)),
            capital_out_mid=safe_float(data.get('capital_out_mid', 0)),
            capital_out_small=safe_float(data.get('capital_out_small', 0)),
            update_time=data.get('update_time', '')
        )


@dataclass
class BrokerQueueData:
    """经纪队列数据 - 对应 get_broker_queue 返回"""
    code: str                    # 股票代码
    bid_frame_table: Dict[str, Any]  # 买盘经纪队列数据
    ask_frame_table: Dict[str, Any]  # 卖盘经纪队列数据
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BrokerQueueData':
        """从字典创建BrokerQueueData对象"""
        return cls(
            code=data.get('code', ''),
            bid_frame_table=data.get('bid_frame_table', {}),
            ask_frame_table=data.get('ask_frame_table', {})
        )


@dataclass
class OwnerPlate:
    """股票所属板块信息 - 对应 get_owner_plate 返回"""
    code: str                  # 股票代码
    plate_code: str           # 板块代码  
    plate_name: str           # 板块名称
    plate_type: str           # 板块类型
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OwnerPlate':
        """从字典创建OwnerPlate对象"""
        return cls(
            code=data.get('code', ''),
            plate_code=data.get('plate_code', ''),
            plate_name=data.get('plate_name', ''),
            plate_type=data.get('plate_type', '')
        )
