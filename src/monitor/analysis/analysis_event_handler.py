"""
AnalysisEventHandler - 分析页面事件处理模块

负责分析页面的用户交互事件处理、快捷键响应、UI更新协调
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from utils.logger import get_logger


class AnalysisEventHandler:
    """
    分析事件处理器
    负责分析页面的所有用户交互事件处理
    """
    
    def __init__(self, analysis_data_manager, chart_manager, ai_analysis_manager):
        """初始化分析事件处理器"""
        self.analysis_data_manager = analysis_data_manager
        self.chart_manager = chart_manager
        self.ai_analysis_manager = ai_analysis_manager
        self.logger = get_logger(__name__)
        
        # 事件处理状态
        self.current_focus = 'chart'  # 'chart', 'ai', 'input'
        self.input_mode = False  # 是否处于输入模式
        self.pending_user_input = ""  # 待处理的用户输入
        
        # 快捷键映射
        self.key_bindings = {
            # 时间周期切换
            'd': self._handle_daily_period,
            'w': self._handle_weekly_period, 
            'm': self._handle_monthly_period,
            
            # 图表操作
            'left': self._handle_chart_scroll_left,
            'right': self._handle_chart_scroll_right,
            'up': self._handle_chart_zoom_in,
            'down': self._handle_chart_zoom_out,
            'home': self._handle_chart_jump_start,
            'end': self._handle_chart_jump_end,
            
            # 显示切换
            'v': self._handle_toggle_volume,
            'i': self._handle_toggle_indicators,
            
            # AI分析快捷键
            'f1': self._handle_technical_analysis,
            'f2': self._handle_fundamental_analysis,
            'f3': self._handle_capital_flow_analysis,
            'f4': self._handle_sector_comparison,
            'f5': self._handle_risk_assessment,
            
            # 界面操作
            'tab': self._handle_focus_switch,
            'enter': self._handle_enter_input,
            'escape': self._handle_exit_analysis,
            
            # 帮助
            'h': self._handle_show_help,
            '?': self._handle_show_ai_help,
        }
        
        # 事件回调函数
        self.event_callbacks: Dict[str, List[Callable]] = {
            'stock_changed': [],
            'period_changed': [],
            'chart_updated': [],
            'ai_response': [],
            'focus_changed': [],
            'error_occurred': []
        }
        
        self.logger.info("AnalysisEventHandler 初始化完成")
    
    def register_callback(self, event_type: str, callback: Callable):
        """注册事件回调函数"""
        try:
            if event_type not in self.event_callbacks:
                self.event_callbacks[event_type] = []
            
            self.event_callbacks[event_type].append(callback)
            self.logger.debug(f"注册事件回调: {event_type}")
            
        except Exception as e:
            self.logger.error(f"注册事件回调失败: {e}")
    
    async def emit_event(self, event_type: str, data: Any = None):
        """触发事件回调"""
        try:
            if event_type in self.event_callbacks:
                for callback in self.event_callbacks[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        self.logger.error(f"事件回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"触发事件失败: {e}")
    
    async def handle_key_event(self, key: str) -> bool:
        """处理按键事件"""
        try:
            key = key.lower()
            
            # 如果处于输入模式，特殊处理
            if self.input_mode:
                return await self._handle_input_mode_key(key)
            
            # 查找对应的按键处理函数
            if key in self.key_bindings:
                handler = self.key_bindings[key]
                result = await handler()
                
                if result is True:
                    self.logger.debug(f"按键事件处理成功: {key}")
                    return True
                elif result is False:
                    self.logger.debug(f"按键事件处理失败: {key}")
                    return False
                else:
                    # 如果返回None，继续尝试其他处理
                    pass
            
            # 尝试让图表管理器处理
            if self.current_focus == 'chart':
                if self.chart_manager.handle_chart_key_event(key):
                    await self.emit_event('chart_updated')
                    return True
            
            self.logger.debug(f"未处理的按键事件: {key}")
            return False
            
        except Exception as e:
            self.logger.error(f"处理按键事件失败: {e}")
            await self.emit_event('error_occurred', str(e))
            return False
    
    async def _handle_input_mode_key(self, key: str) -> bool:
        """处理输入模式下的按键"""
        try:
            if key == 'escape':
                # 退出输入模式
                self.input_mode = False
                self.pending_user_input = ""
                await self.emit_event('focus_changed', {'focus': self.current_focus, 'input_mode': False})
                return True
                
            elif key == 'enter':
                # 提交用户输入
                if self.pending_user_input.strip():
                    response = await self.ai_analysis_manager.process_user_input(self.pending_user_input)
                    await self.emit_event('ai_response', {
                        'user_input': self.pending_user_input,
                        'ai_response': response
                    })
                
                self.input_mode = False
                self.pending_user_input = ""
                await self.emit_event('focus_changed', {'focus': self.current_focus, 'input_mode': False})
                return True
                
            elif key == 'backspace':
                # 删除字符
                if self.pending_user_input:
                    self.pending_user_input = self.pending_user_input[:-1]
                return True
                
            elif len(key) == 1 and key.isprintable():
                # 添加字符
                self.pending_user_input += key
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"处理输入模式按键失败: {e}")
            return False
    
    async def handle_stock_change(self, stock_code: str) -> bool:
        """处理股票切换事件"""
        try:
            self.logger.info(f"处理股票切换: {stock_code}")
            
            # 设置当前分析股票
            data_success = await self.analysis_data_manager.set_current_stock(stock_code)
            if not data_success:
                await self.emit_event('error_occurred', f"无法加载股票 {stock_code} 的数据")
                return False
            
            # 更新图表数据
            chart_success = await self.chart_manager.update_chart_data(
                stock_code, self.analysis_data_manager.current_time_period
            )
            if not chart_success:
                self.logger.warning(f"更新图表数据失败: {stock_code}")
            
            # 设置AI分析股票
            ai_success = await self.ai_analysis_manager.set_current_stock(stock_code)
            if not ai_success:
                self.logger.warning(f"设置AI分析股票失败: {stock_code}")
            
            await self.emit_event('stock_changed', {
                'stock_code': stock_code,
                'data_loaded': data_success,
                'chart_updated': chart_success,
                'ai_ready': ai_success
            })
            
            return data_success
            
        except Exception as e:
            self.logger.error(f"处理股票切换失败: {e}")
            await self.emit_event('error_occurred', str(e))
            return False
    
    async def handle_user_input(self, user_input: str) -> str:
        """处理用户AI对话输入"""
        try:
            if not user_input.strip():
                return "请输入您的问题。"
            
            # 处理用户输入
            response = await self.ai_analysis_manager.process_user_input(user_input)
            
            await self.emit_event('ai_response', {
                'user_input': user_input,
                'ai_response': response
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"处理用户输入失败: {e}")
            error_msg = "处理您的问题时出现错误，请稍后重试。"
            await self.emit_event('error_occurred', str(e))
            return error_msg
    
    async def _handle_daily_period(self) -> bool:
        """处理日线周期切换"""
        try:
            success = await self.analysis_data_manager.change_time_period('D')
            if success:
                await self.chart_manager.update_chart_data(
                    self.analysis_data_manager.current_stock_code, 'D'
                )
                await self.emit_event('period_changed', {'period': 'D', 'name': '日线'})
                await self.emit_event('chart_updated')
            return success
            
        except Exception as e:
            self.logger.error(f"切换日线周期失败: {e}")
            return False
    
    async def _handle_weekly_period(self) -> bool:
        """处理周线周期切换"""
        try:
            success = await self.analysis_data_manager.change_time_period('W')
            if success:
                await self.chart_manager.update_chart_data(
                    self.analysis_data_manager.current_stock_code, 'W'
                )
                await self.emit_event('period_changed', {'period': 'W', 'name': '周线'})
                await self.emit_event('chart_updated')
            return success
            
        except Exception as e:
            self.logger.error(f"切换周线周期失败: {e}")
            return False
    
    async def _handle_monthly_period(self) -> bool:
        """处理月线周期切换"""
        try:
            success = await self.analysis_data_manager.change_time_period('M')
            if success:
                await self.chart_manager.update_chart_data(
                    self.analysis_data_manager.current_stock_code, 'M'
                )
                await self.emit_event('period_changed', {'period': 'M', 'name': '月线'})
                await self.emit_event('chart_updated')
            return success
            
        except Exception as e:
            self.logger.error(f"切换月线周期失败: {e}")
            return False
    
    async def _handle_chart_scroll_left(self) -> bool:
        """处理图表左滚动"""
        success = self.chart_manager.scroll_chart('left')
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_chart_scroll_right(self) -> bool:
        """处理图表右滚动"""
        success = self.chart_manager.scroll_chart('right')
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_chart_zoom_in(self) -> bool:
        """处理图表放大"""
        success = self.chart_manager.zoom_chart(True)
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_chart_zoom_out(self) -> bool:
        """处理图表缩小"""
        success = self.chart_manager.zoom_chart(False)
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_chart_jump_start(self) -> bool:
        """处理跳转到图表开始"""
        success = self.chart_manager.jump_to_earliest()
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_chart_jump_end(self) -> bool:
        """处理跳转到图表结束"""
        success = self.chart_manager.jump_to_latest()
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_toggle_volume(self) -> bool:
        """处理切换成交量显示"""
        success = self.chart_manager.toggle_volume_display()
        if success:
            await self.emit_event('chart_updated')
        return success
    
    async def _handle_toggle_indicators(self) -> bool:
        """处理切换技术指标显示"""
        # 循环切换MACD和RSI
        if not self.chart_manager.show_macd and not self.chart_manager.show_rsi:
            self.chart_manager.toggle_indicator_display('macd')
        elif self.chart_manager.show_macd and not self.chart_manager.show_rsi:
            self.chart_manager.toggle_indicator_display('rsi')
        else:
            self.chart_manager.toggle_indicator_display('macd')
            self.chart_manager.toggle_indicator_display('rsi')
        
        await self.emit_event('chart_updated')
        return True
    
    async def _handle_technical_analysis(self) -> bool:
        """处理技术分析快捷键"""
        try:
            response = await self.ai_analysis_manager.generate_analysis('technical')
            await self.emit_event('ai_response', {
                'user_input': 'F1 - 技术分析',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"技术分析失败: {e}")
            return False
    
    async def _handle_fundamental_analysis(self) -> bool:
        """处理基本面分析快捷键"""
        try:
            response = await self.ai_analysis_manager.generate_analysis('fundamental')
            await self.emit_event('ai_response', {
                'user_input': 'F2 - 基本面分析',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"基本面分析失败: {e}")
            return False
    
    async def _handle_capital_flow_analysis(self) -> bool:
        """处理资金面分析快捷键"""
        try:
            response = await self.ai_analysis_manager.generate_analysis('capital_flow')
            await self.emit_event('ai_response', {
                'user_input': 'F3 - 资金面分析',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"资金面分析失败: {e}")
            return False
    
    async def _handle_sector_comparison(self) -> bool:
        """处理同行对比快捷键"""
        try:
            response = await self.ai_analysis_manager.generate_analysis('sector_comparison')
            await self.emit_event('ai_response', {
                'user_input': 'F4 - 同行对比',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"同行对比失败: {e}")
            return False
    
    async def _handle_risk_assessment(self) -> bool:
        """处理风险评估快捷键"""
        try:
            response = await self.ai_analysis_manager.generate_analysis('risk_assessment')
            await self.emit_event('ai_response', {
                'user_input': 'F5 - 风险评估',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            return False
    
    async def _handle_focus_switch(self) -> bool:
        """处理焦点切换"""
        try:
            if self.current_focus == 'chart':
                self.current_focus = 'ai'
            else:
                self.current_focus = 'chart'
            
            await self.emit_event('focus_changed', {
                'focus': self.current_focus,
                'input_mode': self.input_mode
            })
            return True
            
        except Exception as e:
            self.logger.error(f"焦点切换失败: {e}")
            return False
    
    async def _handle_enter_input(self) -> bool:
        """处理进入输入模式"""
        try:
            if self.current_focus == 'ai':
                self.input_mode = True
                self.pending_user_input = ""
                await self.emit_event('focus_changed', {
                    'focus': self.current_focus,
                    'input_mode': True
                })
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"进入输入模式失败: {e}")
            return False
    
    async def _handle_exit_analysis(self) -> bool:
        """处理退出分析页面"""
        try:
            await self.emit_event('focus_changed', {'action': 'exit_analysis'})
            return True
            
        except Exception as e:
            self.logger.error(f"退出分析页面失败: {e}")
            return False
    
    async def _handle_show_help(self) -> bool:
        """处理显示帮助"""
        try:
            help_text = self._generate_analysis_help()
            await self.emit_event('ai_response', {
                'user_input': 'H - 帮助',
                'ai_response': help_text
            })
            return True
            
        except Exception as e:
            self.logger.error(f"显示帮助失败: {e}")
            return False
    
    async def _handle_show_ai_help(self) -> bool:
        """处理显示AI帮助"""
        try:
            response = await self.ai_analysis_manager.process_user_input('?')
            await self.emit_event('ai_response', {
                'user_input': '? - AI帮助',
                'ai_response': response
            })
            return True
            
        except Exception as e:
            self.logger.error(f"显示AI帮助失败: {e}")
            return False
    
    def _generate_analysis_help(self) -> str:
        """生成分析页面帮助信息"""
        help_text = """📋 分析页面操作指南:

⏰ 时间周期切换:
• D - 切换到日线
• W - 切换到周线  
• M - 切换到月线

📊 图表操作:
• ←→ - 左右滚动图表
• ↑↓ - 放大/缩小图表
• Home/End - 跳转到最早/最新
• V - 切换成交量显示
• I - 切换技术指标显示

🤖 AI分析快捷键:
• F1 - 技术分析 (RSI, MACD等)
• F2 - 基本面分析 (估值, 财务)
• F3 - 资金面分析 (资金流向)  
• F4 - 同行对比 (行业分析)
• F5 - 风险评估 (风险等级)

💬 AI对话:
• Tab - 切换焦点到AI区域
• Enter - 进入输入模式
• ? - AI帮助指南
• Escape - 退出输入模式

🔄 通用操作:
• H - 显示此帮助
• Escape - 返回主界面

💡 提示: 使用Tab键在图表区域和AI区域间切换焦点"""
        
        return help_text
    
    def get_event_handler_status(self) -> Dict[str, Any]:
        """获取事件处理器状态"""
        return {
            'current_focus': self.current_focus,
            'input_mode': self.input_mode,
            'pending_input': self.pending_user_input,
            'registered_callbacks': {
                event_type: len(callbacks) 
                for event_type, callbacks in self.event_callbacks.items()
            }
        }
    
    def get_key_bindings_help(self) -> Dict[str, str]:
        """获取按键绑定帮助"""
        help_map = {
            'd/w/m': '切换时间周期(日/周/月)',
            '←→↑↓': '图表滚动和缩放',
            'home/end': '跳转到开始/结束',
            'v': '切换成交量显示',
            'i': '切换技术指标',
            'f1-f5': 'AI分析快捷键',
            'tab': '切换焦点',
            'enter': '进入输入模式',
            'escape': '退出/返回',
            'h/?': '显示帮助'
        }
        return help_map
    
    async def cleanup(self):
        """清理事件处理器"""
        try:
            self.event_callbacks.clear()
            self.current_focus = 'chart'
            self.input_mode = False
            self.pending_user_input = ""
            
            self.logger.info("AnalysisEventHandler 清理完成")
            
        except Exception as e:
            self.logger.error(f"AnalysisEventHandler 清理失败: {e}")
    
    # 便捷方法，供外部调用
    async def trigger_technical_analysis(self) -> str:
        """触发技术分析"""
        return await self.ai_analysis_manager.generate_analysis('technical')
    
    async def trigger_fundamental_analysis(self) -> str:
        """触发基本面分析"""
        return await self.ai_analysis_manager.generate_analysis('fundamental')
    
    async def trigger_risk_assessment(self) -> str:
        """触发风险评估"""
        return await self.ai_analysis_manager.generate_analysis('risk_assessment')
    
    async def switch_time_period(self, period: str) -> bool:
        """切换时间周期的便捷方法"""
        if period.upper() == 'D':
            return await self._handle_daily_period()
        elif period.upper() == 'W':
            return await self._handle_weekly_period()
        elif period.upper() == 'M':
            return await self._handle_monthly_period()
        else:
            return False
    
    async def scroll_chart(self, direction: str) -> bool:
        """滚动图表的便捷方法"""
        if direction.lower() == 'left':
            return await self._handle_chart_scroll_left()
        elif direction.lower() == 'right':
            return await self._handle_chart_scroll_right()
        else:
            return False
    
    async def zoom_chart(self, zoom_in: bool) -> bool:
        """缩放图表的便捷方法"""
        if zoom_in:
            return await self._handle_chart_zoom_in()
        else:
            return await self._handle_chart_zoom_out()