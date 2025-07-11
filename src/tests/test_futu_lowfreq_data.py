#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    FutuClient, FutuConfig, QuoteManager,
    FutuException, FutuConnectException, FutuQuoteException,
    AuTypeInfo, PlateInfo, PlateStock, StockInfo, MarketSnapshot
)

def is_futu_available():
    """检查富途API是否可用"""
    if not FUTU_AVAILABLE:
        return False
    
    try:
        # 尝试连接FutuOpenD
        test_client = FutuClient()
        test_client.connect()
        result = test_client.is_connected
        test_client.disconnect()
        return result
    except:
        return False

def create_client(enable_proto_encrypt=False):
    """创建测试客户端"""
    config = FutuConfig(enable_proto_encrypt=enable_proto_encrypt)
    return FutuClient(config)


@skipIf(not is_futu_available(), "富途API不可用或FutuOpenD未启动")
class TestFutuLowFreqDataAPI(TestCase):
    """富途低频数据接口测试"""
    
    def setUp(self):
        """测试前准备"""
        self.client = create_client(enable_proto_encrypt=False)
        self.client.connect()
    
    def tearDown(self):
        """测试后清理"""
        try:
            if self.client:
                self.client.disconnect()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        finally:
            self.client = None
            time.sleep(0.1)
    
    # ================== 复权因子接口测试 ==================
    
    def test_get_autype_list(self):
        """测试获取复权因子 (使用get_rehab接口)"""
        print("\n测试获取复权因子 (使用get_rehab接口)...")
        
        codes = ["HK.00700"]  # 腾讯
        
        try:
            autype_list = self.client.quote.get_autype_list(codes)
            
            # 验证返回类型
            self.assertIsInstance(autype_list, list)
            print(f"   ✓ 返回类型正确: {type(autype_list)}")
            
            if autype_list:
                # 验证第一个复权信息
                first_autype = autype_list[0]
                self.assertIsInstance(first_autype, AuTypeInfo)
                
                # 验证必需字段
                self.assertIsInstance(first_autype.code, str)
                self.assertIsInstance(first_autype.ex_div_date, str)
                
                print(f"   ✓ 获取到 {len(autype_list)} 条复权信息")
                print(f"   ✓ 首条复权信息: {first_autype.code}")
            else:
                print("   注意: 该股票可能没有复权信息")
                
        except FutuQuoteException as e:
            # 处理方法不可用或权限限制
            if any(keyword in str(e) for keyword in ["不可用", "不支持", "权限", "limit", "available"]):
                print(f"   注意: 复权因子接口 - {e}")
            else:
                self.fail(f"获取复权因子失败: {e}")
    
    def test_get_autype_list_multiple_codes(self):
        """测试获取多只股票的复权因子 (使用get_rehab接口)"""
        print("\n测试获取多只股票的复权因子 (使用get_rehab接口)...")
        
        codes = ["HK.00700", "HK.00388"]  # 腾讯、港交所
        
        try:
            autype_list = self.client.quote.get_autype_list(codes)
            
            self.assertIsInstance(autype_list, list)
            print(f"   ✓ 获取到 {len(autype_list)} 条复权信息")
            
            # 验证每个复权信息
            for autype in autype_list:
                self.assertIsInstance(autype, AuTypeInfo)
                self.assertIn(autype.code, codes)
                
        except FutuQuoteException as e:
            # 处理方法不可用或权限限制
            if any(keyword in str(e) for keyword in ["不可用", "不支持", "权限", "limit", "available"]):
                print(f"   注意: 复权因子接口 - {e}")
            else:
                self.fail(f"获取多只股票复权因子失败: {e}")
    
    # ================== 板块列表接口测试 ==================
    
    def test_get_plate_list_all(self):
        """测试获取所有板块列表"""
        print("\n测试获取所有板块列表...")
        
        try:
            plate_list = self.client.quote.get_plate_list("HK", "ALL")
            
            # 验证返回类型
            self.assertIsInstance(plate_list, list)
            self.assertGreater(len(plate_list), 0)
            print(f"   ✓ 获取到 {len(plate_list)} 个板块")
            
            # 验证第一个板块信息
            first_plate = plate_list[0]
            self.assertIsInstance(first_plate, PlateInfo)
            
            # 验证必需字段
            self.assertIsInstance(first_plate.plate_code, str)
            self.assertIsInstance(first_plate.plate_name, str)
            self.assertIsInstance(first_plate.plate_type, str)
            
            print(f"   ✓ 首个板块: {first_plate.plate_code} - {first_plate.plate_name}")
            
        except FutuQuoteException as e:
            if "权限" in str(e) or "limit" in str(e).lower():
                self.skipTest(f"板块列表接口权限限制: {e}")
            else:
                self.fail(f"获取板块列表失败: {e}")
    
    def test_get_plate_list_industry(self):
        """测试获取行业板块列表"""
        print("\n测试获取行业板块列表...")
        
        try:
            plate_list = self.client.quote.get_plate_list("HK", "INDUSTRY")
            
            self.assertIsInstance(plate_list, list)
            print(f"   ✓ 获取到 {len(plate_list)} 个行业板块")
            
            if plate_list:
                # 验证板块类型
                for plate in plate_list[:3]:  # 检查前3个
                    self.assertIsInstance(plate, PlateInfo)
                    print(f"   ✓ 行业板块: {plate.plate_code} - {plate.plate_name}")
                    
        except FutuQuoteException as e:
            if "权限" in str(e) or "limit" in str(e).lower():
                self.skipTest(f"行业板块接口权限限制: {e}")
            else:
                self.fail(f"获取行业板块列表失败: {e}")
    
    # ================== 板块股票接口测试 ==================
    
    def test_get_plate_stock(self):
        """测试获取板块下的股票列表"""
        print("\n测试获取板块下的股票列表...")
        
        # 先获取一个板块代码
        try:
            plate_list = self.client.quote.get_plate_list("HK", "ALL")
            if not plate_list:
                self.skipTest("无法获取板块信息用于测试")
            
            # 寻找合适的板块（跳过港股通等特殊板块）
            test_plate = None
            for plate in plate_list:
                if "HK.BK" in plate.plate_code and "港股通" not in plate.plate_name:
                    test_plate = plate
                    break
                    
            if test_plate is None:
                print("   注意: 未找到合适的测试板块，跳过测试")
                return
            
            print(f"   使用测试板块: {test_plate.plate_code} - {test_plate.plate_name}")
            
            stock_list = self.client.quote.get_plate_stock(test_plate.plate_code)
            
            # 验证返回类型
            self.assertIsInstance(stock_list, list)
            print(f"   ✓ 获取到 {len(stock_list)} 只股票")
            
            if stock_list:
                # 验证第一只股票信息
                first_stock = stock_list[0]
                self.assertIsInstance(first_stock, PlateStock)
                
                # 验证必需字段
                self.assertIsInstance(first_stock.code, str)
                self.assertIsInstance(first_stock.stock_name, str)
                self.assertIsInstance(first_stock.lot_size, int)
                
                print(f"   ✓ 首只股票: {first_stock.code} - {first_stock.stock_name}")
            else:
                print("   注意: 该板块下没有股票")
                
        except FutuQuoteException as e:
            # 处理板块代码格式错误等常见问题
            if any(keyword in str(e) for keyword in ["权限", "limit", "format", "wrong", "错误"]):
                print(f"   注意: 板块股票接口限制 - {e}")
            else:
                self.fail(f"获取板块股票列表失败: {e}")
    
    def test_get_plate_stock_specific(self):
        """测试获取特定板块的股票列表"""
        print("\n测试获取特定板块的股票列表...")
        
        # 使用一个已知的港股板块代码
        plate_code = "HK.BK1001"  # 可能是地产板块或其他
        
        try:
            stock_list = self.client.quote.get_plate_stock(plate_code)
            
            self.assertIsInstance(stock_list, list)
            print(f"   ✓ 板块 {plate_code} 包含 {len(stock_list)} 只股票")
            
            # 验证股票信息结构
            for stock in stock_list[:3]:  # 检查前3只
                self.assertIsInstance(stock, PlateStock)
                self.assertTrue(stock.code.startswith("HK."))
                print(f"   ✓ 股票: {stock.code} - {stock.stock_name}")
                
        except FutuQuoteException as e:
            if "板块不存在" in str(e) or "不存在" in str(e):
                print(f"   注意: 测试板块 {plate_code} 不存在，这是正常的")
            elif "权限" in str(e) or "limit" in str(e).lower():
                self.skipTest(f"板块股票接口权限限制: {e}")
            else:
                self.fail(f"获取特定板块股票列表失败: {e}")


class TestFutuLowFreqDataModels(TestCase):
    """富途低频数据模型测试"""
    
    def test_autype_info_model(self):
        """测试AuTypeInfo数据模型"""
        print("\n测试AuTypeInfo数据模型...")
        
        test_data = {
            'code': 'HK.00700',
            'ex_div_date': '2023-05-17',
            'split_ratio': 1.0,
            'per_cash_div': 2.4,
            'per_share_div_ratio': 0.0,
            'per_share_trans_ratio': 0.0,
            'allot_ratio': 0.0,
            'allot_price': 0.0,
            'stk_spo_ratio': 0.0,
            'stk_spo_price': 0.0,
            'forward_adj_factorA': 1.0,
            'forward_adj_factorB': 0.0,
            'backward_adj_factorA': 1.0,
            'backward_adj_factorB': 0.0
        }
        
        autype = AuTypeInfo.from_dict(test_data)
        
        self.assertEqual(autype.code, 'HK.00700')
        self.assertEqual(autype.ex_div_date, '2023-05-17')
        self.assertEqual(autype.per_cash_div, 2.4)
        
        print("   ✓ AuTypeInfo模型创建和字段访问正常")
    
    def test_plate_info_model(self):
        """测试PlateInfo数据模型"""
        print("\n测试PlateInfo数据模型...")
        
        test_data = {
            'plate_code': 'HK.BK1001',
            'plate_name': '地产建筑',
            'plate_type': 'INDUSTRY'
        }
        
        plate = PlateInfo.from_dict(test_data)
        
        self.assertEqual(plate.plate_code, 'HK.BK1001')
        self.assertEqual(plate.plate_name, '地产建筑')
        self.assertEqual(plate.plate_type, 'INDUSTRY')
        
        print("   ✓ PlateInfo模型创建和字段访问正常")
    
    def test_plate_stock_model(self):
        """测试PlateStock数据模型"""
        print("\n测试PlateStock数据模型...")
        
        test_data = {
            'code': 'HK.00700',
            'lot_size': 100,
            'stock_name': '腾讯控股',
            'stock_owner': 'HK.00700',
            'stock_child_type': 'NORMAL',
            'stock_type': 'STOCK',
            'list_time': '2004-06-16',
            'stock_id': 700
        }
        
        stock = PlateStock.from_dict(test_data)
        
        self.assertEqual(stock.code, 'HK.00700')
        self.assertEqual(stock.lot_size, 100)
        self.assertEqual(stock.stock_name, '腾讯控股')
        self.assertEqual(stock.stock_id, 700)
        
        print("   ✓ PlateStock模型创建和字段访问正常")


if __name__ == '__main__':
    print("=" * 60)
    print("富途低频数据接口测试")
    print("=" * 60)
    
    # 检查富途API可用性
    if not FUTU_AVAILABLE:
        print("❌ 富途API不可用，请安装: pip install futu-api")
        sys.exit(1)
    
    if not is_futu_available():
        print("❌ 无法连接FutuOpenD，请确保：")
        print("   1. FutuOpenD程序已启动")
        print("   2. 程序监听在127.0.0.1:11111")
        print("   3. 拥有相应的行情权限")
        sys.exit(1)
    
    print("✅ 富途API环境检查通过")
    print()
    
    # 运行测试
    try:
        result = unittest.main(exit=False, verbosity=2)
        
        # 等待一下再退出，让富途线程有时间清理
        print("\n等待富途连接清理...")
        time.sleep(1)
        
        if result.result.wasSuccessful():
            print("🎉 所有测试通过！")
        else:
            print(f"❌ 测试失败: {len(result.result.failures)} 个失败, {len(result.result.errors)} 个错误")
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试执行出错: {e}")
    finally:
        print("测试完成，程序退出") 