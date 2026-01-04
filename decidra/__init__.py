"""
Decidra - 智能交易决策系统

基于富途OpenAPI的Python股票交易分析平台
"""

import warnings

# 过滤富途API相关的警告
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*socket.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*setDaemon.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*Pandas.*")

__version__ = "1.0.2"
__author__ = "rtx3"
__email__ = "r@rtx3.com"

# 导出版本信息
__all__ = ["__version__", "__author__", "__email__"]
