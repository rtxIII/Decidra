"""
富途API封装测试用例

测试src/api/futu.py中的所有功能
使用unittest框架，不使用mock
"""

import unittest
import os
import json
import tempfile
import hashlib
from pathlib import Path
from unittest import TestCase

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.futu import (
    FutuConfig, 
    FutuClient, 
    FutuException, 
    FutuConnectException, 
    FutuTradeException, 
    FutuQuoteException,
    create_client
)


class TestFutuConfig(TestCase):
    """FutuConfig配置管理类测试"""
    
    def setUp(self):
        """测试前设置"""
        self.default_config = FutuConfig()
        self.test_password = "test123456"
        self.expected_md5 = hashlib.md5(self.test_password.encode('utf-8')).hexdigest()
    
    def test_default_config(self):
        """测试默认配置"""
        config = FutuConfig()
        
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 11111)
        self.assertEqual(config.default_trd_env, "SIMULATE")
        self.assertEqual(config.timeout, 30)
        self.assertFalse(config.enable_proto_encrypt)
        self.assertEqual(config.log_level, "INFO")
        self.assertTrue(config.auto_reconnect)
        self.assertEqual(config.max_reconnect_attempts, 3)
        self.assertEqual(config.reconnect_interval, 5)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = FutuConfig(
            host="192.168.1.100",
            port=11112,
            trade_pwd=self.test_password,
            default_trd_env="REAL",
            timeout=60
        )
        
        self.assertEqual(config.host, "192.168.1.100")
        self.assertEqual(config.port, 11112)
        self.assertEqual(config.trade_pwd, self.test_password)
        self.assertEqual(config.trade_pwd_md5, self.expected_md5)
        self.assertEqual(config.default_trd_env, "REAL")
        self.assertEqual(config.timeout, 60)
    
    def test_password_md5_generation(self):
        """测试密码MD5生成"""
        config = FutuConfig(trade_pwd=self.test_password)
        self.assertEqual(config.trade_pwd_md5, self.expected_md5)
    
    def test_config_validation(self):
        """测试配置验证"""
        # 测试无效端口
        with self.assertRaises(ValueError):
            FutuConfig(port=0)
        
        with self.assertRaises(ValueError):
            FutuConfig(port=70000)
        
        # 测试无效环境
        with self.assertRaises(ValueError):
            FutuConfig(default_trd_env="INVALID")
        
        # 测试无效超时
        with self.assertRaises(ValueError):
            FutuConfig(timeout=-1)
        
        # 测试无效日志级别
        with self.assertRaises(ValueError):
            FutuConfig(log_level="INVALID")
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        config = FutuConfig(
            host="test_host",
            port=12345,
            trade_pwd="password123"
        )
        
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict['host'], "test_host")
        self.assertEqual(config_dict['port'], 12345)
        self.assertEqual(config_dict['trade_pwd'], "password123")
        self.assertIn('trade_pwd_md5', config_dict)
    
    def test_config_file_operations(self):
        """测试配置文件读写"""
        # 创建临时配置文件
        test_config_data = {
            "futu": {
                "host": "test.example.com",
                "port": 11113,
                "trade_pwd": "test_password",
                "default_trd_env": "REAL",
                "log_level": "DEBUG"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config_data, f)
            temp_file = f.name
        
        try:
            # 测试从文件加载
            config = FutuConfig.from_file(temp_file)
            
            self.assertEqual(config.host, "test.example.com")
            self.assertEqual(config.port, 11113)
            self.assertEqual(config.trade_pwd, "test_password")
            self.assertEqual(config.default_trd_env, "REAL")
            self.assertEqual(config.log_level, "DEBUG")
            
            # 测试保存到文件
            new_temp_file = temp_file + "_new"
            config.save_to_file(new_temp_file)
            
            # 验证保存的文件
            with open(new_temp_file, 'r') as f:
                saved_data = json.load(f)
            
            self.assertIn('futu', saved_data)
            self.assertEqual(saved_data['futu']['host'], "test.example.com")
            
            # 清理
            os.unlink(new_temp_file)
            
        finally:
            os.unlink(temp_file)
    
    def test_config_from_file_not_found(self):
        """测试文件不存在时的异常"""
        with self.assertRaises(FileNotFoundError):
            FutuConfig.from_file("non_existent_file.json")
    
    def test_config_from_env(self):
        """测试从环境变量加载配置"""
        # 设置测试环境变量
        test_env = {
            'FUTU_HOST': 'env.example.com',
            'FUTU_PORT': '11114',
            'FUTU_TRADE_PWD': 'env_password',
            'FUTU_TRD_ENV': 'REAL',
            'FUTU_TIMEOUT': '45',
            'FUTU_ENCRYPT': 'false',
            'FUTU_LOG_LEVEL': 'WARNING'
        }
        
        # 备份原有环境变量
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config = FutuConfig.from_env()
            
            self.assertEqual(config.host, 'env.example.com')
            self.assertEqual(config.port, 11114)
            self.assertEqual(config.trade_pwd, 'env_password')
            self.assertEqual(config.default_trd_env, 'REAL')
            self.assertEqual(config.timeout, 45)
            self.assertFalse(config.enable_proto_encrypt)
            self.assertEqual(config.log_level, 'WARNING')
            
        finally:
            # 恢复原有环境变量
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class TestFutuExceptions(TestCase):
    """富途异常类测试"""
    
    def test_futu_exception(self):
        """测试基础异常"""
        ret_code = -1
        ret_msg = "Test error message"
        detail = "Additional detail"
        
        exception = FutuException(ret_code, ret_msg, detail)
        
        self.assertEqual(exception.ret_code, ret_code)
        self.assertEqual(exception.ret_msg, ret_msg)
        self.assertEqual(exception.detail, detail)
        self.assertIn(str(ret_code), str(exception))
        self.assertIn(ret_msg, str(exception))
        self.assertIn(detail, str(exception))
    
    def test_futu_connect_exception(self):
        """测试连接异常"""
        exception = FutuConnectException(-2, "Connection failed")
        
        self.assertIsInstance(exception, FutuException)
        self.assertEqual(exception.ret_code, -2)
        self.assertEqual(exception.ret_msg, "Connection failed")
    
    def test_futu_trade_exception(self):
        """测试交易异常"""
        exception = FutuTradeException(-3, "Trade error")
        
        self.assertIsInstance(exception, FutuException)
        self.assertEqual(exception.ret_code, -3)
        self.assertEqual(exception.ret_msg, "Trade error")
    
    def test_futu_quote_exception(self):
        """测试行情异常"""
        exception = FutuQuoteException(-4, "Quote error")
        
        self.assertIsInstance(exception, FutuException)
        self.assertEqual(exception.ret_code, -4)
        self.assertEqual(exception.ret_msg, "Quote error")


class TestFutuClient(TestCase):
    """FutuClient客户端测试"""
    
    def setUp(self):
        """测试前设置"""
        self.test_config = FutuConfig(
            host="127.0.0.1",
            port=11111,
            trade_pwd="test123456",
            default_trd_env="SIMULATE"
        )
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        # 使用默认配置
        client = FutuClient()
        self.assertIsInstance(client.config, FutuConfig)
        self.assertFalse(client.is_connected)
        self.assertFalse(client.is_unlocked)
        
        # 使用自定义配置
        client = FutuClient(self.test_config)
        self.assertEqual(client.config, self.test_config)
        
        # 使用kwargs
        client = FutuClient(host="test_host", port=12345)
        self.assertEqual(client.config.host, "test_host")
        self.assertEqual(client.config.port, 12345)
    
    def test_client_properties(self):
        """测试客户端属性"""
        client = FutuClient(self.test_config)
        
        # 初始状态
        self.assertFalse(client.is_connected)
        self.assertFalse(client.is_unlocked)
        
        # 模拟连接状态
        client._connected = True
        self.assertTrue(client.is_connected)
        
        # 模拟解锁状态
        client._unlocked = True
        self.assertTrue(client.is_unlocked)
    
    def test_client_repr(self):
        """测试客户端字符串表示"""
        client = FutuClient(self.test_config)
        repr_str = repr(client)
        
        self.assertIn("FutuClient", repr_str)
        self.assertIn("127.0.0.1:11111", repr_str)
        self.assertIn("disconnected", repr_str)
        self.assertIn("locked", repr_str)
    
    def test_get_trade_context_validation(self):
        """测试获取交易上下文的参数验证"""
        client = FutuClient(self.test_config)
        
        # 未连接时应该抛出异常
        with self.assertRaises(FutuConnectException):
            client._get_trade_context("HK")
        
        # 无效市场代码
        client._connected = True
        with self.assertRaises(ValueError):
            client._get_trade_context("INVALID")
    
    def test_unlock_trade_validation(self):
        """测试解锁交易的参数验证"""
        client = FutuClient()
        
        # 没有密码时应该抛出异常
        with self.assertRaises(ValueError):
            client.unlock_trade()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        # 注意：这个测试不会真正连接，只测试方法调用
        client = FutuClient(self.test_config)
        
        # 模拟__enter__和__exit__方法的存在
        self.assertTrue(hasattr(client, '__enter__'))
        self.assertTrue(hasattr(client, '__exit__'))


class TestCreateClient(TestCase):
    """create_client便利函数测试"""
    
    def test_create_client_default(self):
        """测试默认创建客户端"""
        client = create_client()
        self.assertIsInstance(client, FutuClient)
    
    def test_create_client_with_kwargs(self):
        """测试使用kwargs创建客户端"""
        client = create_client(host="test_host", port=12345)
        self.assertEqual(client.config.host, "test_host")
        self.assertEqual(client.config.port, 12345)
    
    def test_create_client_with_config_file(self):
        """测试使用配置文件创建客户端"""
        # 创建临时配置文件
        test_config_data = {
            "futu": {
                "host": "config_host",
                "port": 11115,
                "trade_pwd": "config_password"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config_data, f)
            temp_file = f.name
        
        try:
            client = create_client(config_file=temp_file)
            self.assertEqual(client.config.host, "config_host")
            self.assertEqual(client.config.port, 11115)
            
            # 测试kwargs覆盖配置文件
            client = create_client(config_file=temp_file, port=99999)
            self.assertEqual(client.config.host, "config_host")  # 来自文件
            self.assertEqual(client.config.port, 99999)  # 被kwargs覆盖
            
        finally:
            os.unlink(temp_file)


class TestFutuClientMethods(TestCase):
    """富途客户端方法测试（不依赖真实连接）"""
    
    def setUp(self):
        """测试前设置"""
        self.client = FutuClient(FutuConfig(
            host="127.0.0.1",
            port=11111,
            trade_pwd="test123456"
        ))
    
    def test_cleanup_connections(self):
        """测试连接清理"""
        # 模拟有连接
        self.client._connected = True
        self.client._unlocked = True
        
        # 调用清理方法
        self.client._cleanup_connections()
        
        # 检查所有上下文是否被清理
        self.assertIsNone(self.client._quote_ctx)
        self.assertIsNone(self.client._trade_hk_ctx)
        self.assertIsNone(self.client._trade_us_ctx)
        self.assertIsNone(self.client._trade_cn_ctx)
    
    def test_disconnect(self):
        """测试断开连接"""
        # 模拟连接状态
        self.client._connected = True
        self.client._unlocked = True
        
        # 断开连接
        self.client.disconnect()
        
        # 检查状态
        self.assertFalse(self.client._connected)
        self.assertFalse(self.client._unlocked)


class TestConfigEdgeCases(TestCase):
    """配置边界情况测试"""
    
    def test_invalid_json_file(self):
        """测试无效JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                FutuConfig.from_file(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_empty_config_file(self):
        """测试空配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            temp_file = f.name
        
        try:
            config = FutuConfig.from_file(temp_file)
            # 应该使用默认值
            self.assertEqual(config.host, "127.0.0.1")
            self.assertEqual(config.port, 11111)
        finally:
            os.unlink(temp_file)
    
    def test_partial_config_file(self):
        """测试部分配置文件"""
        test_config_data = {
            "futu": {
                "host": "partial_host"
                # 缺少其他配置
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config_data, f)
            temp_file = f.name
        
        try:
            config = FutuConfig.from_file(temp_file)
            # 指定的配置应该被加载
            self.assertEqual(config.host, "partial_host")
            # 其他配置应该使用默认值
            self.assertEqual(config.port, 11111)
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    
    # 加载所有测试类
    test_classes = [
        TestFutuConfig,
        TestFutuExceptions,
        TestFutuClient,
        TestCreateClient,
        TestFutuClientMethods,
        TestConfigEdgeCases
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
    print(f"测试完成: 运行 {result.testsRun} 个测试")
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