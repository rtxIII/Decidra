"""
Decidra - 智能交易决策系统

基于富途OpenAPI的Python股票交易分析平台
"""

import sys
import warnings
from pathlib import Path

# 过滤富途API相关的警告
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*socket.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*setDaemon.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*Pandas.*")