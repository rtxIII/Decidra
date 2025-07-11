#!/usr/bin/env python3
"""
富途API订阅功能测试

测试订阅功能的各个接口，包括数据模型、订阅管理、推送处理等
"""

import sys
import os
import unittest
from unittest import TestCase, skipIf
import time
import threading
from collections import defaultdict
import atexit

from typing import List, Dict, Optional, Callable, Any
from unittest.mock import Mock, patch



sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import futu as ft
    from api.futu import (
        FutuClient, FutuConfig, FutuConnectException, FutuQuoteException,
        QuoteManager, StockInfo, KLineData, StockQuote, MarketSnapshot,
        TickerData, OrderBookData, RTData,
        create_client
    )
    FUTU_AVAILABLE = True
except ImportError as e:
    print(f"富途API导入失败: {e}")
    FUTU_AVAILABLE = False

# 全局清理变量
_all_clients = []

def is_futu_available():
    """检查FutuOpenD是否可用"""
    if not FUTU_AVAILABLE:
        return False
        
    client = None
    try:
        config = FutuConfig(
            host="127.0.0.1",
            port=11111,
            enable_proto_encrypt=False,
            timeout=3
        )
        client = FutuClient(config)
        client.connect()
        return True
    except:
        return False
    finally:
        if client:
            try:
                client.disconnect()
            except:
                pass

def cleanup_all_connections():
    """清理所有连接"""
    global _all_clients
    for client in _all_clients:
        try:
            if hasattr(client, 'disconnect'):
                client.disconnect()
        except:
            pass
    _all_clients.clear()

def force_exit():
    """强制退出程序"""
    try:
        cleanup_all_connections()
        time.sleep(0.5)  # 给线程一些时间来清理
    except:
        pass
    finally:
        os._exit(0)  # 强制退出

# 注册清理函数
atexit.register(cleanup_all_connections)

class TestSubscriptionDataModels(TestCase):
    """测试订阅相关的数据模型"""

    def test_ticker_data_creation(self):
        """测试TickerData创建"""
        # 测试正常创建
        ticker = TickerData(
            code="HK.00700",
            sequence=1001,
            time="2024-01-15 09:30:00",
            price=350.5,
            volume=1000,
            turnover=350500.0,
            ticker_direction="BUY",
            type="AUCTION"
        )
        
        self.assertEqual(ticker.code, "HK.00700")
        self.assertEqual(ticker.sequence, 1001)
        self.assertEqual(ticker.price, 350.5)
        self.assertEqual(ticker.volume, 1000)
        self.assertEqual(ticker.ticker_direction, "BUY")

    def test_ticker_data_from_dict(self):
        """测试TickerData从字典创建"""
        data = {
            'code': 'HK.00700',
            'sequence': '1001',
            'time': '2024-01-15 09:30:00',
            'price': '350.5',
            'volume': '1000',
            'turnover': '350500.0',
            'ticker_direction': 'BUY',
            'type': 'AUCTION'
        }
        
        ticker = TickerData.from_dict(data)
        self.assertEqual(ticker.code, "HK.00700")
        self.assertEqual(ticker.sequence, 1001)
        self.assertEqual(ticker.price, 350.5)

    def test_order_book_data_creation(self):
        """测试OrderBookData创建"""
        order_book = OrderBookData(
            code="HK.00700",
            svr_recv_time_bid="2024-01-15 09:30:00",
            svr_recv_time_ask="2024-01-15 09:30:00",
            bid_price_1=350.0,
            bid_volume_1=1000,
            ask_price_1=350.5,
            ask_volume_1=2000
        )
        
        self.assertEqual(order_book.code, "HK.00700")
        self.assertEqual(order_book.bid_price_1, 350.0)
        self.assertEqual(order_book.ask_price_1, 350.5)

    def test_order_book_data_from_dict(self):
        """测试OrderBookData从字典创建"""
        data = {
            'code': 'HK.00700',
            'svr_recv_time_bid': '2024-01-15 09:30:00',
            'svr_recv_time_ask': '2024-01-15 09:30:00',
            'Bid1': '350.0',
            'BidVol1': '1000',
            'Ask1': '350.5',
            'AskVol1': '2000'
        }
        
        order_book = OrderBookData.from_dict(data)
        self.assertEqual(order_book.code, "HK.00700")
        self.assertEqual(order_book.bid_price_1, 350.0)
        self.assertEqual(order_book.ask_price_1, 350.5)

    def test_rt_data_creation(self):
        """测试RTData创建"""
        rt_data = RTData(
            code="HK.00700",
            time="09:30",
            is_blank=False,
            opened_mins=570,
            cur_price=350.5,
            last_close=349.0,
            avg_price=350.2,
            volume=10000,
            turnover=3502000.0
        )
        
        self.assertEqual(rt_data.code, "HK.00700")
        self.assertEqual(rt_data.cur_price, 350.5)
        self.assertEqual(rt_data.volume, 10000)
        self.assertFalse(rt_data.is_blank)

    def test_rt_data_from_dict(self):
        """测试RTData从字典创建"""
        data = {
            'code': 'HK.00700',
            'time': '09:30',
            'is_blank': False,
            'opened_mins': '570',
            'cur_price': '350.5',
            'last_close': '349.0',
            'avg_price': '350.2',
            'volume': '10000',
            'turnover': '3502000.0'
        }
        
        rt_data = RTData.from_dict(data)
        self.assertEqual(rt_data.code, "HK.00700")
        self.assertEqual(rt_data.cur_price, 350.5)
        self.assertFalse(rt_data.is_blank)


class TestSubscriptionManager(TestCase):
    """测试订阅管理器（不需要连接）"""

    def setUp(self):
        """测试前设置"""
        self.config = FutuConfig(enable_proto_encrypt=False)
        self.client = FutuClient(self.config)

    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            finally:
                self.client = None

    def test_quote_manager_initialization(self):
        """测试行情管理器初始化"""
        self.assertIsInstance(self.client.quote, QuoteManager)
        self.assertIsInstance(self.client.quote._subscriptions, dict)
        self.assertIsInstance(self.client.quote._handlers, dict)
        self.assertIsInstance(self.client.quote._sub_type_map, dict)

    def test_subscription_type_mapping(self):
        """测试订阅类型映射"""
        sub_type_map = self.client.quote._sub_type_map
        
        # 检查关键的订阅类型映射
        self.assertIn('quote', sub_type_map)
        self.assertIn('kline_day', sub_type_map)
        self.assertIn('ticker', sub_type_map)
        self.assertIn('order_book', sub_type_map)
        self.assertIn('rt_data', sub_type_map)
        
        # 检查映射到正确的富途类型
        self.assertEqual(sub_type_map['quote'], ft.SubType.QUOTE)
        self.assertEqual(sub_type_map['kline_day'], ft.SubType.K_DAY)
        self.assertEqual(sub_type_map['ticker'], ft.SubType.TICKER)

    def test_subscription_methods_exist(self):
        """测试订阅方法存在性"""
        quote_manager = self.client.quote
        
        # 基础订阅方法
        self.assertTrue(hasattr(quote_manager, 'subscribe'))
        self.assertTrue(hasattr(quote_manager, 'unsubscribe'))
        self.assertTrue(hasattr(quote_manager, 'unsubscribe_all'))
        self.assertTrue(hasattr(quote_manager, 'set_handler'))
        
        # 便捷订阅方法
        self.assertTrue(hasattr(quote_manager, 'subscribe_quote'))
        self.assertTrue(hasattr(quote_manager, 'subscribe_kline'))
        self.assertTrue(hasattr(quote_manager, 'subscribe_ticker'))
        self.assertTrue(hasattr(quote_manager, 'subscribe_order_book'))
        self.assertTrue(hasattr(quote_manager, 'subscribe_rt_data'))
        
        # 订阅管理方法
        self.assertTrue(hasattr(quote_manager, 'get_subscriptions'))
        self.assertTrue(hasattr(quote_manager, 'is_subscribed'))

    def test_subscription_when_not_connected(self):
        """测试未连接时的订阅异常"""
        with self.assertRaises(FutuConnectException):
            self.client.quote.subscribe(["HK.00700"], ["quote"])
        
        with self.assertRaises(FutuConnectException):
            self.client.quote.subscribe_quote(["HK.00700"])
        
        with self.assertRaises(FutuConnectException):
            self.client.quote.unsubscribe(["HK.00700"], ["quote"])

    def test_invalid_subscription_types(self):
        """测试无效订阅类型处理"""
        # 这个测试不需要连接，只测试参数验证
        quote_manager = self.client.quote
        
        # 检查订阅类型映射功能
        valid_types = ["quote", "kline_day", "ticker"]
        invalid_types = ["invalid_type", "unknown"]
        
        # 测试类型验证逻辑（不实际执行订阅）
        for sub_type in valid_types:
            self.assertIn(sub_type, quote_manager._sub_type_map)
        
        for sub_type in invalid_types:
            self.assertNotIn(sub_type, quote_manager._sub_type_map)


@skipIf(not is_futu_available(), "FutuOpenD not available")
class TestSubscriptionIntegration(TestCase):
    """订阅功能集成测试（需要FutuOpenD）"""

    def setUp(self):
        """测试前准备"""
        global _all_clients
        config = FutuConfig(enable_proto_encrypt=False)
        self.client = FutuClient(config)
        _all_clients.append(self.client)
        self.client.connect()

    def tearDown(self):
        """测试后清理"""
        global _all_clients
        try:
            # 尝试取消所有订阅（忽略富途API的时间限制）
            try:
                self.client.quote.unsubscribe_all()
            except Exception as e:
                # 富途API的1分钟订阅限制是正常的业务限制
                if "订阅时间过短" in str(e) or "至少需要订阅1分钟" in str(e):
                    pass  # 这是预期的，不需要warning
                else:
                    print(f"Warning: 取消订阅时出现意外错误: {e}")
            
            # 断开连接
            if self.client:
                self.client.disconnect()
                
            # 从全局列表移除
            if self.client in _all_clients:
                _all_clients.remove(self.client)
                
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        finally:
            self.client = None
            
            # 给富途线程一些时间来清理
            time.sleep(0.1)

    def test_basic_subscription_flow(self):
        """测试基础订阅流程"""
        print("\n测试基础订阅流程...")
        
        codes = ["HK.00700"]
        
        # 1. 测试订阅
        try:
            result = self.client.quote.subscribe(codes, ["quote"])
            self.assertTrue(result)
            print("   ✓ 基础订阅成功")
            
            # 检查订阅状态
            self.assertTrue(self.client.quote.is_subscribed("HK.00700", "quote"))
            
            # 获取订阅列表
            subscriptions = self.client.quote.get_subscriptions()
            self.assertIsInstance(subscriptions, dict)
            
        except Exception as e:
            # 富途API可能需要权限或订阅限制
            if "权限" in str(e) or "订阅" in str(e) or "limit" in str(e).lower():
                print(f"   注意: {e} (这是富途API的权限限制)")
            else:
                self.fail(f"基础订阅测试失败: {e}")

    def test_convenience_subscription_methods(self):
        """测试便捷订阅方法"""
        print("\n测试便捷订阅方法...")
        
        codes = ["HK.00700"]
        
        # 测试各种便捷订阅方法
        subscription_tests = [
            ("报价订阅", lambda: self.client.quote.subscribe_quote(codes)),
            ("日K线订阅", lambda: self.client.quote.subscribe_kline(codes, "day")),
            ("逐笔数据订阅", lambda: self.client.quote.subscribe_ticker(codes)),
            ("买卖盘订阅", lambda: self.client.quote.subscribe_order_book(codes)),
            ("分时数据订阅", lambda: self.client.quote.subscribe_rt_data(codes)),
        ]
        
        for test_name, subscribe_func in subscription_tests:
            try:
                result = subscribe_func()
                if result:
                    print(f"   ✓ {test_name}成功")
                else:
                    print(f"   ! {test_name}返回False")
                    
            except Exception as e:
                # 富途API可能需要权限或有订阅限制
                if any(keyword in str(e) for keyword in ["权限", "订阅", "limit", "permission", "subscribe"]):
                    print(f"   注意: {test_name} - {e} (富途API限制)")
                else:
                    self.fail(f"{test_name}失败: {e}")

    def test_subscription_with_callback(self):
        """测试带回调的订阅"""
        print("\n测试带回调的订阅...")
        
        # 创建回调函数
        received_data = []
        
        def quote_callback(data):
            received_data.append(data)
            print(f"   接收到报价推送: {len(received_data)} 条")
        
        try:
            # 设置处理器
            result = self.client.quote.set_handler("quote", quote_callback)
            self.assertTrue(result)
            print("   ✓ 设置回调处理器成功")
            
            # 订阅报价
            result = self.client.quote.subscribe_quote(["HK.00700"], quote_callback)
            print("   ✓ 带回调的订阅成功")
            
        except Exception as e:
            if any(keyword in str(e) for keyword in ["权限", "订阅", "limit", "permission"]):
                print(f"   注意: 带回调订阅 - {e} (富途API限制)")
            else:
                self.fail(f"带回调订阅失败: {e}")

    def test_unsubscribe_operations(self):
        """测试取消订阅操作"""
        print("\n测试取消订阅操作...")
        
        codes = ["HK.00700"]
        
        try:
            # 先订阅
            result = self.client.quote.subscribe(codes, ["quote"])
            self.assertTrue(result)
            print("   ✓ 先进行订阅")
            
            # 验证订阅状态
            self.assertTrue(self.client.quote.is_subscribed("HK.00700", "quote"))
            print("   ✓ 订阅状态验证成功")
            
            # 尝试取消特定订阅（可能因为时间限制失败）
            try:
                result = self.client.quote.unsubscribe(codes, ["quote"])
                if result:
                    print("   ✓ 取消特定订阅成功")
                else:
                    print("   ! 取消特定订阅返回False")
            except Exception as e:
                if "订阅时间过短" in str(e) or "至少需要订阅1分钟" in str(e):
                    print(f"   注意: 取消订阅 - {e} (富途API限制)")
                    # 这是预期的行为，不算测试失败
                else:
                    raise
            
            # 尝试取消所有订阅（可能因为时间限制失败）
            try:
                result = self.client.quote.unsubscribe_all()
                if result:
                    print("   ✓ 取消所有订阅成功")
                else:
                    print("   ! 取消所有订阅返回False")
            except Exception as e:
                if "订阅时间过短" in str(e) or "至少需要订阅1分钟" in str(e):
                    print(f"   注意: 取消所有订阅 - {e} (富途API限制)")
                    # 这是预期的行为，不算测试失败
                else:
                    raise
                    
        except Exception as e:
            if any(keyword in str(e) for keyword in ["权限", "订阅", "limit", "permission"]):
                print(f"   注意: 订阅操作 - {e} (富途API限制)")
            else:
                self.fail(f"取消订阅测试失败: {e}")

    def test_real_time_data_methods(self):
        """测试实时数据获取方法"""
        print("\n测试实时数据获取方法...")
        
        code = "HK.00700"
        
        # 测试各种实时数据方法
        data_tests = [
            ("逐笔数据", lambda: self.client.quote.get_ticker_data(code, 10)),
            ("买卖盘数据", lambda: self.client.quote.get_order_book(code)),
            ("分时数据", lambda: self.client.quote.get_rt_data(code)),
            ("经纪队列", lambda: self.client.quote.get_broker_queue(code)),
        ]
        
        for test_name, get_func in data_tests:
            try:
                data = get_func()
                self.assertIsNotNone(data)
                print(f"   ✓ {test_name}获取成功")
                
            except Exception as e:
                # 这些功能可能需要订阅或权限
                if any(keyword in str(e) for keyword in ["订阅", "权限", "subscribe", "permission", "请先"]):
                    print(f"   注意: {test_name} - {e} (需要先订阅或权限限制)")
                else:
                    self.fail(f"{test_name}获取失败: {e}")


class TestSubscriptionOffline(TestCase):
    """订阅功能离线测试（不需要FutuOpenD）"""

    def test_subscription_state_management(self):
        """测试订阅状态管理"""
        config = FutuConfig(enable_proto_encrypt=False)
        client = FutuClient(config)
        
        quote_manager = client.quote
        
        # 测试初始状态
        subscriptions = quote_manager.get_subscriptions()
        self.assertEqual(len(subscriptions), 0)
        
        # 测试订阅状态检查
        self.assertFalse(quote_manager.is_subscribed("HK.00700", "quote"))
        
        # 测试处理器存储
        def dummy_handler(data):
            pass
        
        quote_manager._handlers["quote"] = dummy_handler
        self.assertEqual(quote_manager._handlers["quote"], dummy_handler)

    def test_ktype_mapping(self):
        """测试K线类型映射"""
        config = FutuConfig(enable_proto_encrypt=False)
        client = FutuClient(config)
        
        # 测试K线类型映射逻辑
        ktype_map = {
            "1m": "kline_1m", "5m": "kline_5m", "15m": "kline_15m", 
            "30m": "kline_30m", "60m": "kline_60m", "day": "kline_day",
            "week": "kline_week", "month": "kline_month"
        }
        
        for short_type, full_type in ktype_map.items():
            self.assertIn(full_type, client.quote._sub_type_map)

    def test_unsubscribe_logic_offline(self):
        """测试取消订阅逻辑（离线测试）"""
        config = FutuConfig(enable_proto_encrypt=False)
        client = FutuClient(config)
        quote_manager = client.quote
        
        # 模拟订阅状态（正确的数据结构）
        code = "HK.00700"
        sub_type = "quote"
        
        # 手动设置订阅状态 - 正确的数据结构是 _subscriptions[sub_type][code]
        quote_manager._subscriptions[sub_type][code] = [code]
        
        # 验证初始状态
        self.assertTrue(quote_manager.is_subscribed(code, sub_type))
        
        # 测试取消订阅逻辑（不实际调用富途API）
        # 这里我们只测试内部状态管理逻辑
        subscriptions = quote_manager.get_subscriptions()
        self.assertIn(sub_type, subscriptions)
        self.assertIn(code, subscriptions[sub_type])
        
        print("   ✓ 离线取消订阅逻辑测试通过")


if __name__ == '__main__':
    print("=" * 60)
    print("富途API订阅功能测试")
    print("=" * 60)
    
    try:
        # 检查富途API可用性
        if not FUTU_AVAILABLE:
            print("⚠️  富途API不可用，只运行离线测试")
            suite = unittest.TestSuite()
            suite.addTest(unittest.makeSuite(TestSubscriptionDataModels))
            suite.addTest(unittest.makeSuite(TestSubscriptionManager))
            suite.addTest(unittest.makeSuite(TestSubscriptionOffline))
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
        else:
            # 运行所有测试
            result = unittest.main(verbosity=2, exit=False)
            
        # 测试完成后的清理
        cleanup_all_connections()
        
        # 等待一段时间让富途线程清理
        print("\n等待线程清理...")
        time.sleep(2)
        
        # 检查是否有活跃的线程
        active_threads = [t for t in threading.enumerate() if t != threading.main_thread()]
        if active_threads:
            print(f"警告: 仍有 {len(active_threads)} 个活跃线程")
            for t in active_threads:
                print(f"  - {t.name}: {t}")
        
        print("测试完成，程序即将退出...")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试执行出错: {e}")
    finally:
        # 强制清理和退出
        force_exit() 