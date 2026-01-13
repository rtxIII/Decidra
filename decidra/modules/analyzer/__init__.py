# -*- coding: utf-8 -*-
"""
===================================
分析器模块 - 包初始化
===================================

本包提供股票分析功能，包括：
1. 趋势分析 - 基于均线和量能的趋势判断
2. AI分析 - 基于大模型的智能分析
3. 大盘分析 - 市场概览和复盘
4. 搜索服务 - 新闻和情报搜索
"""

from .analyzer_stock import (
    StockTrendAnalyzer,
    TrendAnalysisResult,
    TrendStatus,
    VolumeStatus,
    BuySignal,
    analyze_stock,
)
from .analyzer_result import (
    GeminiAnalyzer,
    AnalysisResult,
    get_analyzer,
)
from .analyzer_market import (
    MarketAnalyzer,
    MarketOverview,
    MarketIndex,
)
from .search_service import (
    SearchService,
    SearchResult,
    SearchResponse,
    get_search_service,
)

__all__ = [
    # 趋势分析
    'StockTrendAnalyzer',
    'TrendAnalysisResult',
    'TrendStatus',
    'VolumeStatus',
    'BuySignal',
    'analyze_stock',
    # AI分析
    'GeminiAnalyzer',
    'AnalysisResult',
    'get_analyzer',
    # 大盘分析
    'MarketAnalyzer',
    'MarketOverview',
    'MarketIndex',
    # 搜索服务
    'SearchService',
    'SearchResult',
    'SearchResponse',
    'get_search_service',
]
