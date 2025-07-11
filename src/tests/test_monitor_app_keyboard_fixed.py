#!/usr/bin/env python3
"""
测试MonitorApp分组光标移动功能的修复
验证k/l键不再出现"No cell exists"错误
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor_app import MonitorApp
from textual.widgets import DataTable
from base.monitor import ConnectionStatus, MarketStatus


class TestMonitorAppKeyboardFixed(unittest.TestCase):
    """测试分组光标移动功能的修复"""
    
    def setUp(self):
        """设置测试环境"""
        self.app = MonitorApp()
        
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self.app, 'futu_market') and self.app.futu_market:
            try:
                self.app.futu_market.close()
            except:
                pass
    
    @patch('monitor_app.ConfigManager')
    @patch('monitor_app.FutuMarket')
    async def test_group_cursor_movement_with_empty_table(self, mock_futu_market, mock_config):
        """测试空表格时的光标移动不会出错"""
        # 模拟配置管理器
        mock_config.return_value._config_data = {
            'monitored_stocks': {'stock_0': 'HK.00700'}
        }
        
        # 模拟富途市场
        mock_futu_instance = MagicMock()
        mock_futu_market.return_value = mock_futu_instance
        mock_futu_instance.client.connect.return_value = True
        mock_futu_instance.get_user_security_group.return_value = None  # 返回空数据
        
        # 模拟表格组件
        mock_group_table = MagicMock(spec=DataTable)
        mock_group_table.cursor_type = "row"
        mock_group_table.show_cursor = True
        mock_group_table.move_cursor = MagicMock()
        mock_group_table.clear = MagicMock()
        mock_group_table.add_row = MagicMock()
        
        # 模拟其他UI组件
        mock_group_stocks_content = MagicMock()
        mock_group_stocks_content.update = MagicMock()
        
        # 设置应用的组件引用
        self.app.group_table = mock_group_table
        self.app.group_stocks_content = mock_group_stocks_content
        self.app.group_data = []  # 空的分组数据
        self.app.current_group_cursor = 0
        
        # 测试k键（向上移动）- 应该不会出错
        try:
            await self.app.action_group_cursor_up()
            # 验证没有异常抛出
            self.assertTrue(True, "k键操作成功，没有抛出异常")
        except Exception as e:
            self.fail(f"k键操作失败: {e}")
        
        # 测试l键（向下移动）- 应该不会出错
        try:
            await self.app.action_group_cursor_down()
            # 验证没有异常抛出
            self.assertTrue(True, "l键操作成功，没有抛出异常")
        except Exception as e:
            self.fail(f"l键操作失败: {e}")
    
    @patch('monitor_app.ConfigManager')
    @patch('monitor_app.FutuMarket')
    async def test_group_cursor_movement_with_data(self, mock_futu_market, mock_config):
        """测试有数据时的光标移动正常工作"""
        # 模拟配置管理器
        mock_config.return_value._config_data = {
            'monitored_stocks': {'stock_0': 'HK.00700'}
        }
        
        # 模拟富途市场
        mock_futu_instance = MagicMock()
        mock_futu_market.return_value = mock_futu_instance
        mock_futu_instance.client.connect.return_value = True
        
        # 模拟表格组件
        mock_group_table = MagicMock(spec=DataTable)
        mock_group_table.cursor_type = "row"
        mock_group_table.show_cursor = True
        mock_group_table.move_cursor = MagicMock()
        mock_group_table.clear = MagicMock()
        mock_group_table.add_row = MagicMock()
        
        # 模拟其他UI组件
        mock_group_stocks_content = MagicMock()
        mock_group_stocks_content.update = MagicMock()
        
        # 设置应用的组件引用
        self.app.group_table = mock_group_table
        self.app.group_stocks_content = mock_group_stocks_content
        
        # 设置测试数据
        self.app.group_data = [
            {'name': '测试分组1', 'stock_count': 5, 'type': 'CUSTOM'},
            {'name': '测试分组2', 'stock_count': 3, 'type': 'CUSTOM'},
            {'name': '测试分组3', 'stock_count': 7, 'type': 'CUSTOM'}
        ]
        self.app.current_group_cursor = 0
        
        # 测试向下移动
        await self.app.action_group_cursor_down()
        self.assertEqual(self.app.current_group_cursor, 1)
        mock_group_table.move_cursor.assert_called_with(row=1, column=0, animate=False, scroll=True)
        
        # 测试向上移动
        await self.app.action_group_cursor_up()
        self.assertEqual(self.app.current_group_cursor, 0)
        mock_group_table.move_cursor.assert_called_with(row=0, column=0, animate=False, scroll=True)
        
        # 测试循环移动（从第一项向上）
        await self.app.action_group_cursor_up()
        self.assertEqual(self.app.current_group_cursor, 2)  # 应该循环到最后一项
        mock_group_table.move_cursor.assert_called_with(row=2, column=0, animate=False, scroll=True)
    
    async def test_update_group_cursor_bounds_checking(self):
        """测试光标位置边界检查"""
        # 模拟表格组件
        mock_group_table = MagicMock(spec=DataTable)
        mock_group_table.move_cursor = MagicMock()
        
        # 模拟其他UI组件
        mock_group_stocks_content = MagicMock()
        mock_group_stocks_content.update = MagicMock()
        
        # 设置应用的组件引用
        self.app.group_table = mock_group_table
        self.app.group_stocks_content = mock_group_stocks_content
        
        # 测试数据
        self.app.group_data = [
            {'name': '分组1', 'stock_count': 1, 'type': 'CUSTOM'},
            {'name': '分组2', 'stock_count': 2, 'type': 'CUSTOM'}
        ]
        
        # 测试负数光标位置的修正
        self.app.current_group_cursor = -1
        await self.app._update_group_cursor()
        self.assertEqual(self.app.current_group_cursor, 0)
        
        # 测试超出范围光标位置的修正
        self.app.current_group_cursor = 5  # 超出范围
        await self.app._update_group_cursor()
        self.assertEqual(self.app.current_group_cursor, 1)  # 应该修正为最后一个有效索引
    
    async def test_update_group_preview(self):
        """测试分组预览更新功能"""
        # 模拟UI组件
        mock_group_stocks_content = MagicMock()
        mock_group_stocks_content.update = MagicMock()
        
        self.app.group_stocks_content = mock_group_stocks_content
        
        # 测试数据
        self.app.group_data = [
            {'name': '我的分组', 'stock_count': 5, 'type': 'CUSTOM'}
        ]
        self.app.current_group_cursor = 0
        
        # 执行预览更新
        await self.app._update_group_preview()
        
        # 验证预览内容已更新
        mock_group_stocks_content.update.assert_called_once()
        call_args = mock_group_stocks_content.update.call_args[0][0]
        self.assertIn('我的分组', call_args)
        self.assertIn('股票数量: 5', call_args)
        self.assertIn('分组类型: CUSTOM', call_args)


async def run_tests():
    """异步运行测试"""
    suite = unittest.TestSuite()
    
    # 添加测试方法
    test_methods = [
        'test_group_cursor_movement_with_empty_table',
        'test_group_cursor_movement_with_data',
        'test_update_group_cursor_bounds_checking',
        'test_update_group_preview'
    ]
    
    for method in test_methods:
        suite.addTest(TestMonitorAppKeyboardFixed(method))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # 在事件循环中运行异步测试
    success = asyncio.run(run_tests())
    exit(0 if success else 1) 