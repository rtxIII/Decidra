#!/usr/bin/env python3
"""
订单修改功能集成测试

测试用户在主界面点击订单时弹出修改订单菜单的完整流程
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from ..base.order import ModifyOrderData
from ..monitor.main.event_handler import EventHandler
from ..monitor.app_core import AppCore


class TestModifyOrderIntegration(unittest.TestCase):
    """订单修改功能集成测试"""

    def setUp(self):
        """测试前准备"""
        # 创建mock应用实例
        self.mock_app = Mock()
        self.mock_app.run_worker = Mock(side_effect=lambda worker, **kwargs: asyncio.create_task(worker()))

        # 创建AppCore实例
        self.app_core = AppCore(self.mock_app)

        # 设置订单数据
        self.app_core.order_data = [
            {
                'order_id': 'TEST_ORDER_001',
                'code': 'HK.00700',
                'price': 350.5,
                'qty': 100,
                'status': 'SUBMITTED'
            },
            {
                'order_id': 'TEST_ORDER_002',
                'code': 'HK.09988',
                'price': 85.2,
                'qty': 200,
                'status': 'FILLED_PART'
            }
        ]

        # 设置活跃表格为订单表格
        self.app_core.active_table = "orders"
        self.app_core.current_order_cursor = 0

        # 创建EventHandler实例
        self.event_handler = EventHandler(self.app_core, self.mock_app)

    def test_validate_order_data_structure(self):
        """测试订单数据结构验证"""
        self.assertEqual(len(self.app_core.order_data), 2)

        first_order = self.app_core.order_data[0]
        self.assertIn('order_id', first_order)
        self.assertIn('code', first_order)
        self.assertIn('price', first_order)
        self.assertIn('qty', first_order)

    def test_order_selection(self):
        """测试订单选择逻辑"""
        # 选择第一个订单
        self.app_core.current_order_cursor = 0
        selected_order = self.app_core.order_data[self.app_core.current_order_cursor]

        self.assertEqual(selected_order['order_id'], 'TEST_ORDER_001')
        self.assertEqual(selected_order['code'], 'HK.00700')

        # 选择第二个订单
        self.app_core.current_order_cursor = 1
        selected_order = self.app_core.order_data[self.app_core.current_order_cursor]

        self.assertEqual(selected_order['order_id'], 'TEST_ORDER_002')
        self.assertEqual(selected_order['code'], 'HK.09988')

    @patch('monitor.main.event_handler.show_modify_order_dialog')
    async def test_modify_order_dialog_trigger(self, mock_dialog):
        """测试改单对话框触发逻辑"""
        # 模拟对话框返回修改数据
        mock_dialog.return_value = ModifyOrderData(
            order_id='TEST_ORDER_001',
            price=360.0,
            qty=150,
            aux_price=None
        )

        # 创建mock ui_manager
        mock_ui_manager = Mock()
        mock_ui_manager.info_panel = Mock()
        mock_ui_manager.info_panel.log_info = AsyncMock()
        mock_ui_manager.update_orders_table = AsyncMock()
        self.app_core.app.ui_manager = mock_ui_manager

        # 创建mock data_manager和futu_trade
        mock_data_manager = Mock()
        mock_futu_trade = Mock()
        mock_futu_trade.modify_order = Mock(return_value={
            'success': True,
            'order_id': 'TEST_ORDER_001',
            'timestamp': '2025-10-15T10:00:00'
        })
        mock_data_manager.futu_trade = mock_futu_trade
        self.app_core.app.data_manager = mock_data_manager

        # 创建mock group_manager
        mock_group_manager = Mock()
        mock_group_manager.refresh_user_orders = AsyncMock()
        self.app_core.app.group_manager = mock_group_manager

        # 执行改单操作
        await self.event_handler._modify_order_worker()

        # 验证对话框被调用
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        self.assertEqual(call_args.kwargs['order_id'], 'TEST_ORDER_001')
        self.assertEqual(call_args.kwargs['current_price'], 350.5)
        self.assertEqual(call_args.kwargs['current_qty'], 100)

    @patch('monitor.main.event_handler.show_modify_order_dialog')
    async def test_modify_order_api_call(self, mock_dialog):
        """测试改单API调用"""
        # 模拟对话框返回修改数据
        modify_data = ModifyOrderData(
            order_id='TEST_ORDER_001',
            price=360.0,
            qty=150,
            aux_price=None
        )
        mock_dialog.return_value = modify_data

        # 创建mock组件
        mock_ui_manager = Mock()
        mock_ui_manager.info_panel = Mock()
        mock_ui_manager.info_panel.log_info = AsyncMock()
        mock_ui_manager.update_orders_table = AsyncMock()
        self.app_core.app.ui_manager = mock_ui_manager

        mock_data_manager = Mock()
        mock_futu_trade = Mock()
        mock_futu_trade.modify_order = Mock(return_value={
            'success': True,
            'order_id': 'TEST_ORDER_001'
        })
        mock_data_manager.futu_trade = mock_futu_trade
        self.app_core.app.data_manager = mock_data_manager

        mock_group_manager = Mock()
        mock_group_manager.refresh_user_orders = AsyncMock()
        self.app_core.app.group_manager = mock_group_manager

        # 执行改单操作
        await self.event_handler._modify_order_worker()

        # 验证API被正确调用
        mock_futu_trade.modify_order.assert_called_once_with(
            order_id='TEST_ORDER_001',
            price=360.0,
            qty=150,
            trd_env=None,
            market=None
        )

        # 验证成功消息被记录
        mock_ui_manager.info_panel.log_info.assert_any_call(
            "订单 TEST_ORDER_001 修改成功",
            "改单操作"
        )

        # 验证订单数据被刷新
        mock_group_manager.refresh_user_orders.assert_called_once()
        mock_ui_manager.update_orders_table.assert_called_once()

    @patch('monitor.main.event_handler.show_modify_order_dialog')
    async def test_modify_order_failure(self, mock_dialog):
        """测试改单失败处理"""
        # 模拟对话框返回修改数据
        modify_data = ModifyOrderData(
            order_id='TEST_ORDER_001',
            price=360.0,
            qty=150,
            aux_price=None
        )
        mock_dialog.return_value = modify_data

        # 创建mock组件
        mock_ui_manager = Mock()
        mock_ui_manager.info_panel = Mock()
        mock_ui_manager.info_panel.log_info = AsyncMock()
        self.app_core.app.ui_manager = mock_ui_manager

        mock_data_manager = Mock()
        mock_futu_trade = Mock()
        mock_futu_trade.modify_order = Mock(return_value={
            'success': False,
            'message': '订单已完成，无法修改'
        })
        mock_data_manager.futu_trade = mock_futu_trade
        self.app_core.app.data_manager = mock_data_manager

        mock_group_manager = Mock()
        self.app_core.app.group_manager = mock_group_manager

        # 执行改单操作
        await self.event_handler._modify_order_worker()

        # 验证失败消息被记录
        mock_ui_manager.info_panel.log_info.assert_any_call(
            "订单 TEST_ORDER_001 修改失败: 订单已完成，无法修改",
            "改单操作"
        )

    async def test_action_select_group_triggers_modify(self):
        """测试空格键在订单表格触发改单"""
        with patch.object(self.event_handler, 'action_modify_order', new_callable=AsyncMock) as mock_modify:
            # 设置活跃表格为订单表格
            self.app_core.active_table = "orders"

            # 触发空格键动作
            await self.event_handler.action_select_group()

            # 验证改单方法被调用
            mock_modify.assert_called_once()


def run_async_test(coro):
    """运行异步测试的辅助函数"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestModifyOrderIntegration)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回测试结果
    exit(0 if result.wasSuccessful() else 1)
