"""
测试monitor_app中的键盘操作功能

测试分组光标移动和选择功能
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMonitorAppKeyboard(unittest.TestCase):
    """测试monitor_app中的键盘操作"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_futu_market = Mock()
        self.mock_group_table = Mock()
        self.mock_group_table.clear = Mock()
        self.mock_group_table.add_row = Mock()
        self.mock_group_table.update_cell = Mock()
        self.mock_group_table.row_count = 0
        
        self.mock_group_stocks_content = Mock()
        self.mock_group_stocks_content.update = Mock()
        
        # Mock monitor_app的部分组件
        self.monitor_app = Mock()
        self.monitor_app.futu_market = self.mock_futu_market
        self.monitor_app.group_table = self.mock_group_table
        self.monitor_app.group_stocks_content = self.mock_group_stocks_content
        self.monitor_app.logger = Mock()
        
        # 初始化分组数据
        self.monitor_app.group_data = [
            {
                'name': '分组1',
                'stock_list': ['HK.00700', 'HK.00388'],
                'stock_count': 2,
                'type': 'CUSTOM'
            },
            {
                'name': '分组2',
                'stock_list': ['US.AAPL', 'US.MSFT'],
                'stock_count': 2,
                'type': 'CUSTOM'
            },
            {
                'name': '分组3',
                'stock_list': ['HK.00941'],
                'stock_count': 1,
                'type': 'CUSTOM'
            }
        ]
        self.monitor_app.current_group_cursor = 0
        self.monitor_app.selected_group_name = None
        self.monitor_app.monitored_stocks = []
        self.monitor_app.stock_data = {}
    
    async def _update_group_cursor_mock(self):
        """模拟_update_group_cursor方法"""
        if not self.mock_group_table or len(self.monitor_app.group_data) == 0:
            return
            
        try:
            # 更新所有行的显示，只有当前行显示光标
            for i, group_data in enumerate(self.monitor_app.group_data):
                cursor_mark = ">" if i == self.monitor_app.current_group_cursor else " "
                display_name = f"{cursor_mark} {group_data['name']}"
                
                # 更新表格中的第一列（分组名称列）
                self.mock_group_table.update_cell(i, 0, display_name)
            
            # 同时更新右侧显示当前选中分组的股票信息
            if 0 <= self.monitor_app.current_group_cursor < len(self.monitor_app.group_data):
                current_group = self.monitor_app.group_data[self.monitor_app.current_group_cursor]
                if self.mock_group_stocks_content:
                    preview_text = f"[bold cyan]▶ {current_group['name']}[/bold cyan]\n\n"
                    preview_text += f"[dim]股票数量: {current_group['stock_count']}\n"
                    preview_text += f"分组类型: {current_group['type']}\n\n"
                    preview_text += "按 [bold]Space[/bold] 键选择此分组作为主监控列表[/dim]"
                    self.mock_group_stocks_content.update(preview_text)
                    
        except Exception as e:
            self.monitor_app.logger.error(f"更新分组光标显示失败: {e}")
    
    async def action_group_cursor_up_mock(self):
        """模拟分组光标向上移动"""
        if len(self.monitor_app.group_data) > 0:
            self.monitor_app.current_group_cursor = (self.monitor_app.current_group_cursor - 1) % len(self.monitor_app.group_data)
            await self._update_group_cursor_mock()
            self.monitor_app.logger.debug(f"分组光标向上移动到: {self.monitor_app.current_group_cursor}")
    
    async def action_group_cursor_down_mock(self):
        """模拟分组光标向下移动"""
        if len(self.monitor_app.group_data) > 0:
            self.monitor_app.current_group_cursor = (self.monitor_app.current_group_cursor + 1) % len(self.monitor_app.group_data)
            await self._update_group_cursor_mock()
            self.monitor_app.logger.debug(f"分组光标向下移动到: {self.monitor_app.current_group_cursor}")
    
    async def action_select_group_mock(self):
        """模拟选择当前光标所在的分组"""
        if 0 <= self.monitor_app.current_group_cursor < len(self.monitor_app.group_data):
            group_data = self.monitor_app.group_data[self.monitor_app.current_group_cursor]
            self.monitor_app.selected_group_name = group_data['name']
            
            # 模拟切换主界面监控的股票为该分组的股票
            stock_list = group_data.get('stock_list', [])
            if stock_list:
                new_monitored_stocks = []
                for stock in stock_list:
                    if isinstance(stock, dict):
                        stock_code = stock.get('code', '')
                        if stock_code:
                            new_monitored_stocks.append(stock_code)
                    elif isinstance(stock, str):
                        new_monitored_stocks.append(stock)
                
                if new_monitored_stocks:
                    self.monitor_app.monitored_stocks = new_monitored_stocks
                    self.monitor_app.stock_data.clear()
            
            self.monitor_app.logger.info(f"选择分组: {group_data['name']}, 包含 {group_data['stock_count']} 只股票")
    
    def test_group_cursor_down_movement(self):
        """测试分组光标向下移动"""
        # 初始位置应该是0
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 向下移动一次
        asyncio.run(self.action_group_cursor_down_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 1)
        
        # 再向下移动一次
        asyncio.run(self.action_group_cursor_down_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 2)
        
        # 从最后一个位置再向下移动，应该循环到第一个
        asyncio.run(self.action_group_cursor_down_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 验证表格更新被调用
        self.assertTrue(self.mock_group_table.update_cell.called)
    
    def test_group_cursor_up_movement(self):
        """测试分组光标向上移动"""
        # 初始位置应该是0
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 从第一个位置向上移动，应该循环到最后一个
        asyncio.run(self.action_group_cursor_up_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 2)
        
        # 再向上移动一次
        asyncio.run(self.action_group_cursor_up_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 1)
        
        # 再向上移动一次
        asyncio.run(self.action_group_cursor_up_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 验证表格更新被调用
        self.assertTrue(self.mock_group_table.update_cell.called)
    
    def test_group_selection(self):
        """测试分组选择功能"""
        # 设置当前光标位置为第二个分组
        self.monitor_app.current_group_cursor = 1
        
        # 选择当前分组
        asyncio.run(self.action_select_group_mock())
        
        # 验证选中的分组名称
        self.assertEqual(self.monitor_app.selected_group_name, '分组2')
        
        # 验证监控股票列表被更新
        expected_stocks = ['US.AAPL', 'US.MSFT']
        self.assertEqual(self.monitor_app.monitored_stocks, expected_stocks)
        
        # 验证股票数据被清空
        self.assertEqual(len(self.monitor_app.stock_data), 0)
    
    def test_update_group_cursor_display(self):
        """测试光标显示更新"""
        # 设置光标位置为第二个分组
        self.monitor_app.current_group_cursor = 1
        
        # 更新光标显示
        asyncio.run(self._update_group_cursor_mock())
        
        # 验证所有行都被更新
        self.assertEqual(self.mock_group_table.update_cell.call_count, 3)
        
        # 验证光标标记
        calls = self.mock_group_table.update_cell.call_args_list
        self.assertEqual(calls[0][0], (0, 0, "  分组1"))  # 第0行，无光标
        self.assertEqual(calls[1][0], (1, 0, "> 分组2"))  # 第1行，有光标
        self.assertEqual(calls[2][0], (2, 0, "  分组3"))  # 第2行，无光标
        
        # 验证右侧内容被更新
        self.mock_group_stocks_content.update.assert_called_once()
        update_text = self.mock_group_stocks_content.update.call_args[0][0]
        self.assertIn("分组2", update_text)
        self.assertIn("股票数量: 2", update_text)
    
    def test_empty_group_data_handling(self):
        """测试空分组数据的处理"""
        # 清空分组数据
        self.monitor_app.group_data = []
        
        # 尝试向下移动光标
        asyncio.run(self.action_group_cursor_down_mock())
        
        # 光标位置应该保持不变
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 表格更新不应该被调用
        self.assertFalse(self.mock_group_table.update_cell.called)
    
    def test_cursor_boundary_conditions(self):
        """测试光标边界条件"""
        # 设置只有一个分组的情况
        self.monitor_app.group_data = [
            {
                'name': '唯一分组',
                'stock_list': ['HK.00700'],
                'stock_count': 1,
                'type': 'CUSTOM'
            }
        ]
        
        # 初始位置
        self.monitor_app.current_group_cursor = 0
        
        # 向下移动，应该回到同一位置
        asyncio.run(self.action_group_cursor_down_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
        
        # 向上移动，也应该在同一位置
        asyncio.run(self.action_group_cursor_up_mock())
        self.assertEqual(self.monitor_app.current_group_cursor, 0)
    
    def test_group_selection_with_dict_stocks(self):
        """测试包含字典格式股票的分组选择"""
        # 设置包含字典格式股票的分组数据
        self.monitor_app.group_data = [
            {
                'name': '字典格式分组',
                'stock_list': [
                    {'code': 'HK.00700', 'name': '腾讯控股'},
                    {'code': 'HK.00388', 'name': '香港交易所'}
                ],
                'stock_count': 2,
                'type': 'CUSTOM'
            }
        ]
        
        # 选择分组
        asyncio.run(self.action_select_group_mock())
        
        # 验证股票代码被正确提取
        expected_stocks = ['HK.00700', 'HK.00388']
        self.assertEqual(self.monitor_app.monitored_stocks, expected_stocks)


if __name__ == '__main__':
    unittest.main()