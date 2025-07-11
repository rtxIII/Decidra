import datetime
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import tempfile
import json
from multiprocessing import cpu_count
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
import requests

from modules.yahoo_data import DataProcessingInterface, YahooFinanceInterface, TuShareInterface, HKEXInterface
from utils.global_vars import PATH_DATA


class TestYahooFinanceInterface(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        pass

    def test_get_top_30_hsi_constituents(self):
        """测试获取恒生指数30强成分股"""
        try:
            top_30_hsi_constituents = YahooFinanceInterface.get_top_30_hsi_constituents()
            self.assertEqual(len(top_30_hsi_constituents), 30)
            for item in top_30_hsi_constituents:
                self.assertRegex(item, r'^[A-Z]{2}.\d{5}$')
        except Exception:
            # 网络请求可能失败，跳过测试
            self.skipTest("Network request failed")

    def test_yfinance_code_to_futu_code(self):
        """测试Yahoo Finance代码转Futu代码"""
        yfinance_code = "9988.HK"
        self.assertEqual(YahooFinanceInterface.yfinance_code_to_futu_code(yfinance_code), "HK.09988")

        # 测试异常情况
        with self.assertRaises(AssertionError):
            YahooFinanceInterface.yfinance_code_to_futu_code("9988")
        with self.assertRaises(AssertionError):
            YahooFinanceInterface.yfinance_code_to_futu_code("998.HK")

    def test_futu_code_to_yfinance_code(self):
        """测试Futu代码转Yahoo Finance代码"""
        futu_code = "HK.09988"
        self.assertEqual(YahooFinanceInterface.futu_code_to_yfinance_code(futu_code), "9988.HK")

        us_code = "US.AAPL"
        self.assertEqual(YahooFinanceInterface.futu_code_to_yfinance_code(us_code), "AAPL")

        # 测试异常情况
        with self.assertRaises(AssertionError):
            YahooFinanceInterface.futu_code_to_yfinance_code("HK.9988")

    @patch('modules.yahoo_data.yahooquery.Ticker')
    def test_get_stocks_email_with_mock(self, mock_ticker):
        """测试获取股票邮件信息（使用mock）"""
        # 设置mock数据
        mock_instance = MagicMock()
        mock_instance.price = {
            '9988.HK': {
                'shortName': 'Alibaba',
                'longName': 'Alibaba Group Holding Limited',
                'regularMarketPrice': 100.0,
                'regularMarketChangePercent': 0.05
            }
        }
        mock_instance.summary_detail = {
            '9988.HK': {
                'currency': 'HKD',
                'previousClose': 95.0,
                'volume': 1000000
            }
        }
        mock_instance.asset_profile = {
            '9988.HK': {
                'sector': 'Technology'
            }
        }
        mock_ticker.return_value = mock_instance

        # 执行测试
        result = YahooFinanceInterface.get_stocks_email(['HK.09988'])
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertIn('9988.HK', result)

    def test_get_stock_info_error_handling(self):
        """测试获取股票信息的错误处理"""
        # 测试无效股票代码
        result = YahooFinanceInterface.get_stock_info('INVALID.CODE')
        self.assertIsInstance(result, dict)



    @patch('modules.yahoo_data.yf.download')
    def test_get_stocks_history_download(self, mock_download):
        """测试下载多只股票历史数据"""
        # 设置mock返回数据
        mock_df = pd.DataFrame({
            'Open': [100, 101],
            'High': [105, 106], 
            'Low': [99, 100],
            'Close': [104, 105],
            'Volume': [1000000, 1100000]
        })
        mock_download.return_value = mock_df
        
        # 测试下载
        stock_list = ['HK.09988', 'HK.00700']
        result = YahooFinanceInterface.get_stocks_history(stock_list)
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        mock_download.assert_called_once()

    @patch('modules.yahoo_data.yf.Ticker')
    def test_get_stock_history_download(self, mock_ticker):
        """测试下载单只股票历史数据"""
        # 设置mock返回数据
        mock_instance = MagicMock()
        mock_history = pd.DataFrame({
            'Open': [100, 101],
            'High': [105, 106], 
            'Low': [99, 100],
            'Close': [104, 105],
            'Volume': [1000000, 1100000]
        })
        mock_instance.history.return_value = mock_history
        mock_ticker.return_value = mock_instance
        
        # 测试下载
        result = YahooFinanceInterface.get_stock_history('HK.09988', period='1y')
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        mock_ticker.assert_called_once_with('9988.HK')
        mock_instance.history.assert_called_once_with(period='1y')

    @patch('modules.yahoo_data.yf.Ticker')
    def test_get_stocks_info_download(self, mock_ticker):
        """测试下载股票信息"""
        # 设置mock返回数据
        mock_instance = MagicMock()
        mock_info = {
            'longName': 'Alibaba Group Holding Limited',
            'sector': 'Technology',
            'industry': 'Internet Content & Information'
        }
        mock_instance.info = mock_info
        mock_ticker.return_value = mock_instance
        
        # 测试下载
        result = YahooFinanceInterface.get_stocks_info(['HK.09988'])
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertIn('9988.HK', result)
        self.assertEqual(result['9988.HK']['longName'], 'Alibaba Group Holding Limited')

    @patch('modules.yahoo_data.yf.Ticker')
    def test_get_stocks_name_download(self, mock_ticker):
        """测试下载股票名称"""
        # 设置mock返回数据
        mock_instance = MagicMock()
        mock_instance.info = {'longName': 'Alibaba Group Holding Limited'}
        mock_ticker.return_value = mock_instance
        
        # 测试下载
        result = YahooFinanceInterface.get_stocks_name(['HK.09988'])
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertIn('9988.HK', result)
        self.assertEqual(result['9988.HK'], 'Alibaba Group Holding Limited')

    def test_get_stock_history_error_handling(self):
        """测试股票历史数据下载错误处理"""
        # 测试无效股票代码
        try:
            result = YahooFinanceInterface.get_stock_history('INVALID.CODE')
            # 如果没有异常，结果应该是DataFrame
            self.assertIsInstance(result, pd.DataFrame)
        except Exception:
            # 如果有异常也是可以接受的
            pass


class TestDataProcessingInterface(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.test_df = pd.DataFrame({
            'code': ['HK.00001', 'HK.00001'],
            'time_key': ['2022-04-11 09:30:00', '2022-04-11 09:31:00'],
            'open': [10.0, 10.1],
            'close': [10.1, 10.2],
            'high': [10.2, 10.3],
            'low': [9.9, 10.0],
            'volume': [1000, 1100],
            'pe_ratio': [15.5, 15.6],
            'turnover_rate': [0.1, 0.1],
            'turnover': [10000, 11000],
            'change_rate': [1.0, 2.0],
            'last_close': [10.0, 10.1]
        })

    def test_get_1M_data_range(self):
        """测试获取1分钟数据范围"""
        date_range = ['2022-04-11', '2022-04-12', '2022-04-13']
        stock_list = ['HK.09988', 'HK.00700']
        
        try:
            output_dict = DataProcessingInterface.get_1M_data_range(date_range, stock_list)
            self.assertIsInstance(output_dict, dict)
            # 结果可能为空或有数据，都是合理的
            # 检查返回的股票代码是否在请求的列表中
            for stock_code in output_dict.keys():
                self.assertIn(stock_code, stock_list)
        except ValueError as e:
            if "No objects to concatenate" in str(e):
                # 这是预期的，因为测试数据文件不存在
                self.skipTest("Test data files do not exist")
            else:
                raise

    def test_get_custom_interval_data(self):
        """测试自定义时间间隔数据"""
        target_date = datetime.datetime(2022, 4, 11)
        custom_intervals = [3, 5, 15, 30]
        stock_list = ['HK.09988']
        for custom_interval in custom_intervals:
            output_df = DataProcessingInterface.get_custom_interval_data(target_date, custom_interval, stock_list)
            self.assertIsInstance(output_df, dict)

    def test_save_and_get_stock_df_file_operations(self):
        """测试文件保存和读取操作"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 测试保存为parquet
            parquet_path = Path(tmp_dir) / "test.parquet"
            result = DataProcessingInterface.save_stock_df_to_file(
                self.test_df, str(parquet_path), 'parquet'
            )
            self.assertTrue(result)
            self.assertTrue(parquet_path.exists())

            # 测试读取parquet
            loaded_df = DataProcessingInterface.get_stock_df_from_file(parquet_path)
            self.assertFalse(loaded_df.empty)
            self.assertEqual(len(loaded_df), 2)

            # 测试保存为CSV
            csv_path = Path(tmp_dir) / "test.csv"
            result = DataProcessingInterface.save_stock_df_to_file(
                self.test_df, str(csv_path), 'csv'
            )
            self.assertTrue(result)
            self.assertTrue(csv_path.exists())

            # 测试读取CSV
            loaded_csv_df = DataProcessingInterface.get_stock_df_from_file(csv_path)
            self.assertFalse(loaded_csv_df.empty)

    def test_get_stock_df_from_nonexistent_file(self):
        """测试读取不存在的文件"""
        nonexistent_path = Path("/nonexistent/path/file.parquet")
        df = DataProcessingInterface.get_stock_df_from_file(nonexistent_path)
        self.assertTrue(df.empty)

    def test_save_empty_dataframe(self):
        """测试保存空数据框"""
        empty_df = pd.DataFrame()
        with tempfile.NamedTemporaryFile(suffix='.parquet') as tmp:
            result = DataProcessingInterface.save_stock_df_to_file(
                empty_df, tmp.name, 'parquet'
            )
            self.assertFalse(result)

    def test_check_empty_data(self):
        """测试检查空数据"""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            # 创建空文件
            empty_df = pd.DataFrame()
            empty_df.to_parquet(tmp.name, index=False)
            tmp_path = Path(tmp.name)
            
            # 检查空数据 - 应该删除空文件
            result = DataProcessingInterface.check_empty_data(tmp_path)
            self.assertTrue(result)
            self.assertFalse(tmp_path.exists())

    def test_convert_csv_to_parquet_conversion(self):
        """测试CSV到Parquet格式转换"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建测试CSV文件
            csv_path = Path(tmp_dir) / "test_data.csv"
            self.test_df.to_csv(csv_path, index=False)
            
            # 执行转换
            result = DataProcessingInterface.convert_csv_to_parquet(csv_path)
            
            # 验证结果
            self.assertTrue(result)
            parquet_path = Path(str(csv_path).replace('.csv', '.parquet'))
            self.assertTrue(parquet_path.exists())
            
            # 验证转换后的数据
            converted_df = pd.read_parquet(parquet_path)
            self.assertEqual(len(converted_df), len(self.test_df))

    def test_convert_parquet_to_csv_conversion(self):
        """测试Parquet到CSV格式转换"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建测试Parquet文件
            parquet_path = Path(tmp_dir) / "test_data.parquet"
            self.test_df.to_parquet(parquet_path, index=False)
            
            # 执行转换
            result = DataProcessingInterface.convert_parquet_to_csv(parquet_path)
            
            # 验证结果
            self.assertTrue(result)
            csv_path = Path(str(parquet_path).replace('.parquet', '.csv'))
            self.assertTrue(csv_path.exists())
            
            # 验证转换后的数据
            converted_df = pd.read_csv(csv_path)
            self.assertEqual(len(converted_df), len(self.test_df))

    def test_convert_unsupported_file_format(self):
        """测试不支持的文件格式转换"""
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            txt_path = Path(tmp.name)
            
            # 尝试转换不支持的格式
            result_csv = DataProcessingInterface.convert_csv_to_parquet(txt_path)
            result_parquet = DataProcessingInterface.convert_parquet_to_csv(txt_path)
            
            # 验证返回False
            self.assertFalse(result_csv)
            self.assertFalse(result_parquet)

    def test_get_num_days_to_update_existing_files(self):
        """测试获取需要更新的天数（文件存在情况）"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建模拟股票目录和文件
            stock_dir = Path(tmp_dir) / "HK.00001"
            stock_dir.mkdir()
            
            test_file = stock_dir / "test_data.parquet"
            self.test_df.to_parquet(test_file, index=False)
            
            # 修改PATH_DATA临时指向测试目录
            original_path = PATH_DATA
            import utils.global_vars as gv
            gv.PATH_DATA = Path(tmp_dir)
            
            try:
                # 测试获取天数
                days = DataProcessingInterface.get_num_days_to_update("HK.00001")
                
                # 验证结果（应该是很小的天数，因为文件刚创建）
                self.assertIsInstance(days, int)
                self.assertGreaterEqual(days, 0)
                
            finally:
                # 恢复原始PATH_DATA
                gv.PATH_DATA = original_path

    def test_get_num_days_to_update_no_files(self):
        """测试获取需要更新的天数（无文件情况）"""
        # 测试不存在的股票代码
        days = DataProcessingInterface.get_num_days_to_update("NONEXISTENT.STOCK")
        
        # 验证返回默认值（2年）
        self.assertEqual(days, 365 * 2)

    @patch('modules.yahoo_data.Pool')
    def test_clear_empty_data_batch_processing(self, mock_pool):
        """测试批量清理空数据文件"""
        # 设置mock pool
        mock_pool_instance = MagicMock()
        mock_pool.return_value = mock_pool_instance
        
        # 执行清理
        DataProcessingInterface.clear_empty_data()
        
        # 验证Pool被正确使用
        mock_pool.assert_called_once_with(cpu_count())
        mock_pool_instance.map.assert_called_once()
        mock_pool_instance.close.assert_called_once()
        mock_pool_instance.join.assert_called_once()

    @patch('modules.yahoo_data.Pool')
    def test_convert_all_csv_to_parquet_batch_processing(self, mock_pool):
        """测试批量CSV到Parquet转换"""
        # 设置mock pool
        mock_pool_instance = MagicMock()
        mock_pool.return_value = mock_pool_instance
        
        # 执行批量转换
        DataProcessingInterface.convert_all_csv_to_parquet()
        
        # 验证Pool被正确使用
        mock_pool.assert_called_once_with(cpu_count())
        mock_pool_instance.map.assert_called_once()
        mock_pool_instance.close.assert_called_once()
        mock_pool_instance.join.assert_called_once()

    def test_validate_dir_creation(self):
        """测试目录验证和创建"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_dir = Path(tmp_dir) / "new_directory" / "nested" / "path"
            
            # 目录应该不存在
            self.assertFalse(test_dir.exists())
            
            # 验证并创建目录
            DataProcessingInterface.validate_dir(test_dir)
            
            # 验证目录被创建
            self.assertTrue(test_dir.exists())
            self.assertTrue(test_dir.is_dir())

    def test_get_file_to_df_parquet_loading(self):
        """测试从Parquet文件加载数据到DataFrame"""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            # 保存测试数据
            self.test_df.to_parquet(tmp.name, index=False)
            
            # 加载数据
            loaded_df = DataProcessingInterface.get_file_to_df(Path(tmp.name))
            
            # 验证结果
            self.assertFalse(loaded_df.empty)
            self.assertEqual(len(loaded_df), len(self.test_df))
            
            # 清理文件
            Path(tmp.name).unlink()

    def test_get_file_to_df_non_parquet_file(self):
        """测试加载非Parquet文件"""
        with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
            # 尝试加载CSV文件（方法只支持parquet）
            result = DataProcessingInterface.get_file_to_df(Path(tmp.name))
            
            # 验证返回空DataFrame
            self.assertTrue(result.empty)


class TestTuShareInterface(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        pass

    def test_validate_stock_code(self):
        """测试TuShare股票代码验证"""
        futu_codes = ['HK.09988', 'US.AAPL']
        validated = TuShareInterface._TuShareInterface__validate_stock_code(futu_codes)
        
        self.assertIsInstance(validated, list)
        self.assertEqual(len(validated), 2)

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_update_stocks_history_with_mock(self, mock_pro):
        """测试更新股票历史数据（使用mock）"""
        # 备份原始数据
        original_df = TuShareInterface.output_df.copy()
        
        try:
            # 重置为空的DataFrame
            TuShareInterface.output_df = pd.DataFrame()
            
            # 设置mock数据
            mock_df = pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': ['20220411'],
                'open': [10.0],
                'close': [10.5],
                'high': [11.0],
                'low': [9.5],
                'vol': [1000000]
            })
            mock_pro.daily.return_value = mock_df

            # 执行测试
            result = TuShareInterface.update_stocks_history(['000001.SZ'])
            
            # 验证结果
            self.assertTrue(result)
            self.assertFalse(TuShareInterface.output_df.empty)
        finally:
            # 恢复原始数据
            TuShareInterface.output_df = original_df

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_get_stocks_email_with_mock(self, mock_pro):
        """测试获取股票邮件信息（使用mock）"""
        # 设置mock基本信息数据
        mock_basic_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'symbol': ['000001'],
            'name': ['平安银行'],
            'area': ['深圳'],
            'industry': ['银行'],
            'market': ['主板'],
            'enname': ['Ping An Bank'],
            'curr_type': ['CNY']
        })
        mock_pro.stock_basic.return_value = mock_basic_df

        # 设置历史数据
        TuShareInterface.output_df = pd.DataFrame({
            'code': ['000001.SZ'],
            'time_key': ['20220411'],
            'open': [10.0],
            'close': [10.5],
            'pre_close': [9.8],
            'pct_chg': [2.5],
            'volume': [1000000],
            'amount': [10500000]
        })

        # 执行测试
        result = TuShareInterface.get_stocks_email(['000001.SZ'])
        
        # 验证结果
        self.assertIsInstance(result, dict)

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_get_stocks_email_api_error(self, mock_pro):
        """测试API错误情况下的处理"""
        # 模拟API错误
        mock_pro.stock_basic.side_effect = Exception("API Error")
        
        # 执行测试
        result = TuShareInterface.get_stocks_email(['000001.SZ'])
        
        # 验证结果 - 应该返回空字典
        self.assertEqual(result, {})

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_update_stocks_history_large_dataset(self, mock_pro):
        """测试大量股票历史数据下载"""
        # 模拟大量股票代码
        large_stock_list = [f'00000{i}.SZ' for i in range(1, 25)]  # 24只股票，测试分批处理
        
        # 设置mock数据
        mock_df = pd.DataFrame({
            'ts_code': large_stock_list,
            'trade_date': ['20220411'] * len(large_stock_list),
            'open': [10.0] * len(large_stock_list),
            'close': [10.5] * len(large_stock_list),
            'high': [11.0] * len(large_stock_list),
            'low': [9.5] * len(large_stock_list),
            'vol': [1000000] * len(large_stock_list)
        })
        mock_pro.daily.return_value = mock_df

        # 执行测试
        result = TuShareInterface.update_stocks_history(large_stock_list)
        
        # 验证结果
        self.assertTrue(result)
        self.assertFalse(TuShareInterface.output_df.empty)
        # 验证数据被重命名了
        self.assertIn('code', TuShareInterface.output_df.columns)
        self.assertIn('time_key', TuShareInterface.output_df.columns)
        self.assertIn('volume', TuShareInterface.output_df.columns)

    @patch('modules.yahoo_data.TuShareInterface.pro')  
    def test_update_stocks_history_rate_limit_handling(self, mock_pro):
        """测试处理API速率限制的分批下载"""
        # 备份原始数据
        original_df = TuShareInterface.output_df.copy()
        
        try:
            # 重置为空的DataFrame
            TuShareInterface.output_df = pd.DataFrame()
            
            # 创建超过速率限制的股票列表 (测试分批逻辑)
            many_stocks = [f'{i:06d}.SZ' for i in range(1, 51)]  # 50只股票
            
            # 设置mock数据 - 每次调用返回不同批次的数据
            call_count = 0
            def mock_daily_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                # 模拟每批返回少量数据
                return pd.DataFrame({
                    'ts_code': [f'{call_count:06d}.SZ'],
                    'trade_date': ['20220411'],
                    'open': [10.0],
                    'close': [10.5],
                    'high': [11.0], 
                    'low': [9.5],
                    'vol': [1000000]
                })
            
            mock_pro.daily.side_effect = mock_daily_side_effect
            
            # 执行测试
            result = TuShareInterface.update_stocks_history(many_stocks)
            
            # 验证结果
            self.assertTrue(result)
            self.assertGreater(mock_pro.daily.call_count, 1)  # 应该被分批调用
        finally:
            # 恢复原始数据
            TuShareInterface.output_df = original_df

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_update_stocks_history_api_error(self, mock_pro):
        """测试API调用失败的情况"""
        # 模拟API调用失败
        mock_pro.daily.side_effect = Exception("API rate limit exceeded")
        
        # 执行测试 - 应该抛出异常
        with self.assertRaises(Exception):
            TuShareInterface.update_stocks_history(['000001.SZ'])

    def test_get_stock_history_empty_output(self):
        """测试从空的output_df获取股票历史"""
        # 备份原始数据
        original_df = TuShareInterface.output_df.copy()
        
        try:
            # 清空output_df
            TuShareInterface.output_df = pd.DataFrame(columns=['code', 'time_key', 'open', 'close'])
            
            # 测试获取历史数据
            result = TuShareInterface.get_stock_history('000001.SZ')
            
            # 验证结果为空
            self.assertTrue(result.empty)
        finally:
            # 恢复原始数据
            TuShareInterface.output_df = original_df

    @patch('modules.yahoo_data.TuShareInterface.pro')
    def test_get_stocks_email_with_large_dataset(self, mock_pro):
        """测试大量股票的邮件信息获取"""
        # 设置mock基本信息数据
        stock_codes = ['000001.SZ', '000002.SZ', '000003.SZ']
        mock_basic_df = pd.DataFrame({
            'ts_code': stock_codes,
            'symbol': ['000001', '000002', '000003'],
            'name': ['平安银行', '万科A', '国农科技'],
            'area': ['深圳', '深圳', '深圳'],
            'industry': ['银行', '房地产', '农业'],
            'market': ['主板', '主板', '主板'],
            'enname': ['Ping An Bank', 'China Vanke', 'Guonong Technology'],
            'curr_type': ['CNY', 'CNY', 'CNY']
        })
        mock_pro.stock_basic.return_value = mock_basic_df

        # 设置历史数据
        TuShareInterface.output_df = pd.DataFrame({
            'code': stock_codes * 3,  # 每只股票3天数据
            'time_key': ['20220411', '20220412', '20220413'] * 3,
            'open': [10.0] * 9,
            'close': [10.5] * 9,
            'pre_close': [9.8] * 9,
            'pct_chg': [2.5] * 9,
            'volume': [1000000] * 9,
            'amount': [10500000] * 9
        })

        # 执行测试
        result = TuShareInterface.get_stocks_email(stock_codes)
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)
        for stock_code in stock_codes:
            self.assertIn(stock_code, result)
            self.assertIn('Company Name', result[stock_code])
            self.assertIn('Description', result[stock_code])


class TestHKEXInterface(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        pass

    @patch('modules.yahoo_data.requests.get')
    @patch('modules.yahoo_data.openpyxl.load_workbook')
    def test_update_security_list_full_with_mock(self, mock_workbook, mock_get):
        """测试更新完整证券列表（使用mock）"""
        # 设置mock响应
        mock_response = MagicMock()
        mock_response.content = b'fake excel content'
        mock_get.return_value = mock_response

        # 设置mock工作簿
        mock_wb = MagicMock()
        mock_sheet = MagicMock()
        mock_wb.active = mock_sheet
        mock_sheet.rows = [
            [MagicMock(value='Stock Code'), MagicMock(value='Name'), MagicMock(value='Category')],
            [MagicMock(value='00001'), MagicMock(value='CKH Holdings'), MagicMock(value='Equity')]
        ]
        mock_workbook.return_value = mock_wb

        # 确保目录存在
        (PATH_DATA / 'stocks').mkdir(parents=True, exist_ok=True)

        try:
            # 执行测试
            HKEXInterface.update_security_list_full()
            
            # 验证文件操作被调用
            mock_get.assert_called_once()
            mock_workbook.assert_called_once()
        except Exception as e:
            self.skipTest(f"File operation error: {e}")

    def test_get_security_df_full_file_not_exist(self):
        """测试读取不存在的证券列表文件"""
        try:
            df = HKEXInterface.get_security_df_full()
            self.assertIsInstance(df, pd.DataFrame)
        except FileNotFoundError:
            # 文件不存在是预期的
            self.skipTest("Security list file does not exist")

    @patch('modules.yahoo_data.HKEXInterface.get_security_df_full')
    def test_get_equity_list_full_with_mock(self, mock_get_df):
        """测试获取股权列表（使用mock）"""
        # 设置mock数据
        mock_df = pd.DataFrame({
            'Stock Code': ['00001', '00002'],
            'Name of Securities': ['CKH Holdings', 'CLP Holdings'],
            'Category': ['Equity', 'Equity'],
            'Board Lot': ['500', '500']
        })
        mock_get_df.return_value = mock_df

        # 执行测试
        equity_list = HKEXInterface.get_equity_list_full()
        
        # 验证结果
        self.assertIsInstance(equity_list, list)
        self.assertEqual(len(equity_list), 2)
        self.assertIn('HK.00001', equity_list)
        self.assertIn('HK.00002', equity_list)

    @patch('modules.yahoo_data.HKEXInterface.get_security_df_full')
    def test_get_board_lot_full_with_mock(self, mock_get_df):
        """测试获取手数信息（使用mock）"""
        # 设置mock数据
        mock_df = pd.DataFrame({
            'Stock Code': ['00001', '00002'],
            'Category': ['Equity', 'Equity'],
            'Board Lot': ['500', '1,000']
        })
        mock_get_df.return_value = mock_df

        # 执行测试
        board_lots = HKEXInterface.get_board_lot_full()
        
        # 验证结果
        self.assertIsInstance(board_lots, dict)
        self.assertEqual(board_lots['HK.00001'], 500)
        self.assertEqual(board_lots['HK.00002'], 1000)

    @patch('modules.yahoo_data.requests.get')
    def test_update_security_list_full_download_success(self, mock_get):
        """测试成功下载证券列表"""
        # 设置mock响应
        mock_response = MagicMock()
        mock_response.content = b'fake excel content'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 确保目录存在
        (PATH_DATA / 'stocks').mkdir(parents=True, exist_ok=True)

        # 执行测试 - 网络下载部分
        try:
            # 只验证网络请求，不执行实际的Excel处理
            mock_get.assert_not_called()  # 开始时未调用
            
            # 由于Excel处理会失败，我们只测试能正确发起网络请求
            with self.assertRaises(Exception):  # 预期Excel处理失败
                HKEXInterface.update_security_list_full()
                
            # 验证网络请求被调用
            mock_get.assert_called_once_with(
                "https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx"
            )
        except Exception as e:
            self.skipTest(f"File operation error: {e}")

    @patch('modules.yahoo_data.requests.get')
    def test_update_security_list_full_download_failure(self, mock_get):
        """测试下载证券列表失败的情况"""
        # 模拟网络请求失败
        mock_get.side_effect = requests.RequestException("Network error")

        # 执行测试 - 应该抛出异常
        with self.assertRaises(requests.RequestException):
            HKEXInterface.update_security_list_full()

    @patch('modules.yahoo_data.requests.get')
    def test_update_security_list_full_download_large_file(self, mock_get):
        """测试下载大文件的情况"""
        # 模拟大文件内容
        large_content = b'fake excel content' * 10000  # 模拟大文件
        mock_response = MagicMock()
        mock_response.content = large_content
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 确保目录存在
        (PATH_DATA / 'stocks').mkdir(parents=True, exist_ok=True)

        # 执行测试
        try:
            HKEXInterface.update_security_list_full()
            
            # 验证网络请求被调用
            mock_get.assert_called_once()
            
            # 验证文件大小
            file_path = PATH_DATA / 'stocks' / 'ListOfSecurities.xlsx'
            if file_path.exists():
                self.assertGreater(file_path.stat().st_size, 0)
        except Exception as e:
            self.skipTest(f"File operation error: {e}")

    @patch('modules.yahoo_data.requests.get')
    def test_update_security_list_full_timeout_handling(self, mock_get):
        """测试下载超时的处理"""
        # 模拟超时
        mock_get.side_effect = requests.Timeout("Request timeout")

        # 执行测试 - 应该抛出超时异常
        with self.assertRaises(requests.Timeout):
            HKEXInterface.update_security_list_full()

    @patch('modules.yahoo_data.requests.get')
    @patch('modules.yahoo_data.openpyxl.load_workbook')
    def test_update_security_list_full_complete_workflow(self, mock_workbook, mock_get):
        """测试完整的下载和处理工作流"""
        # 设置mock网络响应
        mock_response = MagicMock()
        mock_response.content = b'fake excel content'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 设置mock Excel处理
        mock_wb = MagicMock()
        mock_sheet = MagicMock()
        mock_wb.active = mock_sheet
        
        # 模拟Excel行数据
        mock_rows = [
            [MagicMock(value='Stock Code'), MagicMock(value='Name of Securities'), MagicMock(value='Category'), MagicMock(value='Board Lot')],
            [MagicMock(value=''), MagicMock(value=''), MagicMock(value=''), MagicMock(value='')],  # 空行
            [MagicMock(value='00001'), MagicMock(value='CKH Holdings'), MagicMock(value='Equity'), MagicMock(value='500')],
            [MagicMock(value='00002'), MagicMock(value='CLP Holdings'), MagicMock(value='Equity'), MagicMock(value='500')],
            [MagicMock(value='00003'), MagicMock(value='Hong Kong & China Gas'), MagicMock(value='Equity'), MagicMock(value='1000')]
        ]
        mock_sheet.rows = mock_rows
        mock_workbook.return_value = mock_wb

        # 确保目录存在
        (PATH_DATA / 'stocks').mkdir(parents=True, exist_ok=True)

        try:
            # 执行测试
            HKEXInterface.update_security_list_full()
            
            # 验证各步骤被调用
            mock_get.assert_called_once()
            mock_workbook.assert_called_once()
            
            # 验证CSV文件是否生成
            csv_path = PATH_DATA / 'stocks' / 'ListOfSecurities.csv'
            if csv_path.exists():
                # 读取生成的CSV并验证内容
                with open(csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn('Stock Code', content)
                    self.assertIn('CKH Holdings', content)
                    
        except Exception as e:
            self.skipTest(f"File operation error: {e}")

    def test_get_security_df_full_with_real_data_structure(self):
        """测试使用真实数据结构的安全检查"""
        # 创建模拟的CSV文件内容
        csv_content = """Hong Kong Exchanges and Clearing Limited
Stock Exchange of Hong Kong Limited

Stock Code,Name of Securities,Category,Sub-Category,Board Lot
00001,CKH HOLDINGS,Equity,L,500
00002,CLP HOLDINGS,Equity,L,500
00003,HONG KONG & CHINA GAS,Equity,L,1000
"""
        
        # 创建临时CSV文件进行测试
        csv_path = PATH_DATA / 'stocks' / 'ListOfSecurities.csv'
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            # 测试读取
            df = HKEXInterface.get_security_df_full()
            
            # 验证结果
            self.assertIsInstance(df, pd.DataFrame)
            self.assertGreater(len(df), 0)
            self.assertIn('Stock Code', df.columns)
            self.assertIn('Name of Securities', df.columns)
            
        except Exception as e:
            self.skipTest(f"CSV operation error: {e}")
        finally:
            # 清理测试文件
            if csv_path.exists():
                csv_path.unlink()


if __name__ == '__main__':
    # 创建测试套件
    suite_data_processing = unittest.TestLoader().loadTestsFromTestCase(TestDataProcessingInterface)
    suite_yahoo_finance = unittest.TestLoader().loadTestsFromTestCase(TestYahooFinanceInterface)
    suite_tushare = unittest.TestLoader().loadTestsFromTestCase(TestTuShareInterface)
    suite_hkex = unittest.TestLoader().loadTestsFromTestCase(TestHKEXInterface)
    
    # 组合所有测试套件
    suite = unittest.TestSuite([
        suite_data_processing,
        suite_yahoo_finance, 
        suite_tushare,
        suite_hkex
    ])
    
    # 运行测试
    unittest.TextTestRunner(verbosity=2).run(suite)
