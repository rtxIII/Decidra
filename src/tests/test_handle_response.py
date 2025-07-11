"""
测试_handle_response方法的DataFrame格式处理

测试futu_trade.py和futu_quote.py中_handle_response方法对于
不同类型数据的处理，特别是DataFrame格式的处理
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.futu_trade import TradeManager
from api.futu_quote import QuoteManager
from base.futu_class import FutuTradeException, FutuQuoteException

try:
    import futu as ft
except ImportError:
    # Mock futu if not available
    ft = Mock()
    ft.RET_OK = 0
    ft.RET_ERROR = -1


class TestHandleResponse(unittest.TestCase):
    """测试_handle_response方法的DataFrame处理"""
    
    def setUp(self):
        """测试前置设置"""
        # Mock client
        self.mock_client = Mock()
        self.mock_client.is_connected = True
        self.mock_client._quote_ctx = Mock()
        self.mock_client._trade_ctx = Mock()
        
        # 初始化管理器
        self.trade_manager = TradeManager(self.mock_client)
        self.quote_manager = QuoteManager(self.mock_client)
    
    def test_trade_handle_response_success_single_row_dataframe(self):
        """测试交易管理器处理单行DataFrame"""
        # 创建测试DataFrame
        test_df = pd.DataFrame([{
            'acc_id': 123456,
            'total_assets': 100000.50,
            'cash': 50000.25,
            'market_value': 50000.25,
            'special_value': pd.NA  # 测试NaN处理
        }])
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试操作")
        
        # 应该返回字典格式
        self.assertIsInstance(result, dict)
        self.assertEqual(result['acc_id'], 123456)
        self.assertEqual(result['total_assets'], 100000.50)
        self.assertIsNone(result['special_value'])  # NaN应该转换为None
    
    def test_trade_handle_response_success_multi_row_dataframe(self):
        """测试交易管理器处理多行DataFrame"""
        # 创建测试DataFrame
        test_df = pd.DataFrame([
            {'code': 'HK.00700', 'qty': 100, 'price': 500.0},
            {'code': 'HK.00388', 'qty': 200, 'price': 100.0}
        ])
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试操作")
        
        # 应该返回DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['code'], 'HK.00700')
    
    def test_trade_handle_response_empty_dataframe(self):
        """测试交易管理器处理空DataFrame"""
        test_df = pd.DataFrame()
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试操作")
        
        # 应该返回空DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
    
    def test_trade_handle_response_non_dataframe(self):
        """测试交易管理器处理非DataFrame数据"""
        test_data = {"result": "success", "data": [1, 2, 3]}
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_data, "测试操作")
        
        # 应该直接返回原数据
        self.assertEqual(result, test_data)
    
    def test_trade_handle_response_error(self):
        """测试交易管理器处理错误响应"""
        with self.assertRaises(FutuTradeException):
            self.trade_manager._handle_response(ft.RET_ERROR, "Error message", "测试操作")
    
    def test_quote_handle_response_success_single_row_dataframe(self):
        """测试行情管理器处理单行DataFrame"""
        # 创建测试DataFrame
        test_df = pd.DataFrame([{
            'code': 'HK.00700',
            'cur_price': 500.50,
            'change_rate': 0.05,
            'volume': 1000000,
            'nan_value': pd.NA  # 测试NaN处理
        }])
        
        result = self.quote_manager._handle_response(ft.RET_OK, test_df, "获取股票报价")
        
        # 应该返回字典格式
        self.assertIsInstance(result, dict)
        self.assertEqual(result['code'], 'HK.00700')
        self.assertEqual(result['cur_price'], 500.50)
        self.assertIsNone(result['nan_value'])  # NaN应该转换为None
    
    def test_quote_handle_response_market_state(self):
        """测试行情管理器处理市场状态数据"""
        # 创建测试DataFrame
        test_df = pd.DataFrame([
            {'code': 'HK.00700', 'market_state': 'TRADING'},
            {'code': 'HK.00388', 'market_state': 'CLOSED'}
        ])
        
        result = self.quote_manager._handle_response(ft.RET_OK, test_df, "获取市场状态")
        
        # 市场状态应该返回DataFrame（特殊处理）
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
    
    def test_quote_handle_response_trading_days(self):
        """测试行情管理器处理交易日历数据"""
        # 模拟交易日历可能返回的列表格式
        test_data = ['2024-01-01', '2024-01-02', '2024-01-03']
        
        result = self.quote_manager._handle_response(ft.RET_OK, test_data, "获取交易日历")
        
        # 应该直接返回列表
        self.assertEqual(result, test_data)
    
    def test_quote_handle_response_error(self):
        """测试行情管理器处理错误响应"""
        with self.assertRaises(FutuQuoteException):
            self.quote_manager._handle_response(ft.RET_ERROR, "Error message", "测试操作")
    
    def test_handle_response_with_complex_dataframe(self):
        """测试处理包含复杂数据类型的DataFrame"""
        # 创建包含各种数据类型的DataFrame
        test_df = pd.DataFrame([{
            'string_col': 'test_string',
            'int_col': 123,
            'float_col': 123.456,
            'nan_col': pd.NA,
            'null_col': None,
            'bool_col': True,
            'object_col': {'nested': 'data'}  # 复杂对象
        }])
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试复杂数据")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['string_col'], 'test_string')
        self.assertEqual(result['int_col'], 123)
        self.assertEqual(result['float_col'], 123.456)
        self.assertIsNone(result['nan_col'])
        self.assertIsNone(result['null_col'])
        self.assertEqual(result['bool_col'], True)
    
    def test_handle_response_dataframe_conversion_error(self):
        """测试DataFrame转换过程中的异常处理"""
        # 创建一个会导致转换异常的DataFrame
        test_df = pd.DataFrame([{'col': 'value'}])
        
        # Mock pandas方法以触发异常
        with patch('pandas.notnull', side_effect=Exception("转换异常")):
            result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试异常")
            
            # 应该返回原始数据并记录警告
            self.assertIsInstance(result, pd.DataFrame)
    
    def test_handle_response_without_pandas(self):
        """测试在没有pandas的情况下的处理"""
        test_data = "some_data"
        
        # Mock import pandas失败
        with patch('builtins.__import__', side_effect=ImportError("No pandas")):
            result = self.trade_manager._handle_response(ft.RET_OK, test_data, "测试无pandas")
            
            # 应该直接返回原数据
            self.assertEqual(result, test_data)
    
    def test_handle_response_dataframe_dtype_conversion(self):
        """测试DataFrame数据类型转换"""
        # 创建包含object类型的DataFrame
        test_df = pd.DataFrame([{
            'object_str': 'normal_string',
            'object_nan': 'nan',  # 字符串'nan'
            'object_number': '123'
        }])
        
        # 确保列是object类型
        test_df = test_df.astype('object')
        
        result = self.trade_manager._handle_response(ft.RET_OK, test_df, "测试数据类型")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['object_str'], 'normal_string')
        self.assertIsNone(result['object_nan'])  # 'nan'字符串应该转换为None
        self.assertEqual(result['object_number'], '123')


class TestIntegrationHandleResponse(unittest.TestCase):
    """测试_handle_response的集成场景"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_client = Mock()
        self.mock_client.is_connected = True
        self.mock_client._quote_ctx = Mock()
        self.mock_client._trade_ctx = Mock()
        
        self.trade_manager = TradeManager(self.mock_client)
        self.quote_manager = QuoteManager(self.mock_client)
    
    def test_real_world_market_state_scenario(self):
        """测试真实世界市场状态数据场景"""
        # 模拟富途API返回的市场状态DataFrame
        market_state_df = pd.DataFrame([
            {
                'code': 'HK.00700',
                'stock_name': '腾讯控股',
                'market_state': 'TRADING',
                'stock_state': 'NORMAL',
                'time': '2024-01-15 09:30:00'
            },
            {
                'code': 'HK.00388',
                'stock_name': '香港交易所',
                'market_state': 'TRADING',
                'stock_state': 'NORMAL',
                'time': '2024-01-15 09:30:00'
            }
        ])
        
        result = self.quote_manager._handle_response(ft.RET_OK, market_state_df, "获取市场状态")
        
        # 市场状态应该返回完整的DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['code'], 'HK.00700')
    
    def test_real_world_account_info_scenario(self):
        """测试真实世界账户信息数据场景"""
        # 模拟富途API返回的账户信息DataFrame
        account_info_df = pd.DataFrame([{
            'acc_id': 1234567890,
            'total_assets': 1000000.00,
            'cash': 500000.00,
            'market_value': 500000.00,
            'frozen_cash': 0.00,
            'currency': 'HKD',
            'update_time': '2024-01-15 15:30:00'
        }])
        
        result = self.trade_manager._handle_response(ft.RET_OK, account_info_df, "获取账户信息")
        
        # 单行账户信息应该返回字典
        self.assertIsInstance(result, dict)
        self.assertEqual(result['acc_id'], 1234567890)
        self.assertEqual(result['total_assets'], 1000000.00)
        self.assertEqual(result['currency'], 'HKD')
    
    def test_real_world_position_list_scenario(self):
        """测试真实世界持仓列表数据场景"""
        # 模拟富途API返回的持仓列表DataFrame
        position_list_df = pd.DataFrame([
            {
                'code': 'HK.00700',
                'stock_name': '腾讯控股',
                'qty': 1000,
                'cur_price': 350.0,
                'market_value': 350000.0,
                'cost_price': 300.0,
                'pnl_val': 50000.0,
                'pnl_ratio': 0.1667
            },
            {
                'code': 'HK.00388',
                'stock_name': '香港交易所',
                'qty': 500,
                'cur_price': 280.0,
                'market_value': 140000.0,
                'cost_price': 260.0,
                'pnl_val': 10000.0,
                'pnl_ratio': 0.0769
            }
        ])
        
        result = self.trade_manager._handle_response(ft.RET_OK, position_list_df, "获取持仓列表")
        
        # 多行持仓列表应该返回DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['code'], 'HK.00700')
        self.assertEqual(result.iloc[1]['code'], 'HK.00388')


if __name__ == '__main__':
    unittest.main()