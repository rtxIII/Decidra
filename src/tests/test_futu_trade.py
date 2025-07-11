"""
富途交易业务逻辑测试

测试FutuTrade类的所有交易功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.futu_trade import FutuTrade
from base.futu_class import FutuTradeException


class TestFutuTrade(unittest.TestCase):
    """富途交易业务逻辑测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # Mock配置和create_client
        with patch('base.futu_modue.config') as mock_config, \
             patch('base.futu_modue.create_client') as mock_create_client:
            
            mock_config.__getitem__.return_value = {
                'Password_md5': 'test_password',
                'Host': '127.0.0.1',
                'Port': '11111'
            }
            
            mock_client = Mock()
            mock_client.trade = Mock()
            mock_client.quote = Mock()
            mock_create_client.return_value = mock_client
            
            self.futu_trade = FutuTrade()
            self.mock_client = mock_client
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.futu_trade.default_trd_env, "SIMULATE")
        self.assertEqual(self.futu_trade.default_market, "HK")
        self.assertEqual(self.futu_trade.default_currency, "HKD")
        self.assertFalse(self.futu_trade.is_trade_unlocked)
        self.assertIsInstance(self.futu_trade.risk_config, dict)
        self.assertIsInstance(self.futu_trade.order_history, list)
        self.assertIsInstance(self.futu_trade.deal_history, list)
    
    def test_get_account_list(self):
        """测试获取账户列表"""
        # Mock返回DataFrame
        mock_df = pd.DataFrame([
            {'acc_id': 1, 'acc_name': 'test_account', 'market': 'HK'},
            {'acc_id': 2, 'acc_name': 'test_account2', 'market': 'US'}
        ])
        self.mock_client.trade.get_acc_list.return_value = mock_df
        
        result = self.futu_trade.get_account_list()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['acc_id'], 1)
        self.mock_client.trade.get_acc_list.assert_called_once_with("HK")
    
    def test_get_account_list_error(self):
        """测试获取账户列表异常"""
        self.mock_client.trade.get_acc_list.side_effect = Exception("API Error")
        
        result = self.futu_trade.get_account_list()
        
        self.assertEqual(result, [])
    
    def test_unlock_trading_success(self):
        """测试解锁交易成功"""
        self.mock_client.trade.unlock_trade.return_value = True
        
        result = self.futu_trade.unlock_trading("test_password")
        
        self.assertTrue(result)
        self.assertTrue(self.futu_trade.is_trade_unlocked)
        self.mock_client.trade.unlock_trade.assert_called_once_with("test_password", "HK")
    
    def test_unlock_trading_no_password(self):
        """测试解锁交易无密码"""
        self.futu_trade.password_md5 = None
        
        result = self.futu_trade.unlock_trading()
        
        self.assertFalse(result)
        self.assertFalse(self.futu_trade.is_trade_unlocked)
    
    def test_get_account_info(self):
        """测试获取账户信息"""
        mock_df = pd.DataFrame([{
            'acc_id': 1,
            'total_assets': 100000,
            'cash': 50000,
            'market_value': 50000
        }])
        self.mock_client.trade.get_account_info.return_value = mock_df
        
        result = self.futu_trade.get_account_info()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['acc_id'], 1)
        self.assertEqual(result['total_assets'], 100000)
        self.assertEqual(self.futu_trade.account_info, result)
    
    def test_get_funds_info(self):
        """测试获取资金信息"""
        mock_df = pd.DataFrame([{
            'cash': 50000,
            'available_funds': 45000,
            'market_value': 50000
        }])
        self.mock_client.trade.get_funds.return_value = mock_df
        
        result = self.futu_trade.get_funds_info()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['cash'], 50000)
        self.assertEqual(result['available_funds'], 45000)
    
    def test_get_position_list(self):
        """测试获取持仓列表"""
        mock_df = pd.DataFrame([
            {'code': 'HK.00700', 'qty': 100, 'cur_price': 500, 'market_value': 50000},
            {'code': 'HK.00388', 'qty': 200, 'cur_price': 100, 'market_value': 20000}
        ])
        self.mock_client.trade.get_position_list.return_value = mock_df
        
        result = self.futu_trade.get_position_list()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['code'], 'HK.00700')
        self.assertEqual(self.futu_trade.position_list, result)
    
    def test_get_position_by_code(self):
        """测试获取特定股票持仓"""
        mock_df = pd.DataFrame([
            {'code': 'HK.00700', 'qty': 100, 'cur_price': 500},
            {'code': 'HK.00388', 'qty': 200, 'cur_price': 100}
        ])
        self.mock_client.trade.get_position_list.return_value = mock_df
        
        result = self.futu_trade.get_position_by_code('HK.00700')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['code'], 'HK.00700')
        self.assertEqual(result['qty'], 100)
    
    def test_get_total_position_value(self):
        """测试获取总持仓市值"""
        mock_df = pd.DataFrame([
            {'code': 'HK.00700', 'qty': 100, 'cur_price': 500},
            {'code': 'HK.00388', 'qty': 200, 'cur_price': 100}
        ])
        self.mock_client.trade.get_position_list.return_value = mock_df
        
        result = self.futu_trade.get_total_position_value()
        
        self.assertEqual(result, 70000)  # 100*500 + 200*100
    
    def test_place_order_success(self):
        """测试下单成功"""
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'code': 'HK.00700',
            'price': 500,
            'qty': 100,
            'trd_side': 'BUY'
        }])
        self.mock_client.trade.place_order.return_value = mock_df
        
        # Mock解锁交易
        self.futu_trade.is_trade_unlocked = True
        
        result = self.futu_trade.place_order('HK.00700', 500, 100, enable_risk_check=False)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'ORDER123')
        self.assertEqual(len(self.futu_trade.order_history), 1)
    
    def test_place_order_risk_check_fail(self):
        """测试下单风险检查失败"""
        # 设置风险参数
        self.futu_trade.risk_config['max_single_order_amount'] = 1000
        
        result = self.futu_trade.place_order('HK.00700', 500, 100)  # 50000 > 1000
        
        self.assertFalse(result['success'])
        self.assertIn('Risk check failed', result['message'])
    
    def test_place_order_not_unlocked(self):
        """测试下单未解锁"""
        self.futu_trade.is_trade_unlocked = False
        self.mock_client.trade.unlock_trade.return_value = False
        
        result = self.futu_trade.place_order('HK.00700', 500, 100, enable_risk_check=False)
        
        self.assertFalse(result['success'])
        self.assertIn('Trading not unlocked', result['message'])
    
    def test_cancel_order_success(self):
        """测试撤单成功"""
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'status': 'CANCELLED'
        }])
        self.mock_client.trade.cancel_order.return_value = mock_df
        
        result = self.futu_trade.cancel_order('ORDER123')
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'ORDER123')
    
    def test_modify_order_success(self):
        """测试修改订单成功"""
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'price': 510,
            'qty': 150
        }])
        self.mock_client.trade.modify_order.return_value = mock_df
        
        result = self.futu_trade.modify_order('ORDER123', 510, 150)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'ORDER123')
    
    def test_get_order_list(self):
        """测试获取订单列表"""
        mock_df = pd.DataFrame([
            {'order_id': 'ORDER123', 'code': 'HK.00700', 'status': 'FILLED'},
            {'order_id': 'ORDER124', 'code': 'HK.00388', 'status': 'SUBMITTED'}
        ])
        self.mock_client.trade.get_order_list.return_value = mock_df
        
        result = self.futu_trade.get_order_list()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['order_id'], 'ORDER123')
    
    def test_get_deal_list(self):
        """测试获取成交列表"""
        mock_df = pd.DataFrame([
            {'deal_id': 'DEAL123', 'code': 'HK.00700', 'pnl': 100, 'fee': 10},
            {'deal_id': 'DEAL124', 'code': 'HK.00388', 'pnl': -50, 'fee': 5}
        ])
        self.mock_client.trade.get_deal_list.return_value = mock_df
        
        result = self.futu_trade.get_deal_list()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['deal_id'], 'DEAL123')
        self.assertEqual(self.futu_trade.deal_history, result)
    
    def test_get_max_buy_qty(self):
        """测试获取最大买入数量"""
        mock_df = pd.DataFrame([{'max_qty': 1000}])
        self.mock_client.trade.get_max_trd_qty.return_value = mock_df
        
        result = self.futu_trade.get_max_buy_qty('HK.00700', 500)
        
        self.assertEqual(result, 1000)
        self.mock_client.trade.get_max_trd_qty.assert_called_once_with(
            "NORMAL", 'HK.00700', 500, "BUY", "SIMULATE", "HK"
        )
    
    def test_get_max_sell_qty(self):
        """测试获取最大卖出数量"""
        mock_df = pd.DataFrame([{'max_qty': 500}])
        self.mock_client.trade.get_max_trd_qty.return_value = mock_df
        
        result = self.futu_trade.get_max_sell_qty('HK.00700', 500)
        
        self.assertEqual(result, 500)
        self.mock_client.trade.get_max_trd_qty.assert_called_once_with(
            "NORMAL", 'HK.00700', 500, "SELL", "SIMULATE", "HK"
        )
    
    def test_get_order_fee(self):
        """测试获取订单费用"""
        mock_df = pd.DataFrame([{
            'fee': 25.5,
            'commission': 20.0,
            'platform_fee': 5.5
        }])
        self.mock_client.trade.get_order_fee.return_value = mock_df
        
        result = self.futu_trade.get_order_fee('HK.00700', 500, 100)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['fee'], 25.5)
        self.assertEqual(result['commission'], 20.0)
    
    def test_market_buy(self):
        """测试市价买入"""
        # Mock获取当前价格
        self.mock_client.quote.get_stock_quote.return_value = [{'cur_price': 500}]
        
        # Mock下单
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'code': 'HK.00700',
            'price': 500,
            'qty': 100,
            'trd_side': 'BUY'
        }])
        self.mock_client.trade.place_order.return_value = mock_df
        self.futu_trade.is_trade_unlocked = True
        
        result = self.futu_trade.market_buy('HK.00700', 50000)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['qty'], 100)  # 50000 / 500
    
    def test_market_sell(self):
        """测试市价卖出"""
        # Mock获取持仓
        mock_position_df = pd.DataFrame([{
            'code': 'HK.00700',
            'qty': 200,
            'cur_price': 500
        }])
        self.mock_client.trade.get_position_list.return_value = mock_position_df
        
        # Mock获取当前价格
        self.mock_client.quote.get_stock_quote.return_value = [{'cur_price': 500}]
        
        # Mock下单
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'code': 'HK.00700',
            'price': 500,
            'qty': 200,
            'trd_side': 'SELL'
        }])
        self.mock_client.trade.place_order.return_value = mock_df
        self.futu_trade.is_trade_unlocked = True
        
        result = self.futu_trade.market_sell('HK.00700')  # 全部卖出
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['qty'], 200)
    
    def test_batch_place_orders(self):
        """测试批量下单"""
        orders = [
            {'code': 'HK.00700', 'price': 500, 'qty': 100, 'trd_side': 'BUY'},
            {'code': 'HK.00388', 'price': 100, 'qty': 200, 'trd_side': 'BUY'}
        ]
        
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'success': True
        }])
        self.mock_client.trade.place_order.return_value = mock_df
        self.futu_trade.is_trade_unlocked = True
        
        with patch('time.sleep'):  # Mock sleep
            result = self.futu_trade.batch_place_orders(orders)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(self.mock_client.trade.place_order.call_count, 2)
    
    def test_batch_cancel_orders(self):
        """测试批量撤单"""
        order_ids = ['ORDER123', 'ORDER124']
        
        mock_df = pd.DataFrame([{
            'order_id': 'ORDER123',
            'success': True
        }])
        self.mock_client.trade.cancel_order.return_value = mock_df
        
        with patch('time.sleep'):  # Mock sleep
            result = self.futu_trade.batch_cancel_orders(order_ids)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(self.mock_client.trade.cancel_order.call_count, 2)
    
    def test_set_risk_config(self):
        """测试设置风险控制配置"""
        new_config = {
            'max_single_order_amount': 200000,
            'max_position_ratio': 0.5
        }
        
        result = self.futu_trade.set_risk_config(new_config)
        
        self.assertTrue(result)
        self.assertEqual(self.futu_trade.risk_config['max_single_order_amount'], 200000)
        self.assertEqual(self.futu_trade.risk_config['max_position_ratio'], 0.5)
    
    def test_get_risk_config(self):
        """测试获取风险控制配置"""
        result = self.futu_trade.get_risk_config()
        
        self.assertIsInstance(result, dict)
        self.assertIn('max_single_order_amount', result)
        self.assertIn('enable_risk_control', result)
    
    def test_risk_check_order_amount_exceed(self):
        """测试风险检查-订单金额超限"""
        self.futu_trade.risk_config['max_single_order_amount'] = 10000
        
        result = self.futu_trade._risk_check_order('HK.00700', 500, 100, 'BUY', 'SIMULATE', 'HK')
        
        self.assertFalse(result)  # 500 * 100 = 50000 > 10000
    
    def test_risk_check_order_disabled(self):
        """测试风险检查-禁用风险控制"""
        self.futu_trade.risk_config['enable_risk_control'] = False
        
        result = self.futu_trade._risk_check_order('HK.00700', 500, 1000, 'BUY', 'SIMULATE', 'HK')
        
        self.assertTrue(result)  # 风险控制禁用，应该通过
    
    def test_get_daily_pnl(self):
        """测试获取当日盈亏"""
        today = datetime.now().strftime('%Y-%m-%d')
        mock_df = pd.DataFrame([
            {'pnl': 100, 'fee': 10, 'timestamp': today},
            {'pnl': -50, 'fee': 5, 'timestamp': today}
        ])
        self.mock_client.trade.get_deal_list.return_value = mock_df
        
        result = self.futu_trade.get_daily_pnl()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_pnl'], 50)  # 100 - 50
        self.assertEqual(result['total_fee'], 15)  # 10 + 5
        self.assertEqual(result['net_pnl'], 35)  # 50 - 15
        self.assertEqual(result['deal_count'], 2)
    
    def test_set_order_callback(self):
        """测试设置订单回调"""
        mock_callback = Mock()
        
        self.futu_trade.set_order_callback(mock_callback)
        
        self.assertEqual(self.futu_trade.order_callbacks['HK'], mock_callback)
        self.mock_client.trade.set_order_callback.assert_called_once_with(mock_callback, 'HK')
    
    def test_set_deal_callback(self):
        """测试设置成交回调"""
        mock_callback = Mock()
        
        self.futu_trade.set_deal_callback(mock_callback)
        
        self.assertEqual(self.futu_trade.deal_callbacks['HK'], mock_callback)
        self.mock_client.trade.set_deal_callback.assert_called_once_with(mock_callback, 'HK')
    
    def test_get_trading_status(self):
        """测试获取交易状态"""
        result = self.futu_trade.get_trading_status()
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_trade_unlocked', result)
        self.assertIn('default_trd_env', result)
        self.assertIn('default_market', result)
        self.assertIn('risk_control_enabled', result)
    
    def test_clear_cache(self):
        """测试清除缓存"""
        # 设置一些缓存数据
        self.futu_trade.account_info = {'test': 'data'}
        self.futu_trade.position_list = [{'test': 'position'}]
        self.futu_trade.order_history = [{'test': 'order'}]
        self.futu_trade.deal_history = [{'test': 'deal'}]
        
        self.futu_trade.clear_cache()
        
        self.assertIsNone(self.futu_trade.account_info)
        self.assertIsNone(self.futu_trade.position_list)
        self.assertEqual(self.futu_trade.order_history, [])
        self.assertEqual(self.futu_trade.deal_history, [])
    
    def test_get_performance_summary(self):
        """测试获取绩效总结"""
        mock_df = pd.DataFrame([
            {'pnl': 100, 'fee': 10, 'price': 500, 'qty': 1},
            {'pnl': -50, 'fee': 5, 'price': 400, 'qty': 2}
        ])
        self.mock_client.trade.get_deal_list.return_value = mock_df
        
        result = self.futu_trade.get_performance_summary(7)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_deals'], 2)
        self.assertEqual(result['total_pnl'], 50)
        self.assertEqual(result['total_fee'], 15)
        self.assertEqual(result['net_pnl'], 35)
        self.assertEqual(result['win_deals'], 1)
        self.assertEqual(result['lose_deals'], 1)
        self.assertEqual(result['win_rate'], 0.5)
    
    def test_health_check(self):
        """测试健康检查"""
        # Mock基础健康检查
        with patch('base.futu_modue.FutuModuleBase.health_check') as mock_base_health:
            mock_base_health.return_value = {'connection_status': 'connected'}
            
            result = self.futu_trade.health_check()
            
            self.assertIsInstance(result, dict)
            self.assertIn('connection_status', result)
            self.assertIn('trade_unlocked', result)
            self.assertIn('risk_control_enabled', result)


if __name__ == '__main__':
    unittest.main()