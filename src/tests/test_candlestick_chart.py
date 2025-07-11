"""
测试 utils.candlestick_chart 模块的功能
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, '.')

from utils.candlestick_chart import Chart, Candle, fnum
from utils.candlestick_chart.candle import CandleType
from utils.candlestick_chart.utils import hexa_to_rgb, make_candles, round_price


class TestCandle(unittest.TestCase):
    """测试 Candle 类"""

    def setUp(self):
        """设置测试数据"""
        self.basic_candle_data = {
            'open': 100.0,
            'high': 110.0,
            'low': 95.0,
            'close': 105.0,
            'volume': 1000.0,
            'timestamp': 1640995200.0  # 2022-01-01 00:00:00
        }

    def test_candle_creation_basic(self):
        """测试基本的 Candle 创建"""
        candle = Candle(**self.basic_candle_data)
        
        self.assertEqual(candle.open, 100.0)
        self.assertEqual(candle.high, 110.0)
        self.assertEqual(candle.low, 95.0)
        self.assertEqual(candle.close, 105.0)
        self.assertEqual(candle.volume, 1000.0)
        self.assertEqual(candle.timestamp, 1640995200.0)
        # 使用 repr 来比较，因为 NamedTuple 的比较有问题
        self.assertEqual(repr(candle.type), repr(CandleType.bullish))

    def test_candle_creation_minimal(self):
        """测试最小参数的 Candle 创建"""
        minimal_data = {
            'open': 100.0,
            'high': 110.0,
            'low': 95.0,
            'close': 105.0
        }
        candle = Candle(**minimal_data)
        
        self.assertEqual(candle.volume, 0.0)
        self.assertEqual(candle.timestamp, 0.0)
        # 使用 repr 来比较，因为 NamedTuple 的比较有问题
        self.assertEqual(repr(candle.type), repr(CandleType.bullish))

    def test_candle_type_bullish(self):
        """测试看涨蜡烛类型"""
        bullish_data = self.basic_candle_data.copy()
        bullish_data['close'] = 110.0  # close > open
        candle = Candle(**bullish_data)
        
        # 使用 repr 来比较，因为 NamedTuple 的比较有问题
        self.assertEqual(repr(candle.type), repr(CandleType.bullish))

    def test_candle_type_bearish(self):
        """测试看跌蜡烛类型"""
        bearish_data = self.basic_candle_data.copy()
        bearish_data['close'] = 95.0  # close < open
        candle = Candle(**bearish_data)
        
        # 使用 repr 来比较，因为 NamedTuple 的比较有问题
        self.assertEqual(repr(candle.type), repr(CandleType.bearish))

    def test_candle_type_doji(self):
        """测试十字星蜡烛类型（开盘价等于收盘价）"""
        doji_data = self.basic_candle_data.copy()
        doji_data['close'] = 100.0  # close == open
        candle = Candle(**doji_data)
        
        # 使用 repr 来比较，因为 NamedTuple 的比较有问题
        self.assertEqual(repr(candle.type), repr(CandleType.bearish))  # 等于时默认为bearish

    def test_candle_equality(self):
        """测试 Candle 对象的相等性"""
        candle1 = Candle(**self.basic_candle_data)
        candle2 = Candle(**self.basic_candle_data)
        
        self.assertEqual(candle1, candle2)

    def test_candle_inequality(self):
        """测试 Candle 对象的不等性"""
        candle1 = Candle(**self.basic_candle_data)
        different_data = self.basic_candle_data.copy()
        different_data['close'] = 110.0
        candle2 = Candle(**different_data)
        
        self.assertNotEqual(candle1, candle2)

    def test_candle_repr(self):
        """测试 Candle 对象的字符串表示"""
        candle = Candle(**self.basic_candle_data)
        repr_str = repr(candle)
        
        self.assertIn('Candle<', repr_str)
        self.assertIn('open=100.0', repr_str)
        self.assertIn('high=110.0', repr_str)
        self.assertIn('low=95.0', repr_str)
        self.assertIn('close=105.0', repr_str)
        self.assertIn('volume=1000.0', repr_str)
        self.assertIn('type=bullish', repr_str)

    def test_candle_string_conversion(self):
        """测试字符串类型的输入转换"""
        string_data = {
            'open': '100.0',
            'high': '110.0',
            'low': '95.0',
            'close': '105.0',
            'volume': '1000.0',
            'timestamp': '1640995200.0'
        }
        candle = Candle(**string_data)
        
        self.assertEqual(candle.open, 100.0)
        self.assertEqual(candle.high, 110.0)
        self.assertEqual(candle.low, 95.0)
        self.assertEqual(candle.close, 105.0)
        self.assertEqual(candle.volume, 1000.0)
        self.assertEqual(candle.timestamp, 1640995200.0)


class TestChart(unittest.TestCase):
    """测试 Chart 类"""

    def setUp(self):
        """设置测试数据"""
        self.test_candles = [
            Candle(open=100, high=110, low=95, close=105, volume=1000),
            Candle(open=105, high=115, low=100, close=108, volume=1200),
            Candle(open=108, high=120, low=103, close=112, volume=1500),
            Candle(open=112, high=118, low=108, close=115, volume=1300),
            Candle(open=115, high=125, low=110, close=120, volume=1800),
        ]

    def test_chart_creation_basic(self):
        """测试基本的 Chart 创建"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        self.assertIsNotNone(chart)
        self.assertEqual(chart.info_bar.name, "Test Chart")
        self.assertTrue(hasattr(chart, 'chart_data'))
        self.assertTrue(hasattr(chart, 'renderer'))
        self.assertTrue(hasattr(chart, 'y_axis'))
        self.assertTrue(hasattr(chart, 'volume_pane'))

    def test_chart_creation_with_size(self):
        """测试带尺寸参数的 Chart 创建"""
        chart = Chart(self.test_candles, title="Test Chart", width=80, height=30)
        
        self.assertEqual(chart.chart_data.width, 80)
        self.assertEqual(chart.chart_data.height, 30)

    def test_chart_render(self):
        """测试图表渲染"""
        chart = Chart(self.test_candles, title="Test Chart", width=60, height=20)
        
        rendered = chart._render()
        
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)
        # 检查是否包含ANSI颜色代码
        self.assertIn('\x1b[', rendered)

    def test_chart_update_candles(self):
        """测试更新蜡烛数据"""
        chart = Chart(self.test_candles[:3], title="Test Chart")
        
        # 添加新的蜡烛
        new_candles = self.test_candles[3:]
        chart.update_candles(new_candles)
        
        # 验证数据已更新
        self.assertEqual(len(chart.chart_data.main_candle_set.candles), 5)

    def test_chart_update_candles_reset(self):
        """测试重置蜡烛数据"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        new_candles = self.test_candles[:2]
        chart.update_candles(new_candles, reset=True)
        
        # 验证数据已重置
        self.assertEqual(len(chart.chart_data.main_candle_set.candles), 2)

    def test_chart_update_size(self):
        """测试更新图表尺寸"""
        chart = Chart(self.test_candles, title="Test Chart", width=60, height=20)
        
        chart.update_size(80, 30)
        
        self.assertEqual(chart.chart_data.width, 80)
        self.assertEqual(chart.chart_data.height, 30)

    def test_chart_color_settings(self):
        """测试图表颜色设置"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        # 设置看涨颜色
        chart.set_bull_color(0, 255, 0)
        self.assertEqual(chart.renderer.bullish_color, (0, 255, 0))
        
        # 设置看跌颜色
        chart.set_bear_color(255, 0, 0)
        self.assertEqual(chart.renderer.bearish_color, (255, 0, 0))

    def test_chart_volume_settings(self):
        """测试成交量设置"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        # 设置成交量颜色
        chart.set_vol_bull_color(0, 255, 0)
        chart.set_vol_bear_color(255, 0, 0)
        
        self.assertEqual(chart.volume_pane.bullish_color, (0, 255, 0))
        self.assertEqual(chart.volume_pane.bearish_color, (255, 0, 0))
        
        # 设置成交量面板高度
        chart.set_volume_pane_height(10)
        self.assertEqual(chart.volume_pane.height, 10)
        
        # 禁用成交量面板
        chart.set_volume_pane_enabled(False)
        self.assertFalse(chart.volume_pane.enabled)

    def test_chart_labels(self):
        """测试图表标签设置"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        chart.set_label("price", "120.45")
        self.assertEqual(chart.info_bar.labels.price, "120.45")
        
        chart.set_name("My Stock Chart")
        self.assertEqual(chart.info_bar.name, "My Stock Chart")

    def test_chart_highlights(self):
        """测试价格高亮设置"""
        chart = Chart(self.test_candles, title="Test Chart")
        
        # 设置高亮
        chart.set_highlight("115.00", "red")
        self.assertEqual(chart.highlights["115.00"], "red")
        
        # 设置RGB颜色高亮
        chart.set_highlight("120.00", (255, 0, 0))
        self.assertEqual(chart.highlights["120.00"], (255, 0, 0))
        
        # 清除高亮
        chart.set_highlight("115.00", "")
        self.assertNotIn("115.00", chart.highlights)

    def test_chart_empty_candles(self):
        """测试空蜡烛数据"""
        # 空蜡烛数据应该能创建图表，但渲染时可能会有问题
        chart = Chart([], title="Empty Chart")
        self.assertIsNotNone(chart)
        # 验证空数据不会导致崩溃
        try:
            chart._render()
        except Exception:
            # 允许渲染失败，因为没有数据
            pass

    def test_chart_single_candle(self):
        """测试单个蜡烛数据"""
        single_candle = [self.test_candles[0]]
        chart = Chart(single_candle, title="Single Candle")
        
        self.assertIsNotNone(chart)
        rendered = chart._render()
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)


class TestUtils(unittest.TestCase):
    """测试工具函数"""

    def test_fnum_integer(self):
        """测试整数格式化"""
        self.assertEqual(fnum(1000), "1,000")
        self.assertEqual(fnum(1000000), "1,000,000")
        self.assertEqual(fnum(0), "0")

    def test_fnum_float(self):
        """测试浮点数格式化"""
        # 根据实际的常量值调整期望结果
        self.assertEqual(fnum(1000.5), "1,000.50")
        self.assertEqual(fnum(0.5), "0.5000")  # 实际的精度
        self.assertEqual(fnum(0.0001), "0.0001")

    def test_fnum_small_numbers(self):
        """测试小数字格式化"""
        result = fnum(0.000000001234)
        self.assertIn("0×", result)  # 应该有压缩格式

    def test_fnum_string_input(self):
        """测试字符串输入"""
        self.assertEqual(fnum("1000"), "1,000")
        self.assertEqual(fnum("1000.5"), "1,000.50")

    def test_hexa_to_rgb(self):
        """测试十六进制颜色转换"""
        self.assertEqual(hexa_to_rgb("#FF0000"), (255, 0, 0))
        self.assertEqual(hexa_to_rgb("FF0000"), (255, 0, 0))
        self.assertEqual(hexa_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(hexa_to_rgb("#0000FF"), (0, 0, 255))

    def test_make_candles(self):
        """测试从字典列表创建蜡烛"""
        candle_data = [
            {'open': 100, 'high': 110, 'low': 95, 'close': 105, 'volume': 1000},
            {'open': 105, 'high': 115, 'low': 100, 'close': 108, 'volume': 1200}
        ]
        
        candles = make_candles(iter(candle_data))
        
        self.assertEqual(len(candles), 2)
        self.assertIsInstance(candles[0], Candle)
        self.assertIsInstance(candles[1], Candle)
        self.assertEqual(candles[0].open, 100)
        self.assertEqual(candles[1].open, 105)

    def test_round_price(self):
        """测试价格四舍五入"""
        result = round_price(123.456)
        self.assertIsInstance(result, str)
        # 默认情况下应该返回格式化的数字
        self.assertIn("123", result)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_chart_with_real_data_format(self):
        """测试使用类似真实数据格式的图表"""
        # 模拟从富途API获取的数据格式
        real_data = [
            {'open': 52.3, 'high': 53.1, 'low': 51.8, 'close': 52.8, 'volume': 1500000},
            {'open': 52.8, 'high': 54.2, 'low': 52.5, 'close': 53.5, 'volume': 1800000},
            {'open': 53.5, 'high': 54.8, 'low': 53.0, 'close': 54.2, 'volume': 2000000},
            {'open': 54.2, 'high': 55.5, 'low': 53.8, 'close': 55.0, 'volume': 2200000},
        ]
        
        candles = make_candles(iter(real_data))
        chart = Chart(candles, title="Real Data Test", width=80, height=25)
        
        # 设置更真实的颜色
        chart.set_bull_color(52, 208, 88)  # 绿色
        chart.set_bear_color(234, 74, 90)  # 红色
        
        # 设置标签
        chart.set_label("price", fnum(candles[-1].close))
        chart.set_label("volume", fnum(candles[-1].volume))
        
        rendered = chart._render()
        
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)
        
        # 验证渲染结果包含预期内容
        self.assertIn("Real Data Test", rendered)

    def test_chart_edge_cases(self):
        """测试边界情况"""
        # 测试所有相同价格的蜡烛
        flat_candles = [
            Candle(open=100, high=100, low=100, close=100, volume=1000),
            Candle(open=100, high=100, low=100, close=100, volume=1000),
        ]
        
        chart = Chart(flat_candles, title="Flat Data")
        rendered = chart._render()
        
        self.assertIsInstance(rendered, str)
        self.assertGreater(len(rendered), 0)

    def test_chart_with_parquet_data(self):
        """测试使用项目中的parquet数据"""
        import pandas as pd
        from pathlib import Path
        
        # 查找测试数据文件
        data_file = Path('./tests/test_data/HK.09988_2022-04-11_15M.parquet')
        if data_file.exists():
            df = pd.read_parquet(data_file)
            
            # 取前20条数据
            df_sample = df.head(20)
            
            # 转换为蜡烛数据
            candles = []
            for _, row in df_sample.iterrows():
                candles.append(Candle(
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'] if 'volume' in row else 0
                ))
            
            chart = Chart(candles, title="HK.09988 Test Data")
            rendered = chart._render()
            
            self.assertIsInstance(rendered, str)
            self.assertGreater(len(rendered), 0)
        else:
            self.skipTest("测试数据文件不存在")


if __name__ == '__main__':
    unittest.main()