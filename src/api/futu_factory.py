"""
富途客户端工厂模块

提供便利函数用于创建和配置富途客户端实例。
"""

from typing import Optional
from .futu_client import FutuClient
from base.futu_class import FutuConfig


def create_client(config_file: Optional[str] = None, **kwargs) -> FutuClient:
    """
    创建富途客户端的便利函数
    
    Args:
        config_file: 配置文件路径
        **kwargs: 其他配置参数
    
    Returns:
        FutuClient: 客户端实例
    """
    if config_file:
        config = FutuConfig.from_file(config_file)
        # 允许kwargs覆盖文件配置
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
    else:
        # 尝试从环境变量加载
        try:
            config = FutuConfig.from_env()
            # 允许kwargs覆盖环境变量
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except:
            # 使用默认配置
            config = FutuConfig(**kwargs)
    
    return FutuClient(config)


# 便利的客户端创建函数
def create_default_client() -> FutuClient:
    """
    创建默认配置的富途客户端
    
    Returns:
        FutuClient: 使用默认配置的客户端实例
    """
    return FutuClient()


def create_simulate_client(host: str = "127.0.0.1", port: int = 11111) -> FutuClient:
    """
    创建模拟交易环境的富途客户端
    
    Args:
        host: 富途OpenD主机地址
        port: 富途OpenD端口
    
    Returns:
        FutuClient: 配置为模拟交易的客户端实例
    """
    config = FutuConfig(
        host=host,
        port=port,
        default_trd_env="SIMULATE"
    )
    return FutuClient(config)


def create_real_client(host: str = "127.0.0.1", 
                      port: int = 11111, 
                      trade_pwd: Optional[str] = None) -> FutuClient:
    """
    创建真实交易环境的富途客户端
    
    Args:
        host: 富途OpenD主机地址
        port: 富途OpenD端口
        trade_pwd: 交易密码
    
    Returns:
        FutuClient: 配置为真实交易的客户端实例
    """
    config = FutuConfig(
        host=host,
        port=port,
        default_trd_env="REAL",
        trade_pwd=trade_pwd
    )
    return FutuClient(config)