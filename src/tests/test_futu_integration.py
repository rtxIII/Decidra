#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
富途API集成测试 - 基于 futu_lowfreq_example.py

本测试集包含了富途API低频数据接口的完整集成测试
"""

import unittest
import sys
import os
import time
from unittest import TestCase, skipIf


# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 尝试导入富途API
try:
    import futu as ft
    FUTU_AVAILABLE = True
except ImportError:
    ft = None
    FUTU_AVAILABLE = False

# 导入我们的模块
from api.futu import (
    FutuClient, FutuConfig,
    FutuException, FutuQuoteException,
    StockInfo, MarketSnapshot, AuTypeInfo, PlateInfo, PlateStock
)

def is_futu_available():
    """检查富途API是否可用"""
    if not FUTU_AVAILABLE:
        return False
    
    try:
        test_client = FutuClient()
        test_client.connect()
        result = test_client.is_connected
        test_client.disconnect()
        return result
    except:
        return False

class TestFutuIntegration(TestCase):
    """富途API集成测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("=" * 60)
        print("富途API集成测试")
        print("=" * 60)
        
        if not is_futu_available():
            raise unittest.SkipTest("富途API环境不可用，跳过所有测试")
        
        print("✅ 富途API环境检查通过")

    def setUp(self):
        """每个测试前的设置"""
        config = FutuConfig(
            host="127.0.0.1",
            port=11111,
            enable_proto_encrypt=False,
            timeout=30
        )
        self.client = FutuClient(config)
        self.client.connect()
        self.assertTrue(self.client.is_connected)

    def tearDown(self):
        """每个测试后的清理"""
        try:
            if self.client:
                self.client.disconnect()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        finally:
            self.client = None
            time.sleep(0.1)

    def test_trading_days(self):
        """测试获取交易日历"""
        print("\n1️⃣ 测试获取港股交易日历")
        
        trading_days = self.client.quote.get_trading_days("HK", start="2024-01-01", end="2024-01-31")
        
        self.assertIsInstance(trading_days, list)
        self.assertGreater(len(trading_days), 0)
        print(f"   ✓ 2024年1月港股交易日共 {len(trading_days)} 天")
        
        # 合理性检查：1月应该有15-25个交易日
        self.assertGreaterEqual(len(trading_days), 15)
        self.assertLessEqual(len(trading_days), 25)

    def test_stock_basic_info(self):
        """测试获取股票基础信息"""
        print("\n2️⃣ 测试获取港股基础信息")
        
        stocks = self.client.quote.get_stock_info("HK", "STOCK")
        
        self.assertIsInstance(stocks, list)
        self.assertGreater(len(stocks), 1000)  # 港股应该有几千只股票
        print(f"   ✓ 港股股票总数: {len(stocks)}")
        
        # 验证前几只股票信息
        for stock in stocks[:3]:
            self.assertIsInstance(stock, StockInfo)
            self.assertIsInstance(stock.code, str)
            self.assertIsInstance(stock.name, str)
            print(f"   📈 {stock.code} - {stock.name}")

    def test_market_snapshot(self):
        """测试获取市场快照"""
        print("\n3️⃣ 测试获取市场快照")
        
        codes = ["HK.00700", "HK.00388", "HK.00981"]
        snapshots = self.client.quote.get_market_snapshot(codes)
        
        self.assertIsInstance(snapshots, list)
        self.assertEqual(len(snapshots), len(codes))
        
        for snapshot in snapshots:
            self.assertIsInstance(snapshot, MarketSnapshot)
            self.assertGreater(snapshot.last_price, 0)
            self.assertGreater(snapshot.open_price, 0)
            print(f"   📊 {snapshot.code}: {snapshot.last_price:.2f}")

    def test_autype_list_rehab(self):
        """测试获取复权因子 (使用get_rehab接口)"""
        print("\n4️⃣ 测试获取复权因子")
        
        codes = ["HK.00700"]
        
        try:
            autype_list = self.client.quote.get_autype_list(codes)
            
            self.assertIsInstance(autype_list, list)
            if autype_list:
                print(f"   ✓ 获取到 {len(autype_list)} 条复权信息")
                
                for autype in autype_list[:3]:
                    self.assertIsInstance(autype, AuTypeInfo)
                    print(f"   📈 {autype.code} - 除权日: {autype.ex_div_date}")
            else:
                print("   注意: 暂无复权信息")
                
        except FutuQuoteException as e:
            if "权限" in str(e) or "limit" in str(e):
                self.skipTest(f"复权因子接口限制: {e}")
            else:
                raise

    def test_plate_list(self):
        """测试获取板块列表"""
        print("\n5️⃣ 测试获取港股板块列表")
        
        # 获取所有板块
        all_plates = self.client.quote.get_plate_list("HK", "ALL")
        self.assertIsInstance(all_plates, list)
        self.assertGreater(len(all_plates), 100)
        print(f"   ✓ 港股板块总数: {len(all_plates)}")
        
        # 获取行业板块
        industry_plates = self.client.quote.get_plate_list("HK", "INDUSTRY")
        self.assertIsInstance(industry_plates, list)
        self.assertGreater(len(industry_plates), 50)
        print(f"   ✓ 行业板块数: {len(industry_plates)}")

    def test_plate_stock(self):
        """测试获取板块下的股票"""
        print("\n6️⃣ 测试获取板块下的股票")
        
        test_plate_code = "HK.BK1001"  # 乳制品板块
        stocks = self.client.quote.get_plate_stock(test_plate_code)
        
        self.assertIsInstance(stocks, list)
        print(f"   ✓ 板块 {test_plate_code} 包含 {len(stocks)} 只股票")
        
        if stocks:
            for stock in stocks[:3]:
                self.assertIsInstance(stock, PlateStock)
                print(f"   📈 {stock.code} - {stock.stock_name}")

    def test_comprehensive_analysis(self):
        """测试综合应用：分析科技板块"""
        print("\n7️⃣ 测试综合应用：分析科技板块")
        
        tech_plate_code = "HK.BK1046"  # 消费电子产品板块
        
        # 获取板块股票
        stocks = self.client.quote.get_plate_stock(tech_plate_code)
        self.assertIsInstance(stocks, list)
        
        if stocks:
            stock_codes = [stock.code for stock in stocks[:5]]  # 前5只
            
            # 获取市场快照
            snapshots = self.client.quote.get_market_snapshot(stock_codes)
            self.assertIsInstance(snapshots, list)
            self.assertEqual(len(snapshots), len(stock_codes))
            
            print("   板块主要股票表现:")
            for snapshot in snapshots:
                change_pct = ((snapshot.last_price / snapshot.prev_close_price - 1) * 100)
                status = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "📊"
                print(f"   {status} {snapshot.code}: {snapshot.last_price:.2f} ({change_pct:+.2f}%)")
            
            print(f"   ✓ 成功分析 {len(snapshots)} 只股票")


if __name__ == "__main__":
    if not is_futu_available():
        print("❌ 富途API环境不可用")
        sys.exit(1)
    
    unittest.main(verbosity=2) 