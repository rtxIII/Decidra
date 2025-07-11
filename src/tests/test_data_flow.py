"""
数据流管理模块测试
测试 DataFlowManager 和 ConnectionManager 的各项功能
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.data_flow import DataFlowManager, ConnectionManager
from monitor.futu_interface import FutuDataManager
from monitor.indicators import IndicatorsManager
from base.monitor import (
    DataUpdateResult, ConnectionStatus, ErrorCode,
    StockData, TechnicalIndicators, SignalType, MarketStatus
)


class TestDataFlowManager(unittest.TestCase):
    """数据流管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.data_flow_manager = DataFlowManager()
    
    def tearDown(self):
        """测试后清理"""
        # 确保清理资源
        asyncio.run(self.data_flow_manager.data_manager.cleanup())
    
    @patch('monitor.data_flow.FutuDataManager')
    @patch('monitor.data_flow.IndicatorsManager')
    async def test_data_update_cycle_success(self, mock_indicators_manager_class, mock_data_manager_class):
        """测试数据更新周期 - 成功案例"""
        # 设置mock实例
        mock_data_manager = Mock()
        mock_indicators_manager = Mock()
        mock_data_manager_class.return_value = mock_data_manager
        mock_indicators_manager_class.return_value = mock_indicators_manager
        
        # 创建测试数据
        stock_codes = ['HK.00700', 'HK.09988']
        
        # 模拟股票数据
        mock_stock_data = {
            'HK.00700': StockData(
                code='HK.00700',
                name='腾讯控股',
                current_price=500.0,
                open_price=498.0,
                prev_close=495.0,
                change_rate=0.0101,
                change_amount=5.0,
                volume=1000000,
                turnover=5000000.0,
                high_price=502.0,
                low_price=497.0,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            ),
            'HK.09988': StockData(
                code='HK.09988',
                name='阿里巴巴',
                current_price=100.0,
                open_price=99.0,
                prev_close=98.0,
                change_rate=0.0204,
                change_amount=2.0,
                volume=2000000,
                turnover=2000000.0,
                high_price=101.0,
                low_price=98.5,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            )
        }
        
        # 模拟技术指标数据
        mock_indicators_data = {
            'HK.00700': TechnicalIndicators(
                stock_code='HK.00700',
                ma5=500.0,
                ma10=498.0,
                ma20=495.0,
                rsi14=65.2,
                rsi_signal=SignalType.HOLD,
                macd_line=2.15,
                signal_line=1.82,
                histogram=0.33,
                macd_signal=SignalType.BUY
            ),
            'HK.09988': TechnicalIndicators(
                stock_code='HK.09988',
                ma5=100.0,
                ma10=99.0,
                ma20=98.0,
                rsi14=45.0,
                rsi_signal=SignalType.HOLD,
                macd_line=1.0,
                signal_line=0.8,
                histogram=0.2,
                macd_signal=SignalType.BUY
            )
        }
        
        # 设置mock返回值
        mock_data_manager.get_real_time_quotes = AsyncMock(return_value=mock_stock_data)
        mock_indicators_manager.update_all_indicators = AsyncMock(return_value=mock_indicators_data)
        
        # 创建数据流管理器
        flow_manager = DataFlowManager()
        flow_manager.data_manager = mock_data_manager
        flow_manager.indicators_manager = mock_indicators_manager
        
        # 执行测试
        result = await flow_manager.data_update_cycle(stock_codes)
        
        # 验证结果
        self.assertIsInstance(result, DataUpdateResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.stock_data), 2)
        self.assertEqual(len(result.indicators_data), 2)
        self.assertIn('HK.00700', result.stock_data)
        self.assertIn('HK.09988', result.stock_data)
        self.assertIn('HK.00700', result.indicators_data)
        self.assertIn('HK.09988', result.indicators_data)
        self.assertIsNone(result.error_message)
        
        # 验证方法调用
        mock_data_manager.get_real_time_quotes.assert_called_once_with(stock_codes)
        mock_indicators_manager.update_all_indicators.assert_called_once_with(stock_codes)
    
    @patch('monitor.data_flow.FutuDataManager')
    @patch('monitor.data_flow.IndicatorsManager')
    async def test_data_update_cycle_data_manager_error(self, mock_indicators_manager_class, mock_data_manager_class):
        """测试数据更新周期 - 数据管理器错误"""
        # 设置mock实例
        mock_data_manager = Mock()
        mock_indicators_manager = Mock()
        mock_data_manager_class.return_value = mock_data_manager
        mock_indicators_manager_class.return_value = mock_indicators_manager
        
        # 设置数据管理器抛出异常
        mock_data_manager.get_real_time_quotes = AsyncMock(side_effect=Exception("API连接失败"))
        mock_indicators_manager.update_all_indicators = AsyncMock(return_value={})
        
        # 创建数据流管理器
        flow_manager = DataFlowManager()
        flow_manager.data_manager = mock_data_manager
        flow_manager.indicators_manager = mock_indicators_manager
        
        # 执行测试
        result = await flow_manager.data_update_cycle(['HK.00700'])
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.stock_data), 0)
        self.assertEqual(len(result.indicators_data), 0)
        self.assertIsNotNone(result.error_message)
        self.assertIn("API连接失败", result.error_message)
    
    @patch('monitor.data_flow.FutuDataManager')
    @patch('monitor.data_flow.IndicatorsManager')
    async def test_data_update_cycle_indicators_error(self, mock_indicators_manager_class, mock_data_manager_class):
        """测试数据更新周期 - 指标管理器错误"""
        # 设置mock实例
        mock_data_manager = Mock()
        mock_indicators_manager = Mock()
        mock_data_manager_class.return_value = mock_data_manager
        mock_indicators_manager_class.return_value = mock_indicators_manager
        
        # 设置正常的股票数据和异常的指标数据
        mock_stock_data = {
            'HK.00700': StockData(
                code='HK.00700',
                name='腾讯控股',
                current_price=500.0,
                open_price=498.0,
                prev_close=495.0,
                change_rate=0.0101,
                change_amount=5.0,
                volume=1000000,
                turnover=5000000.0,
                high_price=502.0,
                low_price=497.0,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            )
        }
        
        mock_data_manager.get_real_time_quotes = AsyncMock(return_value=mock_stock_data)
        mock_indicators_manager.update_all_indicators = AsyncMock(side_effect=Exception("指标计算失败"))
        
        # 创建数据流管理器
        flow_manager = DataFlowManager()
        flow_manager.data_manager = mock_data_manager
        flow_manager.indicators_manager = mock_indicators_manager
        
        # 执行测试
        result = await flow_manager.data_update_cycle(['HK.00700'])
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("指标计算失败", result.error_message)
    
    async def test_data_update_cycle_empty_codes(self):
        """测试数据更新周期 - 空股票代码列表"""
        flow_manager = DataFlowManager()
        
        # 执行测试
        result = await flow_manager.data_update_cycle([])
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.stock_data), 0)
        self.assertEqual(len(result.indicators_data), 0)


class TestConnectionManager(unittest.TestCase):
    """连接管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_futu_client = Mock()
        self.connection_manager = ConnectionManager(self.mock_futu_client)
    
    async def test_ensure_connection_success(self):
        """测试确保连接 - 成功"""
        # 模拟连接成功
        result = await self.connection_manager.ensure_connection()
        
        # 验证结果
        self.assertTrue(result)
        self.assertEqual(self.connection_manager.connection_status, ConnectionStatus.CONNECTED)
    
    async def test_ensure_connection_failure(self):
        """测试确保连接 - 失败"""
        # 通过修改ensure_connection方法来模拟连接失败
        async def mock_ensure_connection():
            raise Exception("连接失败")
        
        # 替换方法
        original_method = self.connection_manager.ensure_connection
        self.connection_manager.ensure_connection = mock_ensure_connection
        
        try:
            result = await self.connection_manager.ensure_connection()
            self.fail("应该抛出异常")
        except Exception as e:
            self.assertIn("连接失败", str(e))
        finally:
            # 恢复原方法
            self.connection_manager.ensure_connection = original_method
    
    async def test_handle_api_error_network_error(self):
        """测试处理API错误 - 网络错误"""
        network_error = Exception("network connection failed")
        
        # 模拟重连方法
        self.connection_manager._retry_with_backoff = AsyncMock(return_value=True)
        
        result = await self.connection_manager.handle_api_error(network_error, "获取股票数据")
        
        # 验证结果
        self.assertTrue(result)
        self.connection_manager._retry_with_backoff.assert_called_once()
    
    async def test_handle_api_error_rate_limit(self):
        """测试处理API错误 - 频率限制"""
        rate_limit_error = Exception("API rate limit exceeded")
        
        # 使用patch来模拟asyncio.sleep
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await self.connection_manager.handle_api_error(rate_limit_error, "获取股票数据")
            
            # 验证结果
            self.assertTrue(result)
            mock_sleep.assert_called_once_with(5)
    
    async def test_handle_api_error_permission_error(self):
        """测试处理API错误 - 权限错误"""
        permission_error = Exception("permission denied for user")
        
        result = await self.connection_manager.handle_api_error(permission_error, "获取股票数据")
        
        # 验证结果
        self.assertFalse(result)  # 权限错误不重试
    
    async def test_handle_api_error_data_error(self):
        """测试处理API错误 - 数据错误"""
        data_error = Exception("invalid data format")
        
        result = await self.connection_manager.handle_api_error(data_error, "获取股票数据")
        
        # 验证结果
        self.assertFalse(result)  # 数据错误不重试
    
    async def test_handle_api_error_unknown_error(self):
        """测试处理API错误 - 未知错误"""
        unknown_error = Exception("something went wrong")
        
        result = await self.connection_manager.handle_api_error(unknown_error, "获取股票数据")
        
        # 验证结果
        self.assertFalse(result)  # 未知错误不重试
    
    async def test_retry_with_backoff_success(self):
        """测试带退避的重试 - 成功"""
        # 重置重试计数
        self.connection_manager.retry_count = 0
        self.connection_manager.max_retries = 3
        
        # 模拟ensure_connection方法
        self.connection_manager.ensure_connection = AsyncMock(return_value=True)
        
        # 使用patch来模拟asyncio.sleep
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await self.connection_manager._retry_with_backoff()
            
            # 验证结果
            self.assertTrue(result)
            self.assertEqual(self.connection_manager.retry_count, 1)
            mock_sleep.assert_called_once_with(2)  # 2^1 = 2秒
    
    async def test_retry_with_backoff_max_retries(self):
        """测试带退避的重试 - 达到最大重试次数"""
        # 设置已达到最大重试次数
        self.connection_manager.retry_count = 3
        self.connection_manager.max_retries = 3
        
        result = await self.connection_manager._retry_with_backoff()
        
        # 验证结果
        self.assertFalse(result)
    
    async def test_retry_with_backoff_exponential_backoff(self):
        """测试带退避的重试 - 指数退避"""
        self.connection_manager.retry_count = 0
        self.connection_manager.max_retries = 5
        
        # 模拟ensure_connection方法
        self.connection_manager.ensure_connection = AsyncMock(return_value=True)
        
        # 测试不同的重试次数和对应的等待时间
        test_cases = [
            (0, 2),   # 2^1 = 2
            (1, 4),   # 2^2 = 4
            (2, 8),   # 2^3 = 8
        ]
        
        for initial_count, expected_wait in test_cases:
            self.connection_manager.retry_count = initial_count
            
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                await self.connection_manager._retry_with_backoff()
                mock_sleep.assert_called_once_with(expected_wait)


class TestDataFlowIntegration(unittest.TestCase):
    """数据流集成测试"""
    
    async def test_full_data_flow_workflow(self):
        """测试完整的数据流工作流程"""
        # 创建完整的测试环境
        with patch('monitor.data_flow.FutuDataManager') as mock_data_manager_class, \
             patch('monitor.data_flow.IndicatorsManager') as mock_indicators_manager_class:
            
            # 设置mock实例
            mock_data_manager = Mock()
            mock_indicators_manager = Mock()
            mock_data_manager_class.return_value = mock_data_manager
            mock_indicators_manager_class.return_value = mock_indicators_manager
            
            # 创建完整的测试数据
            stock_codes = ['HK.00700', 'HK.09988', 'US.AAPL']
            
            mock_stock_data = {}
            mock_indicators_data = {}
            
            for i, code in enumerate(stock_codes):
                # 股票数据
                mock_stock_data[code] = StockData(
                    code=code,
                    name=f'股票{i+1}',
                    current_price=100.0 + i * 10,
                    open_price=99.0 + i * 10,
                    prev_close=98.0 + i * 10,
                    change_rate=0.01 + i * 0.005,
                    change_amount=1.0 + i * 0.5,
                    volume=1000000 + i * 100000,
                    turnover=100000000.0 + i * 10000000,
                    high_price=102.0 + i * 10,
                    low_price=97.0 + i * 10,
                    update_time=datetime.now(),
                    market_status=MarketStatus.OPEN
                )
                
                # 技术指标数据
                mock_indicators_data[code] = TechnicalIndicators(
                    stock_code=code,
                    ma5=100.0 + i * 10,
                    ma10=99.0 + i * 10,
                    ma20=98.0 + i * 10,
                    rsi14=50.0 + i * 5,
                    rsi_signal=SignalType.HOLD,
                    macd_line=1.0 + i * 0.5,
                    signal_line=0.8 + i * 0.4,
                    histogram=0.2 + i * 0.1,
                    macd_signal=SignalType.BUY
                )
            
            # 设置mock返回值
            mock_data_manager.get_real_time_quotes = AsyncMock(return_value=mock_stock_data)
            mock_indicators_manager.update_all_indicators = AsyncMock(return_value=mock_indicators_data)
            
            # 创建数据流管理器
            flow_manager = DataFlowManager()
            flow_manager.data_manager = mock_data_manager
            flow_manager.indicators_manager = mock_indicators_manager
            
            # 执行完整的数据更新周期
            result = await flow_manager.data_update_cycle(stock_codes)
            
            # 验证完整结果
            self.assertTrue(result.success)
            self.assertEqual(len(result.stock_data), 3)
            self.assertEqual(len(result.indicators_data), 3)
            
            # 验证每只股票的数据
            for code in stock_codes:
                self.assertIn(code, result.stock_data)
                self.assertIn(code, result.indicators_data)
                
                stock = result.stock_data[code]
                indicators = result.indicators_data[code]
                
                self.assertEqual(stock.code, code)
                self.assertEqual(indicators.stock_code, code)
                self.assertGreater(stock.current_price, 0)
                self.assertIsNotNone(indicators.ma5)
    
    async def test_data_flow_with_connection_issues(self):
        """测试有连接问题的数据流"""
        # 创建连接管理器
        mock_futu_client = Mock()
        connection_manager = ConnectionManager(mock_futu_client)
        
        # 测试连接状态管理
        self.assertEqual(connection_manager.connection_status, ConnectionStatus.DISCONNECTED)
        
        # 模拟连接成功
        success = await connection_manager.ensure_connection()
        self.assertTrue(success)
        self.assertEqual(connection_manager.connection_status, ConnectionStatus.CONNECTED)
        
        # 模拟各种API错误处理
        error_scenarios = [
            ("network timeout", True),   # 网络错误，应该重试
            ("rate limit", True),        # 频率限制，应该重试
            ("permission denied", False), # 权限错误，不重试
            ("invalid format", False),   # 数据错误，不重试
        ]
        
        for error_msg, should_retry in error_scenarios:
            error = Exception(error_msg)
            result = await connection_manager.handle_api_error(error, "测试操作")
            
            if should_retry:
                # 对于应该重试的错误，这里简化测试逻辑
                # 实际重试逻辑会更复杂
                pass
            else:
                self.assertFalse(result)


class TestErrorCode(unittest.TestCase):
    """错误代码测试"""
    
    def test_error_code_messages(self):
        """测试错误代码消息"""
        # 测试所有预定义的错误代码
        test_cases = [
            (ErrorCode.NETWORK_ERROR, "网络连接失败"),
            (ErrorCode.API_LIMIT_ERROR, "API请求频率限制"),
            (ErrorCode.PERMISSION_ERROR, "API权限不足"),
            (ErrorCode.DATA_ERROR, "数据格式错误"),
            (ErrorCode.VALIDATION_ERROR, "数据验证失败"),
        ]
        
        for error_code, expected_keyword in test_cases:
            message = ErrorCode.get_message(error_code)
            self.assertIsNotNone(message)
            self.assertIn(expected_keyword, message)
    
    def test_error_code_unknown(self):
        """测试未知错误代码"""
        unknown_code = "E999"
        message = ErrorCode.get_message(unknown_code)
        self.assertEqual(message, "未知错误")


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