"""
性能监控模块测试
测试 PerformanceMonitor 的各项功能
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.performance import PerformanceMonitor
from base.monitor import PerformanceMetrics


class TestPerformanceMetrics(unittest.TestCase):
    """性能指标数据类测试"""
    
    def test_init(self):
        """测试初始化"""
        metrics = PerformanceMetrics()
        
        self.assertEqual(metrics.api_call_count, 0)
        self.assertEqual(metrics.api_response_time, [])
        self.assertEqual(metrics.memory_usage, [])
        self.assertEqual(metrics.cache_hit_rate, 0.0)
        self.assertEqual(metrics.error_count, 0)
    
    def test_get_avg_response_time_empty(self):
        """测试获取平均响应时间 - 空数据"""
        metrics = PerformanceMetrics()
        avg_time = metrics.get_avg_response_time()
        self.assertEqual(avg_time, 0.0)
    
    def test_get_avg_response_time_with_data(self):
        """测试获取平均响应时间 - 有数据"""
        metrics = PerformanceMetrics()
        metrics.api_response_time = [100, 200, 300, 150, 250]  # 毫秒
        
        avg_time = metrics.get_avg_response_time()
        expected_avg = sum(metrics.api_response_time) / len(metrics.api_response_time)
        self.assertEqual(avg_time, expected_avg)
        self.assertEqual(avg_time, 200.0)
    
    def test_get_current_memory_usage_empty(self):
        """测试获取当前内存使用量 - 空数据"""
        metrics = PerformanceMetrics()
        memory = metrics.get_current_memory_usage()
        self.assertEqual(memory, 0.0)
    
    def test_get_current_memory_usage_with_data(self):
        """测试获取当前内存使用量 - 有数据"""
        metrics = PerformanceMetrics()
        metrics.memory_usage = [10.5, 12.3, 15.7, 11.2]  # MB
        
        memory = metrics.get_current_memory_usage()
        self.assertEqual(memory, 11.2)  # 最后一个值


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.monitor = PerformanceMonitor()
    
    def test_init(self):
        """测试初始化"""
        self.assertIsInstance(self.monitor.metrics, PerformanceMetrics)
        self.assertEqual(self.monitor.metrics.api_call_count, 0)
    
    @patch('psutil.Process')
    async def test_measure_api_call_success(self, mock_process_class):
        """测试API调用性能测量 - 成功案例"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 50 * 1024 * 1024  # 50MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # 创建测试函数
        async def test_api_call():
            await asyncio.sleep(0.1)  # 模拟API调用延迟
            return "success"
        
        # 执行测试
        result = await self.monitor.measure_api_call(test_api_call)
        
        # 验证结果
        self.assertEqual(result, "success")
        self.assertEqual(self.monitor.metrics.api_call_count, 1)
        self.assertEqual(len(self.monitor.metrics.api_response_time), 1)
        self.assertEqual(len(self.monitor.metrics.memory_usage), 1)
        self.assertEqual(self.monitor.metrics.error_count, 0)
        
        # 验证响应时间在合理范围内（100ms左右）
        response_time = self.monitor.metrics.api_response_time[0]
        self.assertGreater(response_time, 90)  # 至少90ms
        self.assertLess(response_time, 200)    # 不超过200ms
        
        # 验证内存使用记录
        memory_usage = self.monitor.metrics.memory_usage[0]
        self.assertEqual(memory_usage, 50.0)  # 50MB
    
    @patch('psutil.Process')
    async def test_measure_api_call_with_args(self, mock_process_class):
        """测试API调用性能测量 - 带参数"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 60 * 1024 * 1024  # 60MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # 创建测试函数
        async def test_api_call_with_args(a, b, c=None):
            await asyncio.sleep(0.05)
            return f"result: {a} + {b} = {a + b}, c={c}"
        
        # 执行测试
        result = await self.monitor.measure_api_call(
            test_api_call_with_args, 
            10, 20, 
            c="test"
        )
        
        # 验证结果
        self.assertEqual(result, "result: 10 + 20 = 30, c=test")
        self.assertEqual(self.monitor.metrics.api_call_count, 1)
    
    @patch('psutil.Process')
    async def test_measure_api_call_exception(self, mock_process_class):
        """测试API调用性能测量 - 异常情况"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 40 * 1024 * 1024  # 40MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # 创建会抛出异常的测试函数
        async def test_api_call_error():
            await asyncio.sleep(0.02)
            raise Exception("API调用失败")
        
        # 执行测试并验证异常
        with self.assertRaises(Exception) as context:
            await self.monitor.measure_api_call(test_api_call_error)
        
        self.assertIn("API调用失败", str(context.exception))
        
        # 验证错误统计
        self.assertEqual(self.monitor.metrics.api_call_count, 0)  # 失败的调用不计数
        self.assertEqual(self.monitor.metrics.error_count, 1)
        self.assertEqual(len(self.monitor.metrics.api_response_time), 0)
        self.assertEqual(len(self.monitor.metrics.memory_usage), 0)
    
    @patch('psutil.Process')
    async def test_measure_multiple_api_calls(self, mock_process_class):
        """测试多次API调用性能测量"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 55 * 1024 * 1024  # 55MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # 创建多个测试函数
        async def fast_call():
            await asyncio.sleep(0.01)
            return "fast"
        
        async def slow_call():
            await asyncio.sleep(0.1)
            return "slow"
        
        async def error_call():
            raise Exception("错误")
        
        # 执行多次调用
        result1 = await self.monitor.measure_api_call(fast_call)
        result2 = await self.monitor.measure_api_call(slow_call)
        
        try:
            await self.monitor.measure_api_call(error_call)
        except Exception:
            pass  # 预期的异常
        
        result3 = await self.monitor.measure_api_call(fast_call)
        
        # 验证统计结果
        self.assertEqual(self.monitor.metrics.api_call_count, 3)  # 成功调用3次
        self.assertEqual(self.monitor.metrics.error_count, 1)     # 失败1次
        self.assertEqual(len(self.monitor.metrics.api_response_time), 3)
        self.assertEqual(len(self.monitor.metrics.memory_usage), 3)
        
        # 验证响应时间趋势
        response_times = self.monitor.metrics.api_response_time
        self.assertLess(response_times[0], response_times[1])  # fast < slow
    
    def test_get_performance_report_empty(self):
        """测试获取性能报告 - 空数据"""
        report = self.monitor.get_performance_report()
        
        expected_keys = [
            "avg_response_time", "memory_usage_mb", "cache_hit_rate",
            "api_calls_total", "error_rate"
        ]
        
        for key in expected_keys:
            self.assertIn(key, report)
        
        # 验证空数据的默认值
        self.assertEqual(report["avg_response_time"], 0.0)
        self.assertEqual(report["memory_usage_mb"], 0.0)
        self.assertEqual(report["cache_hit_rate"], 0.0)
        self.assertEqual(report["api_calls_total"], 0)
        self.assertEqual(report["error_rate"], 0.0)
    
    @patch('psutil.Process')
    async def test_get_performance_report_with_data(self, mock_process_class):
        """测试获取性能报告 - 有数据"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 45 * 1024 * 1024  # 45MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # 设置一些测试数据
        self.monitor.metrics.api_call_count = 10
        self.monitor.metrics.error_count = 2
        self.monitor.metrics.cache_hit_rate = 0.85
        
        # 执行一些API调用来生成数据
        async def test_call():
            await asyncio.sleep(0.05)
            return "test"
        
        for _ in range(3):
            await self.monitor.measure_api_call(test_call)
        
        # 获取性能报告
        report = self.monitor.get_performance_report()
        
        # 验证报告内容
        self.assertGreater(report["avg_response_time"], 0)
        self.assertEqual(report["memory_usage_mb"], 45.0)
        self.assertEqual(report["cache_hit_rate"], 0.85)
        self.assertEqual(report["api_calls_total"], 13)  # 10 + 3
        self.assertEqual(report["error_rate"], 2/13)  # 2 errors out of 13 calls
    
    def test_performance_metrics_edge_cases(self):
        """测试性能指标边界情况"""
        # 测试除零情况
        self.monitor.metrics.api_call_count = 0
        self.monitor.metrics.error_count = 5
        
        report = self.monitor.get_performance_report()
        self.assertEqual(report["error_rate"], 5.0)  # error_count / max(api_call_count, 1)
        
        # 测试大量数据
        self.monitor.metrics.api_response_time = [i for i in range(1000)]
        self.monitor.metrics.memory_usage = [i * 0.1 for i in range(1000)]
        
        report = self.monitor.get_performance_report()
        expected_avg = sum(range(1000)) / 1000
        self.assertEqual(report["avg_response_time"], expected_avg)
        self.assertEqual(report["memory_usage_mb"], 99.9)  # 最后一个值


class TestPerformanceMonitorIntegration(unittest.TestCase):
    """性能监控器集成测试"""
    
    @patch('psutil.Process')
    async def test_real_world_scenario(self, mock_process_class):
        """测试真实世界场景"""
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        
        # 模拟内存使用量逐渐增加
        memory_values = [50, 52, 55, 53, 60, 58]  # MB
        memory_iter = iter(memory_values)
        
        def mock_memory():
            try:
                return Mock(rss=next(memory_iter) * 1024 * 1024)
            except StopIteration:
                return Mock(rss=60 * 1024 * 1024)
        
        mock_process.memory_info = mock_memory
        mock_process_class.return_value = mock_process
        
        monitor = PerformanceMonitor()
        
        # 模拟真实的API调用模式
        async def get_stock_data(stock_code):
            """模拟获取股票数据"""
            if stock_code == "INVALID":
                raise Exception("无效股票代码")
            
            # 模拟不同的响应时间
            if stock_code.startswith("HK"):
                await asyncio.sleep(0.05)  # 港股较快
            elif stock_code.startswith("US"):
                await asyncio.sleep(0.1)   # 美股较慢
            
            return {"code": stock_code, "price": 100.0}
        
        # 执行多种API调用
        stock_codes = ["HK.00700", "HK.09988", "US.AAPL", "US.GOOGL", "INVALID", "HK.00005"]
        results = []
        
        for code in stock_codes:
            try:
                result = await monitor.measure_api_call(get_stock_data, code)
                results.append(result)
            except Exception:
                pass  # 忽略预期的错误
        
        # 验证性能统计
        self.assertEqual(monitor.metrics.api_call_count, 5)  # 5次成功调用
        self.assertEqual(monitor.metrics.error_count, 1)     # 1次失败调用
        self.assertEqual(len(results), 5)
        
        # 获取最终报告
        report = monitor.get_performance_report()
        
        # 验证报告合理性
        self.assertGreater(report["avg_response_time"], 30)   # 至少30ms
        self.assertLess(report["avg_response_time"], 150)     # 不超过150ms
        self.assertGreater(report["memory_usage_mb"], 40)     # 至少40MB
        self.assertEqual(report["api_calls_total"], 5)
        self.assertEqual(report["error_rate"], 1/5)           # 20%错误率
    
    async def test_performance_under_load(self):
        """测试高负载下的性能监控"""
        monitor = PerformanceMonitor()
        
        # 模拟高频率的API调用
        async def quick_call(i):
            return f"result_{i}"
        
        # 并发执行大量调用
        tasks = []
        for i in range(100):
            task = monitor.measure_api_call(quick_call, i)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 验证结果
        self.assertEqual(len(results), 100)
        self.assertEqual(monitor.metrics.api_call_count, 100)
        self.assertEqual(monitor.metrics.error_count, 0)
        
        # 验证性能报告
        report = monitor.get_performance_report()
        self.assertEqual(report["api_calls_total"], 100)
        self.assertEqual(report["error_rate"], 0.0)
    
    @patch('time.time')
    @patch('psutil.Process')
    async def test_timing_accuracy(self, mock_process_class, mock_time):
        """测试计时准确性"""
        # 模拟时间
        time_values = [1000.0, 1000.15]  # 150ms差异
        time_iter = iter(time_values)
        mock_time.side_effect = lambda: next(time_iter)
        
        # 模拟psutil.Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 50 * 1024 * 1024
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        monitor = PerformanceMonitor()
        
        async def test_call():
            return "test"
        
        result = await monitor.measure_api_call(test_call)
        
        # 验证计时准确性
        self.assertEqual(result, "test")
        self.assertEqual(len(monitor.metrics.api_response_time), 1)
        recorded_time = monitor.metrics.api_response_time[0]
        self.assertEqual(recorded_time, 150.0)  # 150ms


if __name__ == '__main__':
    # 运行异步测试的辅助函数
    def run_async_test(test_func):
        """运行异步测试"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_func)
        finally:
            loop.close()
    
    # 运行所有测试
    unittest.main(verbosity=2)