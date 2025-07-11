"""
技术指标模块测试
测试 IndicatorsCalculator 和 IndicatorsManager 的各项功能
"""

import unittest
import asyncio
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.indicators import IndicatorsCalculator, IndicatorsManager
from base.monitor import TechnicalIndicators, SignalType


class TestIndicatorsCalculator(unittest.TestCase):
    """技术指标计算器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.calculator = IndicatorsCalculator()
        
        # 准备测试数据
        self.test_prices = [100, 102, 101, 105, 103, 107, 106, 110, 108, 112]
        self.rsi_test_prices = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.85, 46.08, 45.89, 46.03,
            46.83, 47.69, 46.49, 46.26, 47.09, 47.37, 47.20, 47.72, 48.90, 50.19
        ]  # 20天价格数据用于RSI测试
    
    def test_calculate_ma_valid_data(self):
        """测试移动平均线计算 - 有效数据"""
        # 测试5日MA
        ma5 = self.calculator.calculate_ma(self.test_prices, 5)
        expected_ma5 = sum(self.test_prices[-5:]) / 5
        self.assertAlmostEqual(ma5, expected_ma5, places=5)
        
        # 测试10日MA
        ma10 = self.calculator.calculate_ma(self.test_prices, 10)
        expected_ma10 = sum(self.test_prices) / 10
        self.assertAlmostEqual(ma10, expected_ma10, places=5)
    
    def test_calculate_ma_insufficient_data(self):
        """测试移动平均线计算 - 数据不足"""
        short_prices = [100, 102, 101]
        ma5 = self.calculator.calculate_ma(short_prices, 5)
        self.assertIsNone(ma5)
    
    def test_calculate_ma_empty_data(self):
        """测试移动平均线计算 - 空数据"""
        ma = self.calculator.calculate_ma([], 5)
        self.assertIsNone(ma)
    
    def test_calculate_ma_invalid_period(self):
        """测试移动平均线计算 - 无效周期"""
        ma = self.calculator.calculate_ma(self.test_prices, 0)
        self.assertIsNone(ma)
    
    def test_calculate_rsi_valid_data(self):
        """测试RSI计算 - 有效数据"""
        rsi, signal = self.calculator.calculate_rsi(self.rsi_test_prices, 14)
        
        self.assertIsNotNone(rsi)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
        self.assertIsInstance(signal, SignalType)
    
    def test_calculate_rsi_signal_generation(self):
        """测试RSI信号生成"""
        # 测试超买信号 (RSI > 70)
        high_prices = [50 + i for i in range(20)]  # 持续上涨
        rsi, signal = self.calculator.calculate_rsi(high_prices, 14)
        # 由于持续上涨，RSI应该较高，可能产生卖出信号
        
        # 测试超卖信号 (RSI < 30)
        low_prices = [50 - i for i in range(20)]  # 持续下跌
        rsi, signal = self.calculator.calculate_rsi(low_prices, 14)
        # 由于持续下跌，RSI应该较低，可能产生买入信号
        
        # 测试持有信号 (30 <= RSI <= 70)
        stable_prices = [50 + (i % 2) for i in range(20)]  # 震荡行情
        rsi, signal = self.calculator.calculate_rsi(stable_prices, 14)
        self.assertIn(signal, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])
    
    def test_calculate_rsi_insufficient_data(self):
        """测试RSI计算 - 数据不足"""
        short_prices = [100, 102, 101]
        rsi, signal = self.calculator.calculate_rsi(short_prices, 14)
        self.assertIsNone(rsi)
        self.assertEqual(signal, SignalType.HOLD)
    
    def test_calculate_macd_valid_data(self):
        """测试MACD计算 - 有效数据"""
        # 准备足够的数据（34天以上）
        prices = [100 + i + (i % 5) for i in range(40)]
        
        macd_line, signal_line, histogram, signal = self.calculator.calculate_macd(prices)
        
        self.assertIsNotNone(macd_line)
        self.assertIsNotNone(signal_line)
        self.assertIsNotNone(histogram)
        self.assertIsInstance(signal, SignalType)
        
        # 验证MACD关系：histogram = macd_line - signal_line
        self.assertAlmostEqual(histogram, macd_line - signal_line, places=5)
    
    def test_calculate_macd_minimal_data(self):
        """测试MACD计算 - 最少数据"""
        # 测试26天数据（最少要求）
        prices = [100 + i for i in range(26)]
        macd_line, signal_line, histogram, signal = self.calculator.calculate_macd(prices)
        
        self.assertIsNotNone(macd_line)
        self.assertIsNone(signal_line)  # 需要34天才有信号线
        self.assertIsNone(histogram)
        self.assertEqual(signal, SignalType.HOLD)
    
    def test_calculate_macd_insufficient_data(self):
        """测试MACD计算 - 数据不足"""
        short_prices = [100, 102, 101]
        macd_line, signal_line, histogram, signal = self.calculator.calculate_macd(short_prices)
        
        self.assertIsNone(macd_line)
        self.assertIsNone(signal_line)
        self.assertIsNone(histogram)
        self.assertEqual(signal, SignalType.HOLD)
    
    def test_calculate_macd_signal_generation(self):
        """测试MACD信号生成"""
        # 创建上升趋势数据
        uptrend_prices = [100 + i * 0.5 for i in range(40)]
        macd_line, signal_line, histogram, signal = self.calculator.calculate_macd(uptrend_prices)
        
        # 在上升趋势中，可能会产生买入信号
        self.assertIn(signal, [SignalType.BUY, SignalType.HOLD, SignalType.SELL])
        
        # 创建下降趋势数据
        downtrend_prices = [100 - i * 0.5 for i in range(40)]
        macd_line, signal_line, histogram, signal = self.calculator.calculate_macd(downtrend_prices)
        
        # 在下降趋势中，可能会产生卖出信号
        self.assertIn(signal, [SignalType.BUY, SignalType.HOLD, SignalType.SELL])


class TestIndicatorsManager(unittest.TestCase):
    """技术指标管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_data_manager = Mock()
        self.indicators_manager = IndicatorsManager(self.mock_data_manager)
    
    def create_mock_kline_data(self, days=60):
        """创建模拟K线数据"""
        data = []
        base_price = 100
        
        for i in range(days):
            price = base_price + i + (i % 5)
            data.append({
                'time_key': f'2024-01-{i+1:02d}',
                'open': price - 1,
                'close': price,
                'high': price + 1,
                'low': price - 2,
                'volume': 1000 + i * 10,
                'turnover': price * (1000 + i * 10)
            })
        
        return pd.DataFrame(data)
    
    async def test_update_all_indicators_success(self):
        """测试更新所有技术指标 - 成功案例"""
        # 准备模拟数据
        stock_codes = ['HK.00700', 'HK.09988']
        mock_klines = self.create_mock_kline_data(60)
        
        # 设置mock返回
        self.mock_data_manager.get_historical_klines = AsyncMock(return_value=mock_klines)
        
        # 执行测试
        result = await self.indicators_manager.update_all_indicators(stock_codes)
        
        # 验证结果
        self.assertEqual(len(result), len(stock_codes))
        
        for code in stock_codes:
            self.assertIn(code, result)
            indicators = result[code]
            self.assertIsInstance(indicators, TechnicalIndicators)
            self.assertEqual(indicators.stock_code, code)
            
            # 验证指标计算结果
            self.assertIsNotNone(indicators.ma5)
            self.assertIsNotNone(indicators.ma10)
            self.assertIsNotNone(indicators.ma20)
            self.assertIsNotNone(indicators.rsi14)
            self.assertIsInstance(indicators.rsi_signal, SignalType)
            self.assertIsNotNone(indicators.macd_line)
            self.assertIsInstance(indicators.macd_signal, SignalType)
    
    async def test_update_all_indicators_empty_data(self):
        """测试更新所有技术指标 - 空数据"""
        stock_codes = ['HK.00700']
        
        # 设置mock返回空数据
        self.mock_data_manager.get_historical_klines = AsyncMock(return_value=pd.DataFrame())
        
        # 执行测试
        result = await self.indicators_manager.update_all_indicators(stock_codes)
        
        # 验证结果 - 应该跳过空数据的股票
        self.assertEqual(len(result), 0)
    
    async def test_update_all_indicators_partial_data(self):
        """测试更新所有技术指标 - 部分数据"""
        stock_codes = ['HK.00700', 'HK.09988', 'US.AAPL']
        
        async def mock_get_klines(code, days):
            if code == 'HK.00700':
                return self.create_mock_kline_data(60)
            elif code == 'HK.09988':
                return pd.DataFrame()  # 空数据
            else:  # US.AAPL
                return self.create_mock_kline_data(30)  # 较少数据
        
        self.mock_data_manager.get_historical_klines = mock_get_klines
        
        # 执行测试
        result = await self.indicators_manager.update_all_indicators(stock_codes)
        
        # 验证结果 - 只有有效数据的股票会被处理
        self.assertIn('HK.00700', result)
        self.assertNotIn('HK.09988', result)  # 空数据被跳过
        self.assertIn('US.AAPL', result)
    
    async def test_update_all_indicators_exception_handling(self):
        """测试更新所有技术指标 - 异常处理"""
        stock_codes = ['HK.00700']
        
        # 设置mock抛出异常
        self.mock_data_manager.get_historical_klines = AsyncMock(side_effect=Exception("API错误"))
        
        # 执行测试
        result = await self.indicators_manager.update_all_indicators(stock_codes)
        
        # 验证结果 - 异常时返回空字典
        self.assertEqual(len(result), 0)
    
    async def test_update_all_indicators_insufficient_data(self):
        """测试更新所有技术指标 - 数据不足"""
        stock_codes = ['HK.00700']
        
        # 创建数据不足的K线数据（少于MACD所需的26天）
        insufficient_data = self.create_mock_kline_data(10)
        self.mock_data_manager.get_historical_klines = AsyncMock(return_value=insufficient_data)
        
        # 执行测试
        result = await self.indicators_manager.update_all_indicators(stock_codes)
        
        # 验证结果
        self.assertIn('HK.00700', result)
        indicators = result['HK.00700']
        
        # MA指标应该能计算（数据足够）
        self.assertIsNotNone(indicators.ma5)
        
        # RSI可能无法计算（取决于数据量）
        # MACD应该无法计算或返回None（数据不足）


class TestIndicatorsIntegration(unittest.TestCase):
    """技术指标集成测试"""
    
    async def test_full_indicators_workflow(self):
        """测试完整的技术指标工作流程"""
        # 创建真实的数据管理器mock
        mock_data_manager = Mock()
        
        # 创建复杂的测试数据（模拟真实股票走势）
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        prices = []
        base_price = 100
        
        for i in range(60):
            # 模拟股票价格波动
            trend = i * 0.5  # 上升趋势
            noise = (i % 10) - 5  # 随机波动
            price = base_price + trend + noise
            prices.append(price)
        
        kline_data = pd.DataFrame({
            'time_key': dates,
            'open': [p - 0.5 for p in prices],
            'close': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'volume': [1000 + i * 50 for i in range(60)],
            'turnover': [p * (1000 + i * 50) for i, p in enumerate(prices)]
        })
        
        mock_data_manager.get_historical_klines = AsyncMock(return_value=kline_data)
        
        # 创建指标管理器
        indicators_manager = IndicatorsManager(mock_data_manager)
        
        # 执行完整流程
        stock_codes = ['HK.00700']
        result = await indicators_manager.update_all_indicators(stock_codes)
        
        # 验证完整结果
        self.assertIn('HK.00700', result)
        indicators = result['HK.00700']
        
        # 验证所有指标都被计算
        self.assertIsNotNone(indicators.ma5)
        self.assertIsNotNone(indicators.ma10)
        self.assertIsNotNone(indicators.ma20)
        self.assertIsNotNone(indicators.rsi14)
        self.assertIsNotNone(indicators.macd_line)
        
        # 验证指标值的合理性
        self.assertGreater(indicators.ma5, 0)
        self.assertGreater(indicators.ma10, 0)
        self.assertGreater(indicators.ma20, 0)
        self.assertGreaterEqual(indicators.rsi14, 0)
        self.assertLessEqual(indicators.rsi14, 100)
        
        # 验证MA指标的关系（在上升趋势中，短期MA通常大于长期MA）
        # 注意：这不是绝对规律，只是在我们的测试数据中应该成立
        self.assertGreater(indicators.ma5, indicators.ma20)
        
        # 验证信号类型
        self.assertIn(indicators.rsi_signal, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])
        self.assertIn(indicators.macd_signal, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])


class TestIndicatorsEdgeCases(unittest.TestCase):
    """技术指标边界情况测试"""
    
    def test_calculator_with_extreme_values(self):
        """测试计算器处理极端值"""
        calculator = IndicatorsCalculator()
        
        # 测试极大值
        large_prices = [1e6 + i for i in range(30)]
        ma = calculator.calculate_ma(large_prices, 5)
        self.assertIsNotNone(ma)
        self.assertGreater(ma, 1e6)
        
        # 测试极小值
        small_prices = [0.001 + i * 0.0001 for i in range(30)]
        ma = calculator.calculate_ma(small_prices, 5)
        self.assertIsNotNone(ma)
        self.assertGreater(ma, 0)
        
        # 测试零值
        zero_prices = [0.0] * 30
        rsi, signal = calculator.calculate_rsi(zero_prices, 14)
        # RSI计算应该能处理零值（虽然结果可能不太有意义）
    
    def test_calculator_with_identical_values(self):
        """测试计算器处理相同值"""
        calculator = IndicatorsCalculator()
        
        # 所有价格相同
        same_prices = [100.0] * 30
        
        ma = calculator.calculate_ma(same_prices, 5)
        self.assertEqual(ma, 100.0)
        
        rsi, signal = calculator.calculate_rsi(same_prices, 14)
        # 所有价格相同时，RSI应该是特殊值或产生特定信号
        self.assertIn(signal, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])
    
    def test_calculator_with_negative_values(self):
        """测试计算器处理负值"""
        calculator = IndicatorsCalculator()
        
        # 包含负值的价格（虽然股价通常不为负，但测试健壮性）
        negative_prices = [-10 + i for i in range(30)]
        
        ma = calculator.calculate_ma(negative_prices, 5)
        self.assertIsNotNone(ma)
        
        # RSI计算应该能处理负值
        rsi, signal = calculator.calculate_rsi(negative_prices, 14)
        # 应该能产生有效的信号


if __name__ == '__main__':
    # 创建测试套件
    def run_async_tests():
        """运行异步测试"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 运行异步测试
            suite = unittest.TestSuite()
            
            # 添加需要异步运行的测试
            async_test_cases = [
                TestIndicatorsManager('test_update_all_indicators_success'),
                TestIndicatorsManager('test_update_all_indicators_empty_data'),
                TestIndicatorsManager('test_update_all_indicators_partial_data'),
                TestIndicatorsManager('test_update_all_indicators_exception_handling'),
                TestIndicatorsManager('test_update_all_indicators_insufficient_data'),
                TestIndicatorsIntegration('test_full_indicators_workflow'),
            ]
            
            for test_case in async_test_cases:
                # 将异步测试包装为同步测试
                def make_sync_test(async_test):
                    def sync_test(self):
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(async_test())
                    return sync_test
                
                # 动态添加同步版本的测试方法
                test_method = getattr(test_case, test_case._testMethodName)
                sync_method = make_sync_test(test_method)
                setattr(test_case.__class__, test_case._testMethodName + '_sync', sync_method)
        finally:
            loop.close()
    
    # 运行所有测试
    unittest.main(verbosity=2)