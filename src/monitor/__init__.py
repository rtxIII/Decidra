"""
监控模块包
提供股票监控相关的所有功能模块，包括富途数据获取、技术指标计算、订阅机制等
"""

# futu_interface 已移除，直接使用 futu_market
from .indicators import IndicatorsCalculator, IndicatorsManager

from .data_flow import DataFlowManager, ConnectionManager
from .performance import PerformanceMonitor

__all__ = [
    # 技术指标计算 - MA、RSI、MACD等指标
    'IndicatorsCalculator', 
    'IndicatorsManager',
    
    
    # 数据流管理 - 数据更新流程和连接管理
    'DataFlowManager',
    'ConnectionManager',
    
    # 性能监控 - API调用性能和系统监控
    'PerformanceMonitor'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Decidra Team"
__description__ = "股票监控系统模块，集成富途OpenAPI数据获取和实时订阅功能"