"""
富途市场接口测试模块
测试富途市场模块的各项功能
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.futu_market import FutuMarket
from base.monitor import StockData, MarketStatus


class TestFutuMarket(unittest.TestCase):
    """富途市场模块测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.futu_market = FutuMarket()
    
    def tearDown(self):
        """测试后清理"""
        # 确保清理资源
        asyncio.run(self.data_manager.cleanup())
    
    @patch('monitor.futu_interface.FutuMarket')
    def test_init(self, mock_futu_market):
        """测试初始化"""
        manager = FutuDataManager()
        
        # 验证初始化状态
        self.assertIsNotNone(manager.futu_market)
        self.assertEqual(manager.subscribed_stocks, set())
        self.assertEqual(manager.subscription_callbacks, {})
        self.assertIn("QUOTE", manager.subscription_types)
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_get_real_time_quotes(self, mock_futu_market):
        """测试获取实时行情数据"""
        # 模拟富途API返回数据
        mock_snapshots = [
            {
                'code': 'HK.00700',
                'stock_name': '腾讯控股',
                'cur_price': 500.0,
                'open_price': 498.0,
                'prev_close_price': 495.0,
                'high_price': 502.0,
                'low_price': 497.0,
                'volume': 1000000,
                'turnover': 5000000.0
            }
        ]
        
        mock_quotes = []
        
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.return_value = mock_snapshots
        mock_instance.get_stock_quote.return_value = mock_quotes
        
        # 创建管理器实例
        manager = FutuDataManager()
        
        # 执行测试
        result = await manager.get_real_time_quotes(['HK.00700'])
        
        # 验证结果
        self.assertIn('HK.00700', result)
        stock_data = result['HK.00700']
        self.assertIsInstance(stock_data, StockData)
        self.assertEqual(stock_data.code, 'HK.00700')
        self.assertEqual(stock_data.name, '腾讯控股')
        self.assertEqual(stock_data.current_price, 500.0)
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_get_historical_klines(self, mock_futu_market):
        """测试获取历史K线数据"""
        # 模拟K线数据
        mock_kline_data = [{
            'kline_list': [
                {
                    'time_key': '2024-01-01',
                    'open': 100.0,
                    'close': 105.0,
                    'high': 106.0,
                    'low': 99.0,
                    'volume': 1000,
                    'turnover': 102500.0
                },
                {
                    'time_key': '2024-01-02',
                    'open': 105.0,
                    'close': 107.0,
                    'high': 108.0,
                    'low': 104.0,
                    'volume': 1200,
                    'turnover': 127200.0
                }
            ]
        }]
        
        mock_instance = mock_futu_market.return_value
        mock_instance.get_cur_kline.return_value = mock_kline_data
        
        # 创建管理器实例
        manager = FutuDataManager()
        
        # 执行测试
        result = await manager.get_historical_klines('HK.00700', 30)
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('time_key', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)
        self.assertEqual(result.iloc[0]['open'], 100.0)
        self.assertEqual(result.iloc[1]['close'], 107.0)
    
    async def test_validate_stock_code(self):
        """测试股票代码验证"""
        manager = FutuDataManager()
        
        # 测试有效代码
        valid_codes = ['HK.00700', 'US.AAPL', 'SH.600000', 'SZ.000001']
        for code in valid_codes:
            result = await manager.validate_stock_code(code)
            self.assertTrue(result, f"代码 {code} 应该有效")
        
        # 测试无效代码
        invalid_codes = ['', '700', 'HK', 'INVALID.CODE', 'XX.00700']
        for code in invalid_codes:
            result = await manager.validate_stock_code(code)
            self.assertFalse(result, f"代码 {code} 应该无效")
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_get_market_status(self, mock_futu_market):
        """测试获取市场状态"""
        # 模拟市场状态数据
        mock_states = [
            {'code': 'HK.00700', 'market_state': 'NORMAL'},
            {'code': 'HK.09988', 'market_state': 'PRE_MARKET_BEGIN'},
            {'code': 'US.AAPL', 'market_state': 'AFTER_HOURS_BEGIN'}
        ]
        
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_state.return_value = mock_states
        
        # 创建管理器实例
        manager = FutuDataManager()
        
        # 执行测试
        result = await manager.get_market_status(['HK.00700', 'HK.09988', 'US.AAPL'])
        
        # 验证结果
        self.assertEqual(result['HK.00700'], MarketStatus.OPEN)
        self.assertEqual(result['HK.09988'], MarketStatus.PRE_MARKET)
        self.assertEqual(result['US.AAPL'], MarketStatus.AFTER_MARKET)
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_subscribe_real_time_data(self, mock_futu_market):
        """测试订阅实时数据"""
        mock_instance = mock_futu_market.return_value
        mock_instance.subscribe.return_value = True
        
        # 创建管理器实例
        manager = FutuDataManager()
        
        # 模拟回调函数
        callback = Mock()
        
        # 执行测试
        result = await manager.subscribe_real_time_data(['HK.00700'], callback)
        
        # 验证结果
        self.assertTrue(result)
        self.assertIn('HK.00700', manager.subscribed_stocks)
        self.assertEqual(manager.subscription_callbacks['HK.00700'], callback)
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_unsubscribe_real_time_data(self, mock_futu_market):
        """测试取消订阅实时数据"""
        mock_instance = mock_futu_market.return_value
        mock_instance.subscribe.return_value = True
        mock_instance.unsubscribe.return_value = True
        
        # 创建管理器实例
        manager = FutuDataManager()
        
        # 先订阅
        callback = Mock()
        await manager.subscribe_real_time_data(['HK.00700'], callback)
        
        # 然后取消订阅
        result = await manager.unsubscribe_real_time_data(['HK.00700'])
        
        # 验证结果
        self.assertTrue(result)
        self.assertNotIn('HK.00700', manager.subscribed_stocks)
        self.assertNotIn('HK.00700', manager.subscription_callbacks)
    
    def test_convert_to_stock_data(self):
        """测试数据转换功能"""
        manager = FutuDataManager()
        
        # 模拟快照数据
        snapshot = {
            'code': 'HK.00700',
            'stock_name': '腾讯控股',
            'cur_price': 500.0,
            'open_price': 498.0,
            'prev_close_price': 495.0,
            'high_price': 502.0,
            'low_price': 497.0,
            'volume': 1000000,
            'turnover': 5000000.0
        }
        
        # 执行转换
        stock_data = manager._convert_to_stock_data(snapshot, [])
        
        # 验证结果
        self.assertEqual(stock_data.code, 'HK.00700')
        self.assertEqual(stock_data.name, '腾讯控股')
        self.assertEqual(stock_data.current_price, 500.0)
        self.assertEqual(stock_data.prev_close, 495.0)
        self.assertAlmostEqual(stock_data.change_rate, 5.0/495.0, places=5)
        self.assertEqual(stock_data.change_amount, 5.0)
    
    def test_convert_kline_to_dataframe(self):
        """测试K线数据转换"""
        manager = FutuDataManager()
        
        # 模拟K线数据
        kline_data = {
            'kline_list': [
                {
                    'time_key': '2024-01-01',
                    'open': 100.0,
                    'close': 105.0,
                    'high': 106.0,
                    'low': 99.0,
                    'volume': 1000,
                    'turnover': 102500.0
                }
            ]
        }
        
        # 执行转换
        df = manager._convert_kline_to_dataframe(kline_data)
        
        # 验证结果
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['open'], 100.0)
        self.assertEqual(df.iloc[0]['close'], 105.0)
        self.assertEqual(df.iloc[0]['volume'], 1000)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_data_flow_integration(self, mock_futu_market):
        """测试数据流集成"""
        # 模拟完整的数据流
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.return_value = [{
            'code': 'HK.00700',
            'stock_name': '腾讯控股',
            'cur_price': 500.0,
            'open_price': 498.0,
            'prev_close_price': 495.0,
            'high_price': 502.0,
            'low_price': 497.0,
            'volume': 1000000,
            'turnover': 5000000.0
        }]
        mock_instance.get_stock_quote.return_value = []
        mock_instance.get_cur_kline.return_value = [{
            'kline_list': [
                {
                    'time_key': '2024-01-01',
                    'open': 100.0,
                    'close': 105.0,
                    'high': 106.0,
                    'low': 99.0,
                    'volume': 1000,
                    'turnover': 102500.0
                }
            ] * 30  # 30天数据
        }]
        
        # 创建管理器
        manager = FutuDataManager()
        
        # 测试完整流程
        stock_codes = ['HK.00700']
        
        # 1. 获取实时数据
        quotes = await manager.get_real_time_quotes(stock_codes)
        self.assertIn('HK.00700', quotes)
        
        # 2. 获取历史数据
        klines = await manager.get_historical_klines('HK.00700', 30)
        self.assertFalse(klines.empty)
        
        # 3. 验证股票代码
        valid = await manager.validate_stock_code('HK.00700')
        self.assertTrue(valid)
        
        # 清理
        await manager.cleanup()


if __name__ == '__main__':
    # 运行异步测试
    def run_async_test(test_func):
        """运行异步测试的辅助函数"""
        return asyncio.run(test_func())
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestFutuDataManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印结果
    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
    else:
        print(f"\n❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")