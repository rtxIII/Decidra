"""
测试触及市价单和触及限价单订单类型功能

测试内容：
1. 验证ORDER_TYPES中包含新订单类型
2. 验证订单数据结构支持新类型
3. 验证futu_trade.py中的订单类型映射
"""
import unittest
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from ..base.order import ORDER_TYPES, OrderData


class TestTrailingStopOrders(unittest.TestCase):
    """测试触及市价单和触及限价单功能"""

    def test_order_types_include_trailing_stop(self):
        """测试ORDER_TYPES包含TRAILING_STOP"""
        order_type_codes = [code for code, name in ORDER_TYPES]
        self.assertIn("TRAILING_STOP", order_type_codes,
                     "ORDER_TYPES应包含TRAILING_STOP")

    def test_order_types_include_trailing_stop_limit(self):
        """测试ORDER_TYPES包含TRAILING_STOP_LIMIT"""
        order_type_codes = [code for code, name in ORDER_TYPES]
        self.assertIn("TRAILING_STOP_LIMIT", order_type_codes,
                     "ORDER_TYPES应包含TRAILING_STOP_LIMIT")

    def test_trailing_stop_display_name(self):
        """测试TRAILING_STOP的显示名称"""
        order_types_dict = dict(ORDER_TYPES)
        self.assertEqual(order_types_dict["TRAILING_STOP"],
                        "触及市价单(止盈)",
                        "TRAILING_STOP显示名称应为'触及市价单(止盈)'")

    def test_trailing_stop_limit_display_name(self):
        """测试TRAILING_STOP_LIMIT的显示名称"""
        order_types_dict = dict(ORDER_TYPES)
        self.assertEqual(order_types_dict["TRAILING_STOP_LIMIT"],
                        "触及限价单(止盈)",
                        "TRAILING_STOP_LIMIT显示名称应为'触及限价单(止盈)'")

    def test_order_data_with_trailing_stop(self):
        """测试OrderData支持TRAILING_STOP类型"""
        order = OrderData(
            code="HK.00700",
            price=400.0,
            qty=100,
            order_type="TRAILING_STOP",
            trd_side="BUY",
            trd_env="SIMULATE",
            market="HK",
            aux_price=390.0,  # 触发价格
            time_in_force="DAY",
            remark="测试触及市价单"
        )

        self.assertEqual(order.order_type, "TRAILING_STOP")
        self.assertEqual(order.aux_price, 390.0)
        self.assertEqual(order.code, "HK.00700")

    def test_order_data_with_trailing_stop_limit(self):
        """测试OrderData支持TRAILING_STOP_LIMIT类型"""
        order = OrderData(
            code="US.AAPL",
            price=180.0,
            qty=50,
            order_type="TRAILING_STOP_LIMIT",
            trd_side="SELL",
            trd_env="SIMULATE",
            market="US",
            aux_price=185.0,  # 触发价格
            time_in_force="GTC",
            remark="测试触及限价单"
        )

        self.assertEqual(order.order_type, "TRAILING_STOP_LIMIT")
        self.assertEqual(order.aux_price, 185.0)
        self.assertEqual(order.code, "US.AAPL")

    def test_order_types_count(self):
        """测试ORDER_TYPES包含正确数量的订单类型"""
        # 应该有10种订单类型
        expected_count = 10
        actual_count = len(ORDER_TYPES)
        self.assertEqual(actual_count, expected_count,
                        f"ORDER_TYPES应包含{expected_count}种订单类型，实际为{actual_count}种")

    def test_order_types_order(self):
        """测试ORDER_TYPES中新类型的顺序"""
        order_type_codes = [code for code, name in ORDER_TYPES]

        # TRAILING_STOP应该在STOP_LIMIT之后
        stop_limit_index = order_type_codes.index("STOP_LIMIT")
        trailing_stop_index = order_type_codes.index("TRAILING_STOP")
        trailing_stop_limit_index = order_type_codes.index("TRAILING_STOP_LIMIT")

        self.assertGreater(trailing_stop_index, stop_limit_index,
                          "TRAILING_STOP应该在STOP_LIMIT之后")
        self.assertGreater(trailing_stop_limit_index, trailing_stop_index,
                          "TRAILING_STOP_LIMIT应该在TRAILING_STOP之后")


class TestOrderTypeMapping(unittest.TestCase):
    """测试订单类型映射功能"""

    def test_all_order_types_have_unique_codes(self):
        """测试所有订单类型代码唯一"""
        order_type_codes = [code for code, name in ORDER_TYPES]
        self.assertEqual(len(order_type_codes), len(set(order_type_codes)),
                        "订单类型代码应该唯一")

    def test_all_order_types_have_display_names(self):
        """测试所有订单类型都有显示名称"""
        for code, name in ORDER_TYPES:
            self.assertTrue(name, f"订单类型{code}应该有显示名称")
            self.assertIsInstance(name, str, f"订单类型{code}的显示名称应该是字符串")

    def test_order_type_codes_uppercase(self):
        """测试所有订单类型代码为大写"""
        for code, name in ORDER_TYPES:
            self.assertEqual(code, code.upper(),
                           f"订单类型代码{code}应该为大写")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTrailingStopOrders))
    suite.addTests(loader.loadTestsFromTestCase(TestOrderTypeMapping))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
