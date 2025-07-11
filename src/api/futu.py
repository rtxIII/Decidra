"""
富途 OpenAPI 封装模块

基于富途官方SDK的高级封装，提供更简洁易用的API接口。
依赖：futu-api >= 6.0.0
需要：FutuOpenD网关程序运行

这是主入口文件，导入了所有拆分的子模块。
"""

try:
    import futu as ft
except ImportError:
    raise ImportError(
        "futu-api is required. Install it with: pip install futu-api"
    )

ft.set_futu_debug_model(False)

# 导入所有子模块
from .futu_client import FutuClient
from .futu_quote import QuoteManager
from .futu_trade import TradeManager
from .futu_factory import (
    create_client, create_default_client, 
    create_simulate_client, create_real_client
)

# 导入基础类定义
from base.futu_class import (
    FutuException, FutuConnectException, FutuTradeException, FutuQuoteException,
    StockInfo, KLineData, StockQuote, MarketSnapshot, TickerData, 
    OrderBookData, RTData, AuTypeInfo, PlateInfo, PlateStock, FutuConfig,
    MarketState, CapitalFlow, CapitalDistribution, OwnerPlate
)

# 对外暴露的主要接口
__all__ = [
    # 客户端类
    'FutuClient',
    'QuoteManager', 
    'TradeManager',
    
    # 工厂函数
    'create_client',
    'create_default_client',
    'create_simulate_client', 
    'create_real_client',
    
    # 异常类
    'FutuException',
    'FutuConnectException',
    'FutuTradeException', 
    'FutuQuoteException',
    
    # 数据类
    'StockInfo',
    'KLineData',
    'StockQuote', 
    'MarketSnapshot',
    'TickerData',
    'OrderBookData',
    'RTData',
    'AuTypeInfo',
    'PlateInfo',
    'PlateStock',
    'FutuConfig',
    'MarketState',
    'CapitalFlow',
    'CapitalDistribution',
    'OwnerPlate'
]


# 示例用法
if __name__ == "__main__":
    # 方式1: 使用默认配置
    client = FutuClient()
    
    # 方式2: 使用自定义配置
    config = FutuConfig(
        host="127.0.0.1",
        port=11111,
        trade_pwd="your_password",
        default_trd_env="SIMULATE"
    )
    client = FutuClient(config)
    
    # 方式3: 使用便利函数
    client = create_client(host="127.0.0.1", port=11111)
    
    # 方式4: 使用上下文管理器
    with create_client() as client:
        # 自动连接和断开
        print(f"Client status: {client}")
        
        # 获取股票报价
        quotes = client.quote.get_stock_quote(["HK.00700", "HK.00388"])
        for quote in quotes:
            print(f"{quote.code}: {quote.cur_price}")
        
        # 获取K线数据
        klines = client.quote.get_current_kline("HK.00700", num=10)
        print(f"获取到 {len(klines)} 条K线数据")
        
        # 获取账户信息（需要解锁交易）
        try:
            client.unlock_trade()
            account_info = client.trade.get_account_info()
            print(f"账户信息: {account_info}")
        except Exception as e:
            print(f"交易功能需要密码解锁: {e}")