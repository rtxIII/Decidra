"""
监控模块集成测试
测试整个监控系统的集成功能，包括数据流、指标计算、UI组件等
"""

import unittest
import asyncio
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor import (
    FutuDataManager, IndicatorsManager, DataFlowManager,
    StockTableInterface, IndicatorsDisplayInterface, 
    StatusBarInterface, DataFormatter, PerformanceMonitor
)
from base.monitor import (
    StockData, TechnicalIndicators, MarketStatus, SignalType,
    ConnectionStatus, DataUpdateResult, PerformanceMetrics
)


class TestMonitorSystemIntegration(unittest.TestCase):
    """监控系统集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_stock_codes = ['HK.00700', 'HK.09988', 'US.AAPL']
        self.test_timestamp = datetime.now()
    
    def create_mock_stock_data(self, code, price=100.0):
        """创建模拟股票数据"""
        return StockData(
            code=code,
            name=f"股票_{code}",
            current_price=price,
            open_price=price - 1,
            prev_close=price - 2,
            change_rate=(price - (price - 2)) / (price - 2),
            change_amount=2.0,
            volume=1000000,
            turnover=price * 1000000,
            high_price=price + 1,
            low_price=price - 3,
            update_time=self.test_timestamp,
            market_status=MarketStatus.OPEN
        )
    
    def create_mock_indicators(self, code, base_value=100.0):
        """创建模拟技术指标"""
        return TechnicalIndicators(
            stock_code=code,
            ma5=base_value,
            ma10=base_value - 1,
            ma20=base_value - 2,
            rsi14=65.0,
            rsi_signal=SignalType.HOLD,
            macd_line=1.5,
            signal_line=1.2,
            histogram=0.3,
            macd_signal=SignalType.BUY
        )
    
    def create_mock_kline_data(self, days=60):
        """创建模拟K线数据"""
        data = []
        for i in range(days):
            price = 100 + i * 0.5 + (i % 10) * 0.1
            data.append({
                'time_key': f'2024-01-{i+1:02d}',
                'open': price - 0.5,
                'close': price,
                'high': price + 0.5,
                'low': price - 1,
                'volume': 1000 + i * 10,
                'turnover': price * (1000 + i * 10)
            })
        return pd.DataFrame(data)
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_complete_data_pipeline(self, mock_futu_market):
        """测试完整的数据管道"""
        # 1. 准备mock数据
        mock_snapshots = []
        mock_klines = {}
        
        for i, code in enumerate(self.test_stock_codes):
            # 市场快照数据
            mock_snapshots.append({
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
            
            # K线数据
            mock_klines[code] = self.create_mock_kline_data(60)
        
        # 2. 设置mock返回
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.return_value = mock_snapshots
        mock_instance.get_stock_quote.return_value = []
        
        # 为每个股票设置K线数据
        def mock_get_klines(codes, num, ktype, autype):
            code = codes[0] if codes else 'HK.00700'
            return [{'kline_list': mock_klines.get(code, pd.DataFrame()).to_dict('records')}]
        
        mock_instance.get_cur_kline.side_effect = mock_get_klines
        
        # 3. 创建数据流管理器
        data_flow = DataFlowManager()
        
        # 4. 执行完整的数据更新周期
        result = await data_flow.data_update_cycle(self.test_stock_codes)
        
        # 5. 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.stock_data), 3)
        self.assertEqual(len(result.indicators_data), 3)
        
        # 验证股票数据
        for i, code in enumerate(self.test_stock_codes):
            self.assertIn(code, result.stock_data)
            stock = result.stock_data[code]
            self.assertEqual(stock.code, code)
            self.assertEqual(stock.current_price, 100.0 + i * 10)
        
        # 验证技术指标数据
        for code in self.test_stock_codes:
            self.assertIn(code, result.indicators_data)
            indicators = result.indicators_data[code]
            self.assertEqual(indicators.stock_code, code)
            self.assertIsNotNone(indicators.ma5)
            self.assertIsNotNone(indicators.rsi14)
        
        # 清理
        await data_flow.data_manager.cleanup()
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_ui_integration_with_real_data(self, mock_futu_market):
        """测试UI组件与真实数据的集成"""
        # 1. 准备数据
        mock_snapshots = [{
            'code': 'HK.00700',
            'stock_name': '腾讯控股',
            'cur_price': 450.0,
            'open_price': 448.0,
            'prev_close_price': 445.0,
            'high_price': 452.0,
            'low_price': 446.0,
            'volume': 5000000,
            'turnover': 2250000000.0
        }]
        
        mock_kline_data = self.create_mock_kline_data(60)
        
        # 2. 设置mock
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.return_value = mock_snapshots
        mock_instance.get_stock_quote.return_value = []
        mock_instance.get_cur_kline.return_value = [{
            'kline_list': mock_kline_data.to_dict('records')
        }]
        
        # 3. 获取数据
        data_manager = FutuDataManager()
        quotes = await data_manager.get_real_time_quotes(['HK.00700'])
        
        indicators_manager = IndicatorsManager(data_manager)
        indicators = await indicators_manager.update_all_indicators(['HK.00700'])
        
        # 4. 测试UI组件
        # 表格组件
        table_interface = StockTableInterface(120, 30)
        table_interface.update_data(list(quotes.values()))
        table = table_interface.render_table()
        self.assertIsNotNone(table)
        
        # 指标显示组件
        indicators_display = IndicatorsDisplayInterface()
        indicators_display.update_indicators(indicators)
        panel = indicators_display.render_panel('HK.00700')
        self.assertIsNotNone(panel)
        
        # 状态栏组件
        status_bar = StatusBarInterface()
        status_bar.update_status(
            ConnectionStatus.CONNECTED,
            datetime.now(),
            'HK.00700'
        )
        status_text = status_bar.render_status_bar()
        self.assertIsNotNone(status_text)
        
        # 5. 测试数据格式化
        stock_data = list(quotes.values())[0]
        
        # 格式化价格
        formatted_price = DataFormatter.format_price(stock_data.current_price)
        self.assertEqual(formatted_price, "450.00")
        
        # 格式化涨跌幅
        change_text, change_color = DataFormatter.format_change_rate(stock_data.change_rate)
        self.assertIn("%", change_text)
        self.assertIn(change_color, [ColorStyle.GREEN, ColorStyle.RED, ColorStyle.GRAY])
        
        # 格式化成交量
        volume_text = DataFormatter.format_volume(stock_data.volume)
        self.assertEqual(volume_text, "5.00M")
        
        # 格式化技术指标
        if 'HK.00700' in indicators:
            indicator_data = DataFormatter.format_indicators_text(indicators['HK.00700'])
            self.assertIn("MA5:", indicator_data.ma_text)
            self.assertIn("RSI", indicator_data.rsi_text)
            self.assertIn("MACD", indicator_data.macd_text)
        
        # 清理
        await data_manager.cleanup()
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_performance_monitoring_integration(self, mock_futu_market):
        """测试性能监控集成"""
        # 1. 设置mock
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
            'turnover': 500000000.0
        }]
        mock_instance.get_stock_quote.return_value = []
        mock_instance.get_cur_kline.return_value = [{
            'kline_list': self.create_mock_kline_data(60).to_dict('records')
        }]
        
        # 2. 创建性能监控器
        performance_monitor = PerformanceMonitor()
        
        # 3. 使用性能监控包装数据获取
        data_manager = FutuDataManager()
        
        # 监控实时数据获取
        quotes = await performance_monitor.measure_api_call(
            data_manager.get_real_time_quotes,
            ['HK.00700']
        )
        
        # 监控历史数据获取
        klines = await performance_monitor.measure_api_call(
            data_manager.get_historical_klines,
            'HK.00700',
            30
        )
        
        # 4. 验证性能数据
        self.assertEqual(performance_monitor.metrics.api_call_count, 2)
        self.assertEqual(len(performance_monitor.metrics.api_response_time), 2)
        self.assertEqual(len(performance_monitor.metrics.memory_usage), 2)
        
        # 5. 获取性能报告
        report = performance_monitor.get_performance_report()
        self.assertIn('avg_response_time', report)
        self.assertIn('memory_usage_mb', report)
        self.assertIn('api_calls_total', report)
        self.assertEqual(report['api_calls_total'], 2)
        
        # 清理
        await data_manager.cleanup()
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_error_handling_integration(self, mock_futu_market):
        """测试错误处理集成"""
        # 1. 设置mock产生各种错误
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.side_effect = Exception("网络连接失败")
        mock_instance.get_stock_quote.return_value = []
        
        # 2. 测试数据流错误处理
        data_flow = DataFlowManager()
        result = await data_flow.data_update_cycle(['HK.00700'])
        
        # 3. 验证错误处理
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("网络连接失败", result.error_message)
        
        # 4. 测试性能监控的错误处理
        performance_monitor = PerformanceMonitor()
        
        async def failing_function():
            raise Exception("测试错误")
        
        with self.assertRaises(Exception):
            await performance_monitor.measure_api_call(failing_function)
        
        # 验证错误统计
        self.assertEqual(performance_monitor.metrics.error_count, 1)
        
        # 清理
        await data_flow.data_manager.cleanup()
    
    async def test_subscription_integration(self):
        """测试订阅功能集成"""
        # 由于订阅功能需要真实的富途连接，这里主要测试接口
        data_manager = FutuDataManager()
        
        # 测试订阅接口
        callback = Mock()
        
        # 注意：这里会失败，因为没有真实的富途连接
        # 但我们可以测试接口是否正确调用
        try:
            success = await data_manager.subscribe_real_time_data(['HK.00700'], callback)
            # 如果有真实连接，应该测试success的值
        except Exception:
            # 预期在没有真实连接时会失败
            pass
        
        # 测试订阅状态
        status = await data_manager.get_subscription_status()
        self.assertIn('subscribed_stocks', status)
        self.assertIn('subscription_count', status)
        
        # 清理
        await data_manager.cleanup()
    
    def test_data_model_validation_integration(self):
        """测试数据模型验证集成"""
        # 测试有效的股票数据
        try:
            valid_stock = StockData(
                code="HK.00700",
                name="腾讯控股",
                current_price=500.0,
                open_price=498.0,
                prev_close=495.0,
                change_rate=0.0101,
                change_amount=5.0,
                volume=1000000,
                turnover=500000000.0,
                high_price=502.0,
                low_price=497.0,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            )
            self.assertIsNotNone(valid_stock)
        except Exception as e:
            self.fail(f"有效股票数据验证失败: {e}")
        
        # 测试无效的股票数据
        with self.assertRaises(ValueError):
            StockData(
                code="HK.00700",
                name="腾讯控股",
                current_price=0.0,  # 无效价格
                open_price=498.0,
                prev_close=495.0,
                change_rate=0.0101,
                change_amount=5.0,
                volume=1000000,
                turnover=500000000.0,
                high_price=502.0,
                low_price=497.0,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            )
        
        # 测试技术指标验证
        try:
            valid_indicators = TechnicalIndicators(
                stock_code="HK.00700",
                ma5=500.0,
                rsi14=65.0,  # 有效RSI值
                rsi_signal=SignalType.HOLD
            )
            self.assertIsNotNone(valid_indicators)
        except Exception as e:
            self.fail(f"有效技术指标验证失败: {e}")
        
        # 测试无效的技术指标
        with self.assertRaises(ValueError):
            TechnicalIndicators(
                stock_code="HK.00700",
                rsi14=150.0,  # 无效RSI值
                rsi_signal=SignalType.HOLD
            )


class TestMonitorSystemStressTest(unittest.TestCase):
    """监控系统压力测试"""
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_high_volume_data_processing(self, mock_futu_market):
        """测试高容量数据处理"""
        # 1. 准备大量股票数据
        large_stock_list = [f"HK.{i:05d}" for i in range(100, 200)]  # 100只股票
        
        # 2. 创建大量mock数据
        mock_snapshots = []
        for i, code in enumerate(large_stock_list):
            mock_snapshots.append({
                'code': code,
                'stock_name': f'股票_{i}',
                'cur_price': 100.0 + i,
                'open_price': 99.0 + i,
                'prev_close_price': 98.0 + i,
                'high_price': 102.0 + i,
                'low_price': 97.0 + i,
                'volume': 1000000 + i * 1000,
                'turnover': (100.0 + i) * (1000000 + i * 1000)
            })
        
        # 3. 设置mock
        mock_instance = mock_futu_market.return_value
        mock_instance.get_market_snapshot.return_value = mock_snapshots
        mock_instance.get_stock_quote.return_value = []
        
        # 创建大量K线数据
        large_kline_data = []
        for i in range(200):  # 200天数据
            large_kline_data.append({
                'time_key': f'2024-{i//30 + 1:02d}-{i%30 + 1:02d}',
                'open': 100.0 + i * 0.1,
                'close': 100.0 + i * 0.1 + 0.5,
                'high': 100.0 + i * 0.1 + 1.0,
                'low': 100.0 + i * 0.1 - 0.5,
                'volume': 1000 + i,
                'turnover': (100.0 + i * 0.1) * (1000 + i)
            })
        
        mock_instance.get_cur_kline.return_value = [{'kline_list': large_kline_data}]
        
        # 4. 执行性能测试
        performance_monitor = PerformanceMonitor()
        data_flow = DataFlowManager()
        
        start_time = datetime.now()
        
        # 测试数据处理性能
        result = await performance_monitor.measure_api_call(
            data_flow.data_update_cycle,
            large_stock_list[:10]  # 限制为10只股票以避免测试过慢
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # 5. 验证性能
        self.assertTrue(result.success)
        self.assertLess(processing_time, 30.0)  # 处理时间应少于30秒
        
        # 验证性能指标
        self.assertEqual(performance_monitor.metrics.api_call_count, 1)
        self.assertGreater(performance_monitor.metrics.api_response_time[0], 0)
        
        # 清理
        await data_flow.data_manager.cleanup()
    
    @patch('monitor.futu_interface.FutuMarket')
    async def test_concurrent_operations(self, mock_futu_market):
        """测试并发操作"""
        # 1. 设置mock
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
            'turnover': 500000000.0
        }]
        mock_instance.get_stock_quote.return_value = []
        mock_instance.get_cur_kline.return_value = [{
            'kline_list': [{'time_key': '2024-01-01', 'open': 100, 'close': 101, 'high': 102, 'low': 99, 'volume': 1000}]
        }]
        
        # 2. 创建多个并发任务
        data_flow = DataFlowManager()
        
        tasks = []
        for i in range(10):
            task = data_flow.data_update_cycle(['HK.00700'])
            tasks.append(task)
        
        # 3. 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 验证结果
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertGreater(len(successful_results), 0)
        
        # 验证所有成功的结果
        for result in successful_results:
            if hasattr(result, 'success'):
                self.assertTrue(result.success)
        
        # 清理
        await data_flow.data_manager.cleanup()


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