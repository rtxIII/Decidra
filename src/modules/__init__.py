# 导入其他模块

try:
    from ..base.futu_modue import FutuModuleBase
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from base.futu_modue import FutuModuleBase
from .futu_market import FutuMarket
from .ai.claude_ai_client import ClaudeAIClient, AIAnalysisRequest, AIAnalysisResponse, create_claude_client, quick_stock_analysis

#对应https://openapi.futunn.com/futu-api-doc/quote/overview.html
"""
富途API模块
提供统一的富途OpenAPI封装和基础功能
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from utils import logger
from utils.global_vars import *

# 使用新的API封装
from api.futu import create_client
from base.futu_class import FutuException


__all__ = [
    'FutuMarket', 
    'ClaudeAIClient', 
    'AIAnalysisRequest', 
    'AIAnalysisResponse', 
    'create_claude_client', 
    'quick_stock_analysis'
]


