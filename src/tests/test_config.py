"""
测试配置文件
定义测试运行的配置、工具函数和测试数据
"""

import unittest
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.monitor import (
    StockData, TechnicalIndicators, MarketStatus, SignalType,
    ConnectionStatus, DataUpdateResult, PerformanceMetrics
)


class TestConfig:
    """测试配置类"""
    
    # 测试环境配置
    TEST_ENV = {
        'LOGGING_LEVEL': logging.INFO,
        'ASYNC_TIMEOUT': 30.0,  # 异步测试超时时间（秒）
        'PERFORMANCE_THRESHOLD': 5.0,  # 性能测试阈值（秒）
        'MAX_RETRY_COUNT': 3,
        'MOCK_DATA_SIZE': 100  # 模拟数据大小
    }
    
    # 测试股票代码
    TEST_STOCK_CODES = [
        'HK.00700',  # 腾讯控股
        'HK.09988',  # 阿里巴巴
        'HK.00005',  # 汇丰控股
        'US.AAPL',   # 苹果
        'US.GOOGL',  # 谷歌
        'SH.600000', # 浦发银行
        'SZ.000001'  # 平安银行
    ]
    
    # 测试数据模板
    STOCK_DATA_TEMPLATE = {
        'code': '',
        'name': '',
        'current_price': 100.0,
        'open_price': 99.0,
        'prev_close': 98.0,
        'change_rate': 0.0204,
        'change_amount': 2.0,
        'volume': 1000000,
        'turnover': 100000000.0,
        'high_price': 102.0,
        'low_price': 97.0,
        'market_status': MarketStatus.OPEN
    }
    
    INDICATORS_TEMPLATE = {
        'stock_code': '',
        'ma5': 100.0,
        'ma10': 99.0,
        'ma20': 98.0,
        'rsi14': 65.0,
        'rsi_signal': SignalType.HOLD,
        'macd_line': 1.5,
        'signal_line': 1.2,
        'histogram': 0.3,
        'macd_signal': SignalType.BUY
    }


class TestDataFactory:
    """测试数据工厂类"""
    
    @staticmethod
    def create_stock_data(code: str, **kwargs) -> StockData:
        """创建股票数据对象"""
        data = TestConfig.STOCK_DATA_TEMPLATE.copy()
        data['code'] = code
        data['name'] = f'股票_{code}'
        data['update_time'] = datetime.now()
        data.update(kwargs)
        
        return StockData(**data)
    
    @staticmethod
    def create_indicators(code: str, **kwargs) -> TechnicalIndicators:
        """创建技术指标对象"""
        data = TestConfig.INDICATORS_TEMPLATE.copy()
        data['stock_code'] = code
        data.update(kwargs)
        
        return TechnicalIndicators(**data)
    
    @staticmethod
    def create_batch_stock_data(codes: List[str], **kwargs) -> List[StockData]:
        """批量创建股票数据"""
        return [TestDataFactory.create_stock_data(code, **kwargs) for code in codes]
    
    @staticmethod
    def create_batch_indicators(codes: List[str], **kwargs) -> List[TechnicalIndicators]:
        """批量创建技术指标"""
        return [TestDataFactory.create_indicators(code, **kwargs) for code in codes]
    
    @staticmethod
    def create_kline_data(days: int = 60) -> List[Dict]:
        """创建K线数据"""
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            price = 100 + i * 0.5 + (i % 10) * 0.1
            
            data.append({
                'time_key': date.strftime('%Y-%m-%d'),
                'open': price - 0.5,
                'close': price,
                'high': price + 0.5,
                'low': price - 1,
                'volume': 1000 + i * 10,
                'turnover': price * (1000 + i * 10)
            })
        
        return data
    
    @staticmethod
    def create_market_snapshot(codes: List[str]) -> List[Dict]:
        """创建市场快照数据"""
        snapshots = []
        for i, code in enumerate(codes):
            snapshots.append({
                'code': code,
                'stock_name': f'股票_{code}',
                'cur_price': 100.0 + i * 10,
                'open_price': 99.0 + i * 10,
                'prev_close_price': 98.0 + i * 10,
                'high_price': 102.0 + i * 10,
                'low_price': 97.0 + i * 10,
                'volume': 1000000 + i * 100000,
                'turnover': (100.0 + i * 10) * (1000000 + i * 100000)
            })
        return snapshots


class AsyncTestCase(unittest.TestCase):
    """异步测试基类"""
    
    def setUp(self):
        """设置测试环境"""
        # 设置日志级别
        logging.basicConfig(
            level=TestConfig.TEST_ENV['LOGGING_LEVEL'],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 创建事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """清理测试环境"""
        if self.loop and not self.loop.is_closed():
            self.loop.close()
    
    def run_async(self, coro):
        """运行异步函数"""
        return self.loop.run_until_complete(
            asyncio.wait_for(coro, timeout=TestConfig.TEST_ENV['ASYNC_TIMEOUT'])
        )
    
    async def async_assert_raises(self, exception_class, coro):
        """异步断言异常"""
        with self.assertRaises(exception_class):
            await coro


class TestHelpers:
    """测试辅助函数"""
    
    @staticmethod
    def assert_stock_data_valid(test_case: unittest.TestCase, stock_data: StockData):
        """断言股票数据有效"""
        test_case.assertIsNotNone(stock_data.code)
        test_case.assertIsNotNone(stock_data.name)
        test_case.assertGreater(stock_data.current_price, 0)
        test_case.assertGreaterEqual(stock_data.volume, 0)
        test_case.assertIsInstance(stock_data.update_time, datetime)
        test_case.assertIsInstance(stock_data.market_status, MarketStatus)
    
    @staticmethod
    def assert_indicators_valid(test_case: unittest.TestCase, indicators: TechnicalIndicators):
        """断言技术指标有效"""
        test_case.assertIsNotNone(indicators.stock_code)
        test_case.assertIsInstance(indicators.rsi_signal, SignalType)
        test_case.assertIsInstance(indicators.macd_signal, SignalType)
        
        if indicators.rsi14 is not None:
            test_case.assertGreaterEqual(indicators.rsi14, 0)
            test_case.assertLessEqual(indicators.rsi14, 100)
    
    @staticmethod
    def assert_data_update_result_valid(test_case: unittest.TestCase, result: DataUpdateResult):
        """断言数据更新结果有效"""
        test_case.assertIsInstance(result, DataUpdateResult)
        test_case.assertIsInstance(result.success, bool)
        test_case.assertIsInstance(result.stock_data, dict)
        test_case.assertIsInstance(result.indicators_data, dict)
        test_case.assertIsInstance(result.update_timestamp, datetime)
        
        if not result.success:
            test_case.assertIsNotNone(result.error_message)
    
    @staticmethod
    def assert_performance_metrics_valid(test_case: unittest.TestCase, metrics: PerformanceMetrics):
        """断言性能指标有效"""
        test_case.assertIsInstance(metrics, PerformanceMetrics)
        test_case.assertGreaterEqual(metrics.api_call_count, 0)
        test_case.assertGreaterEqual(metrics.error_count, 0)
        test_case.assertGreaterEqual(metrics.cache_hit_rate, 0.0)
        test_case.assertLessEqual(metrics.cache_hit_rate, 1.0)
    
    @staticmethod
    def create_mock_async_function(return_value=None, side_effect=None):
        """创建mock异步函数"""
        async def mock_func(*args, **kwargs):
            if side_effect:
                if isinstance(side_effect, Exception):
                    raise side_effect
                elif callable(side_effect):
                    return side_effect(*args, **kwargs)
            return return_value
        
        return mock_func
    
    @staticmethod
    def measure_execution_time(func):
        """测量函数执行时间"""
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = func(*args, **kwargs)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            return result, execution_time
        return wrapper
    
    @staticmethod
    async def measure_async_execution_time(coro):
        """测量异步函数执行时间"""
        start_time = datetime.now()
        result = await coro
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        return result, execution_time


class TestSuite:
    """测试套件管理"""
    
    @staticmethod
    def create_monitor_test_suite():
        """创建监控模块测试套件"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # 添加所有测试模块
        test_modules = [
            'tests.test_futu_interface',
            'tests.test_indicators',
            'tests.test_ui_components',
            'tests.test_data_flow',
            'tests.test_performance',
            'tests.test_monitor_integration'
        ]
        
        for module_name in test_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                tests = loader.loadTestsFromModule(module)
                suite.addTests(tests)
            except ImportError as e:
                print(f"警告: 无法导入测试模块 {module_name}: {e}")
        
        return suite
    
    @staticmethod
    def run_all_tests(verbosity=2):
        """运行所有测试"""
        suite = TestSuite.create_monitor_test_suite()
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    @staticmethod
    def run_specific_test(test_class_name: str, test_method_name: str = None):
        """运行特定测试"""
        loader = unittest.TestLoader()
        
        if test_method_name:
            suite = loader.loadTestsFromName(f'{test_class_name}.{test_method_name}')
        else:
            suite = loader.loadTestsFromName(test_class_name)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()


class MockDataGenerator:
    """模拟数据生成器"""
    
    @staticmethod
    def generate_realistic_price_series(days: int, initial_price: float = 100.0):
        """生成真实的价格序列"""
        import random
        
        prices = [initial_price]
        for i in range(1, days):
            # 随机游走模型
            change = random.gauss(0, 0.02)  # 均值0，标准差2%
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))  # 价格不能为负
        
        return prices
    
    @staticmethod
    def generate_trending_price_series(days: int, initial_price: float = 100.0, trend: float = 0.001):
        """生成趋势价格序列"""
        import random
        
        prices = [initial_price]
        for i in range(1, days):
            # 趋势 + 随机波动
            trend_change = trend  # 每日趋势变化
            random_change = random.gauss(0, 0.015)  # 随机波动
            total_change = trend_change + random_change
            
            new_price = prices[-1] * (1 + total_change)
            prices.append(max(new_price, 0.01))
        
        return prices
    
    @staticmethod
    def generate_volatile_price_series(days: int, initial_price: float = 100.0, volatility: float = 0.03):
        """生成高波动价格序列"""
        import random
        
        prices = [initial_price]
        for i in range(1, days):
            # 高波动随机游走
            change = random.gauss(0, volatility)
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))
        
        return prices


# 测试运行器
if __name__ == '__main__':
    # 设置测试环境
    print("=== 监控模块测试配置 ===")
    print(f"测试环境: {TestConfig.TEST_ENV}")
    print(f"测试股票代码: {TestConfig.TEST_STOCK_CODES}")
    
    # 运行所有测试
    print("\n=== 运行所有测试 ===")
    success = TestSuite.run_all_tests()
    
    if success:
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)