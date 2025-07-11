"""
性能监控模块
提供API调用性能测量和系统监控功能
"""

from typing import Dict
import asyncio
import logging

from base.monitor import PerformanceMetrics


logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def measure_api_call(self, func, *args, **kwargs):
        """
        测量API调用性能
        
        功能:
        1. 记录调用次数
        2. 测量响应时间
        3. 监控内存使用
        4. 异常统计
        """
        import time
        import psutil
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = await func(*args, **kwargs)
            self.metrics.api_call_count += 1
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000  # 毫秒
            self.metrics.api_response_time.append(response_time)
            
            # 记录内存使用
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            self.metrics.memory_usage.append(end_memory)
            
            return result
            
        except Exception as e:
            self.metrics.error_count += 1
            self.logger.error(f"API调用异常: {e}")
            raise
        
    def get_performance_report(self) -> Dict[str, float]:
        """
        获取性能报告
        
        输出数据: {
            "avg_response_time": 150.5,  # 毫秒
            "memory_usage_mb": 45.2,
            "cache_hit_rate": 0.85,
            "api_calls_per_minute": 12,
            "error_rate": 0.02
        }
        """
        return {
            "avg_response_time": self.metrics.get_avg_response_time(),
            "memory_usage_mb": self.metrics.get_current_memory_usage(),
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "api_calls_total": self.metrics.api_call_count,
            "error_rate": self.metrics.error_count / max(self.metrics.api_call_count, 1)
        }