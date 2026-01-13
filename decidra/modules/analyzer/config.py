# -*- coding: utf-8 -*-
"""
===================================
Analyzer 模块配置
===================================

为 analyzer 模块提供配置支持，从环境变量或配置文件读取 AI API 配置。
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class AnalyzerConfig:
    """
    Analyzer 模块配置类

    配置优先级：
    1. 环境变量
    2. 默认值
    """

    # Gemini API 配置
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_model_fallback: str = "gemini-1.5-flash"
    gemini_max_retries: int = 3
    gemini_retry_delay: float = 5.0
    gemini_request_delay: float = 1.0

    # OpenAI 兼容 API 配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"

    # 搜索 API 配置
    tavily_api_keys: List[str] = field(default_factory=list)
    serpapi_keys: List[str] = field(default_factory=list)

    def __post_init__(self):
        """从环境变量加载配置"""
        # Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        self.gemini_model = os.getenv("GEMINI_MODEL", self.gemini_model)
        self.gemini_model_fallback = os.getenv("GEMINI_MODEL_FALLBACK", self.gemini_model_fallback)

        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", self.openai_base_url)
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)

        # Tavily (支持多个 key，用逗号分隔)
        tavily_keys_str = os.getenv("TAVILY_API_KEYS", "")
        if tavily_keys_str:
            self.tavily_api_keys = [k.strip() for k in tavily_keys_str.split(",") if k.strip()]

        # SerpAPI (支持多个 key，用逗号分隔)
        serpapi_keys_str = os.getenv("SERPAPI_KEYS", "")
        if serpapi_keys_str:
            self.serpapi_keys = [k.strip() for k in serpapi_keys_str.split(",") if k.strip()]

        # 日志记录配置状态
        if self.gemini_api_key:
            logger.debug(f"Gemini API Key 已配置 (长度: {len(self.gemini_api_key)})")
        if self.openai_api_key:
            logger.debug(f"OpenAI API Key 已配置 (长度: {len(self.openai_api_key)})")
        if self.tavily_api_keys:
            logger.debug(f"Tavily API Keys 已配置 (数量: {len(self.tavily_api_keys)})")
        if self.serpapi_keys:
            logger.debug(f"SerpAPI Keys 已配置 (数量: {len(self.serpapi_keys)})")


# 全局配置单例
_config: Optional[AnalyzerConfig] = None


def get_config() -> AnalyzerConfig:
    """获取配置单例"""
    global _config
    if _config is None:
        _config = AnalyzerConfig()
    return _config


def reset_config() -> None:
    """重置配置（用于测试）"""
    global _config
    _config = None
