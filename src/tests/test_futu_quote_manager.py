"""
富途API行情管理器测试用例

测试src/api/futu.py中的行情管理器功能
使用unittest框架，不使用mock
"""

import unittest
import sys
import os
from unittest import TestCase

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.futu import (
    FutuConfig, 
    FutuClient, 
    QuoteManager,
    StockInfo,
    KLineData,
    StockQuote,
    MarketSnapshot,
    FutuQuoteException,
    FutuConnectException
)


class TestDataModels(TestCase):
    """数据模型测试"""
    
    def test_stock_info_creation(self):
        """测试StockInfo数据模型创建"""
        data = {
            'code': 'HK.00700',
            'name': '腾讯控股',
            'stock_type': 'STOCK',
            'list_time': '2004-06-16',
            'stock_id': 700,
            'lot_size': 100
        }
        
        stock_info = StockInfo.from_dict(data)
        
        self.assertEqual(stock_info.code, 'HK.00700')
        self.assertEqual(stock_info.name, '腾讯控股')
        self.assertEqual(stock_info.stock_type, 'STOCK')
        self.assertEqual(stock_info.list_time, '2004-06-16')
        self.assertEqual(stock_info.stock_id, 700)
        self.assertEqual(stock_info.lot_size, 100)
    
    def test_stock_info_from_empty_dict(self):
        """测试从空字典创建StockInfo"""
        stock_info = StockInfo.from_dict({})
        
        self.assertEqual(stock_info.code, '')
        self.assertEqual(stock_info.name, '')
        self.assertEqual(stock_info.stock_type, '')
        self.assertEqual(stock_info.list_time, '')
        self.assertEqual(stock_info.stock_id, 0)
        self.assertEqual(stock_info.lot_size, 0)
    
    def test_kline_data_creation(self):
        """测试KLineData数据模型创建"""
        data = {
            'code': 'HK.00700',
            'time_key': '2024-01-01 09:30:00',
            'open': 350.0,
            'close': 355.0,
            'high': 360.0,
            'low': 348.0,
            'volume': 1000000,
            'turnover': 354000000.0,
            'pe_ratio': 15.5,
            'turnover_rate': 0.8
        }
        
        kline = KLineData.from_dict(data)
        
        self.assertEqual(kline.code, 'HK.00700')
        self.assertEqual(kline.time_key, '2024-01-01 09:30:00')
        self.assertEqual(kline.open, 350.0)
        self.assertEqual(kline.close, 355.0)
        self.assertEqual(kline.high, 360.0)
        self.assertEqual(kline.low, 348.0)
        self.assertEqual(kline.volume, 1000000)
        self.assertEqual(kline.turnover, 354000000.0)
        self.assertEqual(kline.pe_ratio, 15.5)
        self.assertEqual(kline.turnover_rate, 0.8)
    
    def test_kline_data_type_conversion(self):
        """测试KLineData数据类型转换"""
        data = {
            'code': 'HK.00700',
            'time_key': '2024-01-01',
            'open': '350.5',
            'close': '355.2',
            'high': '360.8',
            'low': '348.1',
            'volume': '1000000',
            'turnover': '354000000.5',
        }
        
        kline = KLineData.from_dict(data)
        
        self.assertIsInstance(kline.open, float)
        self.assertIsInstance(kline.close, float)
        self.assertIsInstance(kline.high, float)
        self.assertIsInstance(kline.low, float)
        self.assertIsInstance(kline.volume, int)
        self.assertIsInstance(kline.turnover, float)
        self.assertIsNone(kline.pe_ratio)
        self.assertIsNone(kline.turnover_rate)
    
    def test_stock_quote_creation(self):
        """测试StockQuote数据模型创建"""
        data = {
            'code': 'HK.00700',
            'data_date': '2024-01-01',
            'data_time': '16:00:00',
            'last_price': 355.0,
            'open_price': 350.0,
            'high_price': 360.0,
            'low_price': 348.0,
            'prev_close_price': 352.0,
            'volume': 1000000,
            'turnover': 354000000.0,
            'turnover_rate': 0.8,
            'suspension': False
        }
        
        quote = StockQuote.from_dict(data)
        
        self.assertEqual(quote.code, 'HK.00700')
        self.assertEqual(quote.data_date, '2024-01-01')
        self.assertEqual(quote.data_time, '16:00:00')
        self.assertEqual(quote.last_price, 355.0)
        self.assertEqual(quote.open_price, 350.0)
        self.assertEqual(quote.high_price, 360.0)
        self.assertEqual(quote.low_price, 348.0)
        self.assertEqual(quote.prev_close_price, 352.0)
        self.assertEqual(quote.volume, 1000000)
        self.assertEqual(quote.turnover, 354000000.0)
        self.assertEqual(quote.turnover_rate, 0.8)
        self.assertFalse(quote.suspension)
    
    def test_market_snapshot_creation(self):
        """测试MarketSnapshot数据模型创建"""
        data = {
            'code': 'HK.00700',
            'update_time': '2024-01-01 16:00:00',
            'last_price': 355.0,
            'open_price': 350.0,
            'high_price': 360.0,
            'low_price': 348.0,
            'prev_close_price': 352.0,
            'volume': 1000000,
            'turnover': 354000000.0,
            'turnover_rate': 0.8,
            'amplitude': 3.4
        }
        
        snapshot = MarketSnapshot.from_dict(data)
        
        self.assertEqual(snapshot.code, 'HK.00700')
        self.assertEqual(snapshot.update_time, '2024-01-01 16:00:00')
        self.assertEqual(snapshot.last_price, 355.0)
        self.assertEqual(snapshot.open_price, 350.0)
        self.assertEqual(snapshot.high_price, 360.0)
        self.assertEqual(snapshot.low_price, 348.0)
        self.assertEqual(snapshot.prev_close_price, 352.0)
        self.assertEqual(snapshot.volume, 1000000)
        self.assertEqual(snapshot.turnover, 354000000.0)
        self.assertEqual(snapshot.turnover_rate, 0.8)
        self.assertEqual(snapshot.amplitude, 3.4)


class TestQuoteManager(TestCase):
    """行情管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.config = FutuConfig(
            host="127.0.0.1",
            port=11111,
            default_trd_env="SIMULATE"
        )
        self.client = FutuClient(self.config)
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'client'):
            self.client.disconnect()
    
    def test_quote_manager_initialization(self):
        """测试行情管理器初始化"""
        self.assertIsInstance(self.client.quote, QuoteManager)
        self.assertEqual(self.client.quote.client, self.client)
        self.assertIsNotNone(self.client.quote.logger)
    
    def test_get_quote_context_not_connected(self):
        """测试未连接时获取行情上下文"""
        with self.assertRaises(FutuConnectException):
            self.client.quote._get_quote_context()
    
    def test_handle_response_success(self):
        """测试处理成功响应"""
        import futu as ft
        
        # 模拟成功响应
        test_data = "success_data"
        result = self.client.quote._handle_response(ft.RET_OK, test_data, "测试操作")
        
        self.assertEqual(result, test_data)
    
    def test_handle_response_failure(self):
        """测试处理失败响应"""
        import futu as ft
        
        # 模拟失败响应
        with self.assertRaises(FutuQuoteException) as context:
            self.client.quote._handle_response(-1, "error_message", "测试操作")
        
        self.assertEqual(context.exception.ret_code, -1)
        self.assertIn("error_message", str(context.exception))


class TestQuoteManagerMethods(TestCase):
    """行情管理器方法测试（不依赖真实连接）"""
    
    def setUp(self):
        """测试前设置"""
        self.client = FutuClient()
    
    def test_quote_manager_methods_exist(self):
        """测试行情管理器方法是否存在"""
        quote_manager = self.client.quote
        
        # 检查基础行情接口
        self.assertTrue(hasattr(quote_manager, 'get_stock_info'))
        self.assertTrue(hasattr(quote_manager, 'get_stock_quote'))
        self.assertTrue(hasattr(quote_manager, 'get_market_snapshot'))
        
        # 检查K线数据接口
        self.assertTrue(hasattr(quote_manager, 'get_current_kline'))
        self.assertTrue(hasattr(quote_manager, 'get_history_kline'))
        
        # 检查实用方法
        self.assertTrue(hasattr(quote_manager, 'get_trading_days'))
    
    def test_quote_manager_method_signatures(self):
        """测试行情管理器方法签名"""
        quote_manager = self.client.quote
        
        # 测试方法是否可调用
        self.assertTrue(callable(quote_manager.get_stock_info))
        self.assertTrue(callable(quote_manager.get_stock_quote))
        self.assertTrue(callable(quote_manager.get_market_snapshot))
        self.assertTrue(callable(quote_manager.get_current_kline))
        self.assertTrue(callable(quote_manager.get_history_kline))
        self.assertTrue(callable(quote_manager.get_trading_days))
    
    def test_methods_raise_exception_when_not_connected(self):
        """测试未连接时方法抛出异常"""
        quote_manager = self.client.quote
        
        # 由于未连接，所有方法都应该抛出异常
        with self.assertRaises(FutuConnectException):
            quote_manager.get_stock_info()
        
        with self.assertRaises(FutuConnectException):
            quote_manager.get_stock_quote(['HK.00700'])
        
        with self.assertRaises(FutuConnectException):
            quote_manager.get_market_snapshot(['HK.00700'])
        
        with self.assertRaises(FutuConnectException):
            quote_manager.get_current_kline('HK.00700')
        
        with self.assertRaises(FutuConnectException):
            quote_manager.get_history_kline('HK.00700', '2024-01-01', '2024-01-31')
        
        with self.assertRaises(FutuConnectException):
            quote_manager.get_trading_days()


class TestQuoteManagerParameters(TestCase):
    """行情管理器参数验证测试"""
    
    def setUp(self):
        """测试前设置"""
        self.client = FutuClient()
        self.quote_manager = self.client.quote
    
    def test_get_stock_info_default_parameters(self):
        """测试get_stock_info默认参数"""
        # 模拟连接状态来测试参数
        self.client._connected = True
        self.client._quote_ctx = object()  # 占位符
        
        # 由于没有真实连接，方法会失败，但我们可以测试参数处理
        try:
            self.quote_manager.get_stock_info()
        except AttributeError:
            # 预期的，因为_quote_ctx不是真实的对象
            pass
        except FutuQuoteException:
            # 也是预期的，因为没有真实连接
            pass
    
    def test_get_current_kline_parameters(self):
        """测试get_current_kline参数"""
        # 测试默认参数值
        self.client._connected = True
        self.client._quote_ctx = object()
        
        try:
            self.quote_manager.get_current_kline('HK.00700')
        except (AttributeError, FutuQuoteException):
            # 预期的异常
            pass
        
        try:
            self.quote_manager.get_current_kline(
                'HK.00700', 
                ktype='K_1M', 
                num=50, 
                autype='hfq'
            )
        except (AttributeError, FutuQuoteException):
            # 预期的异常
            pass


class TestIntegrationWithFutuClient(TestCase):
    """与FutuClient的集成测试"""
    
    def test_client_has_quote_manager(self):
        """测试客户端包含行情管理器"""
        client = FutuClient()
        
        self.assertTrue(hasattr(client, 'quote'))
        self.assertIsInstance(client.quote, QuoteManager)
    
    def test_quote_manager_has_client_reference(self):
        """测试行情管理器包含客户端引用"""
        client = FutuClient()
        
        self.assertEqual(client.quote.client, client)
    
    def test_multiple_clients_have_separate_quote_managers(self):
        """测试多个客户端有独立的行情管理器"""
        client1 = FutuClient()
        client2 = FutuClient()
        
        self.assertNotEqual(client1.quote, client2.quote)
        self.assertEqual(client1.quote.client, client1)
        self.assertEqual(client2.quote.client, client2)


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    
    # 加载所有测试类
    test_classes = [
        TestDataModels,
        TestQuoteManager,
        TestQuoteManagerMethods,
        TestQuoteManagerParameters,
        TestIntegrationWithFutuClient
    ]
    
    suites = []
    for test_class in test_classes:
        suite = loader.loadTestsFromTestCase(test_class)
        suites.append(suite)
    
    # 合并所有测试套件
    combined_suite = unittest.TestSuite(suites)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(combined_suite)
    
    # 输出测试结果摘要
    print(f"\n{'='*50}")
    print(f"行情管理器测试完成: 运行 {result.testsRun} 个测试")
    print(f"失败: {len(result.failures)} 个")
    print(f"错误: {len(result.errors)} 个")
    print(f"跳过: {len(result.skipped)} 个")
    
    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    print(f"{'='*50}") 