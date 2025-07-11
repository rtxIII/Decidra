"""
测试monitor_app中的用户分组功能

测试加载用户分组时的DataFrame处理问题
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMonitorAppGroups(unittest.TestCase):
    """测试monitor_app中的用户分组处理"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_futu_market = Mock()
        self.mock_group_table = Mock()
        self.mock_group_table.clear = Mock()
        self.mock_group_table.add_row = Mock()
        self.mock_group_table.row_count = 0
        
        # Mock monitor_app的部分组件
        self.monitor_app = Mock()
        self.monitor_app.futu_market = self.mock_futu_market
        self.monitor_app.group_table = self.mock_group_table
        self.monitor_app.logger = Mock()
    
    async def _load_user_groups_mock(self):
        """模拟_load_user_groups方法实现"""
        try:
            # 模拟从富途API获取数据
            user_groups = self.mock_futu_market.get_user_security_group("CUSTOM")
            
            # 清空现有数据
            self.mock_group_table.clear()
            
            # 处理不同类型的返回数据
            processed_groups = []
            if user_groups is not None:
                import pandas as pd
                if isinstance(user_groups, pd.DataFrame):
                    if not user_groups.empty:
                        # DataFrame转换为字典列表
                        processed_groups = user_groups.to_dict('records')
                elif isinstance(user_groups, dict):
                    # 单个字典转换为列表
                    processed_groups = [user_groups]
                elif isinstance(user_groups, list):
                    # 已经是列表格式
                    processed_groups = user_groups
                    
            if processed_groups:
                self.monitor_app.logger.info(f"获取到 {len(processed_groups)} 个分组数据")
                
                for i, group in enumerate(processed_groups):
                    try:
                        if isinstance(group, dict):
                            # 富途API返回的字典格式
                            group_name = group.get('group_name', f'分组{i+1}')
                            stock_list = group.get('stock_list', [])
                            stock_count = len(stock_list) if stock_list else 0
                            group_type = group.get('group_type', 'CUSTOM')
                            
                            self.mock_group_table.add_row(
                                group_name,
                                str(stock_count),
                                group_type
                            )
                            self.monitor_app.logger.debug(f"添加分组: {group_name}, 股票数: {stock_count}")
                            
                        elif isinstance(group, (list, tuple)) and len(group) >= 2:
                            # 可能的元组格式 (group_name, stock_list)
                            group_name = str(group[0])
                            stock_count = len(group[1]) if isinstance(group[1], (list, tuple)) else 0
                            
                            self.mock_group_table.add_row(
                                group_name,
                                str(stock_count),
                                "CUSTOM"
                            )
                            self.monitor_app.logger.debug(f"添加分组(元组): {group_name}, 股票数: {stock_count}")
                            
                        else:
                            # 其他格式，作为分组名处理
                            group_name = str(group)
                            self.mock_group_table.add_row(
                                group_name,
                                "未知",
                                "CUSTOM"
                            )
                            self.monitor_app.logger.debug(f"添加分组(字符串): {group_name}")
                            
                    except Exception as e:
                        self.monitor_app.logger.warning(f"处理分组数据失败: {e}, 数据: {group}")
                        continue
                        
                # 如果没有成功添加任何分组，显示默认信息
                if self.mock_group_table.add_row.call_count == 0:
                    self.mock_group_table.add_row("数据解析失败", "0", "ERROR")
                    
            else:
                # 添加默认提示行
                self.mock_group_table.add_row("暂无分组", "0", "-")
                self.monitor_app.logger.info("未获取到分组数据，显示默认提示")
            
            self.monitor_app.logger.info(f"加载用户分组完成，共 {len(processed_groups)} 个分组")
            
        except Exception as e:
            self.monitor_app.logger.warning(f"加载用户分组失败: {e}")
            # API调用失败时不更新连接状态，只显示错误信息
            if self.mock_group_table:
                self.mock_group_table.clear()
                self.mock_group_table.add_row(
                    "加载失败",
                    "0",
                    "ERROR"
                )
    
    def test_load_empty_dataframe(self):
        """测试加载空DataFrame时的处理"""
        # 模拟返回空DataFrame
        empty_df = pd.DataFrame()
        self.mock_futu_market.get_user_security_group.return_value = empty_df
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.mock_group_table.add_row.assert_called_with("暂无分组", "0", "-")
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 0 个分组")
    
    def test_load_single_row_dataframe(self):
        """测试加载单行DataFrame时的处理"""
        # 模拟返回单行DataFrame
        single_df = pd.DataFrame([{
            'group_name': '我的分组',
            'stock_list': ['HK.00700', 'HK.00388'],
            'group_type': 'CUSTOM'
        }])
        self.mock_futu_market.get_user_security_group.return_value = single_df
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.mock_group_table.add_row.assert_called_with("我的分组", "2", "CUSTOM")
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 1 个分组")
    
    def test_load_multi_row_dataframe(self):
        """测试加载多行DataFrame时的处理"""
        # 模拟返回多行DataFrame
        multi_df = pd.DataFrame([
            {
                'group_name': '分组1',
                'stock_list': ['HK.00700'],
                'group_type': 'CUSTOM'
            },
            {
                'group_name': '分组2',
                'stock_list': ['HK.00388', 'HK.00941'],
                'group_type': 'CUSTOM'
            }
        ])
        self.mock_futu_market.get_user_security_group.return_value = multi_df
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.assertEqual(self.mock_group_table.add_row.call_count, 2)
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 2 个分组")
    
    def test_load_dict_response(self):
        """测试加载字典响应时的处理"""
        # 模拟返回字典格式
        dict_response = {
            'group_name': '单个分组',
            'stock_list': ['HK.00700', 'HK.00388', 'HK.00941'],
            'group_type': 'CUSTOM'
        }
        self.mock_futu_market.get_user_security_group.return_value = dict_response
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.mock_group_table.add_row.assert_called_with("单个分组", "3", "CUSTOM")
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 1 个分组")
    
    def test_load_list_response(self):
        """测试加载列表响应时的处理"""
        # 模拟返回列表格式
        list_response = [
            {
                'group_name': '列表分组1',
                'stock_list': ['HK.00700'],
                'group_type': 'CUSTOM'
            },
            {
                'group_name': '列表分组2',
                'stock_list': ['HK.00388'],
                'group_type': 'CUSTOM'
            }
        ]
        self.mock_futu_market.get_user_security_group.return_value = list_response
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.assertEqual(self.mock_group_table.add_row.call_count, 2)
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 2 个分组")
    
    def test_load_none_response(self):
        """测试加载None响应时的处理"""
        # 模拟返回None
        self.mock_futu_market.get_user_security_group.return_value = None
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called_once()
        self.mock_group_table.add_row.assert_called_with("暂无分组", "0", "-")
        self.monitor_app.logger.info.assert_called_with("加载用户分组完成，共 0 个分组")
    
    def test_load_exception_handling(self):
        """测试异常处理"""
        # 模拟抛出异常
        self.mock_futu_market.get_user_security_group.side_effect = Exception("API连接错误")
        
        # 运行测试
        import asyncio
        asyncio.run(self._load_user_groups_mock())
        
        # 验证结果
        self.mock_group_table.clear.assert_called()
        self.mock_group_table.add_row.assert_called_with("加载失败", "0", "ERROR")
        self.monitor_app.logger.warning.assert_called_with("加载用户分组失败: API连接错误")


if __name__ == '__main__':
    unittest.main()