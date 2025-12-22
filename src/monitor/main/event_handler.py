"""
EventHandler - 事件处理和用户动作模块

负责所有用户交互、事件处理和动作方法
"""

from typing import Optional

from textual.events import Key
from textual.widgets import DataTable, TabbedContent, TabPane
from textual.validation import Function

from monitor.widgets.window_dialog import show_confirm_dialog
from monitor.widgets.auto_dialog import show_auto_input_dialog
from utils.global_vars import get_logger


class EventHandler:
    """
    事件处理器
    负责所有用户交互和事件处理
    """
    
    def __init__(self, app_core, app_instance):
        """初始化事件处理器"""
        self.app_core = app_core
        self.app = app_instance
        self.logger = get_logger(__name__)
        
        self.logger.info("EventHandler 初始化完成")
    
    def on_key(self, event: Key) -> None:
        """处理按键事件"""
        # 只处理退出相关的按键
        if event.key == "q":
            event.prevent_default()
            self.app.action_quit()
        elif event.key == "ctrl+c":
            event.prevent_default()
            self.app.action_quit()
        # 其他按键正常处理，不退出程序
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件"""
        try:
            # 判断是哪个表格的选择事件
            if event.data_table.id == "stock_table":
                # 股票表格选择
                row_index = event.cursor_row
                if 0 <= row_index < len(self.app_core.monitored_stocks):
                    self.app_core.current_stock_code = self.app_core.monitored_stocks[row_index]

                    self.logger.info(f"选择股票: {self.app_core.current_stock_code}")
            elif event.data_table.id == "group_table":
                # 分组表格选择 - 同步光标位置并更新预览
                self.app_core.current_group_cursor = event.cursor_row
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager:
                    await ui_manager.update_group_preview()
                self.logger.debug(f"用户点击选择分组行: {event.cursor_row}")
            elif event.data_table.id == "orders_table":
                # 订单表格选择 - 同步光标位置
                self.app_core.current_order_cursor = event.cursor_row
                self.logger.debug(f"用户点击选择订单行: {event.cursor_row}")
                # 如果有需要，这里可以添加显示订单详情的逻辑
                if 0 <= event.cursor_row < len(self.app_core.order_data):
                    selected_order = self.app_core.order_data[event.cursor_row]
                    self.logger.info(f"选择订单: {selected_order.get('order_id', 'N/A')}")
        except Exception as e:
            self.logger.error(f"处理行选择事件失败: {e}")
    
    async def action_add_stock(self) -> None:
        """添加股票动作"""
        # 使用 run_worker 来处理对话框
        self.app.run_worker(self._add_stock_worker, exclusive=True)
    
    async def _add_stock_worker(self) -> None:
        """添加股票的工作线程"""
        try:
            # 获取data_manager以便提供自动补全候选项
            data_manager = getattr(self.app_core.app, 'data_manager', None)
            candidates_callback = data_manager.get_stock_code_from_cache_full if data_manager else None
            
            # 使用WindowInputDialog获取股票代码
            stock_code = await show_auto_input_dialog(
                self.app,
                message="请输入要添加的股票代码\n格式：HK.00700 (港股) 或 US.AAPL (美股)",
                title="添加股票",
                placeholder="例如：HK.00700",
                validator=Function(self.app_core.validate_stock_code),
                required=True,
                candidates_callback=candidates_callback
            )
            
            if stock_code:
                # 格式化股票代码
                formatted_code = stock_code.upper().strip()
                
                # 检查是否已经存在
                if formatted_code in self.app_core.monitored_stocks:
                    ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                    if ui_manager and ui_manager.info_panel:
                        await ui_manager.info_panel.log_info(f"股票 {formatted_code} 已在监控列表中", "添加股票")
                    return
                
                # 确认添加
                confirmed = await show_confirm_dialog(
                    self.app,
                    message=f"确定要添加股票 {formatted_code} 到监控列表吗？",
                    title="确认添加",
                    confirm_text="添加",
                    cancel_text="取消"
                )
                
                if confirmed:
                    # 添加到监控列表
                    self.app_core.monitored_stocks.append(formatted_code)
                    
                    # 更新股票表格
                    ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                    if ui_manager:
                        await ui_manager.add_stock_to_table(formatted_code)
                    
                    # 尝试将股票添加到当前选中的分组
                    if self.app_core.selected_group_name:
                        group_manager = getattr(self.app_core.app, 'group_manager', None)
                        if group_manager:
                            success = await group_manager.add_stock_to_group(
                                self.app_core.selected_group_name, 
                                formatted_code
                            )
                            if ui_manager and ui_manager.info_panel:
                                if success:
                                    await ui_manager.info_panel.log_info(f"股票 {formatted_code} 已添加到分组 {self.app_core.selected_group_name}", "添加股票")
                                else:
                                    await ui_manager.info_panel.log_info(f"股票 {formatted_code} 添加到分组失败", "添加股票")
                    
                    # 刷新股票数据
                    data_manager = getattr(self.app_core.app, 'data_manager', None)
                    if data_manager:
                        await data_manager.refresh_stock_data()
                    
                    # 刷新用户分组数据以更新stock_list
                    group_manager = getattr(self.app_core.app, 'group_manager', None)
                    if group_manager:
                        await group_manager.refresh_user_groups()
                    
                    self.logger.info(f"成功添加股票: {formatted_code}")
                    if ui_manager and ui_manager.info_panel:
                        await ui_manager.info_panel.log_info(f"成功添加股票: {formatted_code}", "添加股票")
                    
        except Exception as e:
            self.logger.error(f"添加股票失败: {e}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"添加股票失败: {e}", "添加股票")
    
    async def action_delete_stock(self) -> None:
        """删除股票动作"""
        # 使用 run_worker 来处理对话框
        self.app.run_worker(self._delete_stock_worker, exclusive=True)
    
    async def _delete_stock_worker(self) -> None:
        """删除股票的工作线程"""
        try:
            # 检查是否有可删除的股票
            if not self.app_core.monitored_stocks:
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("监控列表为空，无法删除股票", "删除股票")
                return
                
            # 获取当前选中的股票
            current_stock = None
            if 0 <= self.app_core.current_stock_cursor < len(self.app_core.monitored_stocks):
                current_stock = self.app_core.monitored_stocks[self.app_core.current_stock_cursor]
            
            # 如果没有选中股票，让用户手动输入
            if not current_stock:
                # 获取data_manager以便提供自动补全候选项
                data_manager = getattr(self.app_core.app, 'data_manager', None)
                candidates_callback = data_manager.get_stock_code_from_cache_full if data_manager else None
                
                stock_code = await show_auto_input_dialog(
                    self.app,
                    message="请输入要删除的股票代码\n格式：HK.00700 (港股) 或 US.AAPL (美股)",
                    title="删除股票",
                    placeholder="例如：HK.00700",
                    validator=Function(self.app_core.validate_stock_code),
                    required=True,
                    candidates_callback=candidates_callback
                )
                if stock_code:
                    current_stock = stock_code.upper().strip()
            
            if not current_stock:
                return
                
            # 检查股票是否在监控列表中
            if current_stock not in self.app_core.monitored_stocks:
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info(f"股票 {current_stock} 不在监控列表中", "删除股票")
                return
            
            # 确认删除
            confirmed = await show_confirm_dialog(
                self.app,
                message=f"确定要删除股票 {current_stock} 吗？\n\n[red]警告：此操作将从监控列表中移除该股票！[/red]",
                title="确认删除",
                confirm_text="删除",
                cancel_text="取消"
            )
            
            if confirmed:
                # 从监控列表中移除
                self.app_core.monitored_stocks.remove(current_stock)
                
                # 从股票表格中删除
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager:
                    await ui_manager.remove_stock_from_table(current_stock)
                
                # 从股票数据中删除
                if current_stock in self.app_core.stock_data:
                    del self.app_core.stock_data[current_stock]
                
                # 尝试从当前选中的分组中删除
                if self.app_core.selected_group_name:
                    group_manager = getattr(self.app_core.app, 'group_manager', None)
                    if group_manager:
                        success = await group_manager.remove_stock_from_group(
                            self.app_core.selected_group_name, 
                            current_stock
                        )
                        if ui_manager and ui_manager.info_panel:
                            if success:
                                await ui_manager.info_panel.log_info(f"股票 {current_stock} 已从分组 {self.app_core.selected_group_name} 中删除", "删除股票")
                            else:
                                await ui_manager.info_panel.log_info(f"股票 {current_stock} 从分组中删除失败", "删除股票")
                
                # 更新光标位置
                if self.app_core.current_stock_cursor >= len(self.app_core.monitored_stocks):
                    self.app_core.current_stock_cursor = max(0, len(self.app_core.monitored_stocks) - 1)
                
                # 更新股票光标
                if self.app_core.monitored_stocks:
                    if ui_manager:
                        await ui_manager.update_stock_cursor()
                else:
                    self.app_core.current_stock_code = None
                
                # 刷新用户分组数据以更新stock_list
                group_manager = getattr(self.app_core.app, 'group_manager', None)
                if group_manager:
                    await group_manager.refresh_user_groups()
                
                self.logger.info(f"成功删除股票: {current_stock}")
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info(f"成功删除股票: {current_stock}", "删除股票")
                
        except Exception as e:
            self.logger.error(f"删除股票失败: {e}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"删除股票失败: {e}", "删除股票")
    
    async def action_refresh(self) -> None:
        """手动刷新动作"""
        self.logger.info("开始手动刷新数据...")
        # 向信息面板显示手动刷新开始
        ui_manager = getattr(self.app, 'ui_manager', None)
        if ui_manager and ui_manager.info_panel:
            await ui_manager.info_panel.log_info("开始手动刷新数据", "手动操作")
        
        # 直接执行数据刷新，不检查连接状态
        data_manager = getattr(self.app_core.app, 'data_manager', None)
        if data_manager:
            await data_manager.refresh_stock_data()
        
        # 更新UI状态显示
        await self.app_core.update_status_display()
        
        # 更新UI界面
        ui_manager = getattr(self.app, 'ui_manager', None)
        if ui_manager:
            await ui_manager.update_stock_table()
        
        self.logger.info("手动刷新数据完成")
        # 向信息面板显示手动刷新完成
        if ui_manager and ui_manager.info_panel:
            await ui_manager.info_panel.log_info("手动刷新数据完成", "手动操作")
    
    async def action_help(self) -> None:
        """显示帮助动作"""
        # TODO: 实现帮助对话框
        self.logger.info("帮助功能待实现")
    
    async def action_go_back(self) -> None:
        """返回主界面动作"""
        try:
            # 获取主标签页容器
            tabs = self.app.query_one("#main_tabs", TabbedContent)
            
            # 如果当前在分析界面，删除分析标签页
            if tabs.active == "analysis":
                try:
                    tabs.remove_pane("analysis")
                    self.logger.info("已关闭分析界面")
                except Exception as e:
                    self.logger.debug(f"删除分析标签页失败: {e}")
            
            # 切换到主界面标签页
            tabs.active = "main"
            
        except Exception as e:
            self.logger.error(f"返回主界面失败: {e}")
    
    async def action_switch_tab(self) -> None:
        """切换标签页动作"""
        try:
            tabs = self.app.query_one("#main_tabs", TabbedContent)
            
            if tabs.active == "main":
                # 从主界面切换，使用Space键的逻辑（智能切换）
                await self.action_select_group()
            else:
                # 从分析界面返回主界面
                await self.action_go_back()
                
        except Exception as e:
            self.logger.error(f"切换标签页失败: {e}")
    
    async def action_cursor_up(self) -> None:
        """光标向上移动 - 根据当前活跃表格决定移动哪个光标"""
        try:
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if self.app_core.active_table == "stock" and len(self.app_core.monitored_stocks) > 0:
                # 移动股票表格光标
                self.app_core.current_stock_cursor = (self.app_core.current_stock_cursor - 1) % len(self.app_core.monitored_stocks)
                if ui_manager:
                    await ui_manager.update_stock_cursor()
                self.logger.debug(f"股票光标向上移动到: {self.app_core.current_stock_cursor}")
            elif self.app_core.active_table == "group" and len(self.app_core.group_data) > 0:
                # 移动分组表格光标
                self.app_core.current_group_cursor = (self.app_core.current_group_cursor - 1) % len(self.app_core.group_data)
                if ui_manager:
                    await ui_manager.update_group_cursor()
                self.logger.debug(f"分组光标向上移动到: {self.app_core.current_group_cursor}")
            elif self.app_core.active_table == "position" and len(self.app_core.position_data) > 0:
                # 持仓表：向上移动时，如果在第一行则跳转到分组表最后一行
                if self.app_core.current_position_cursor == 0:
                    # 跳转到分组表
                    self.app_core.active_table = "group"
                    if len(self.app_core.group_data) > 0:
                        self.app_core.current_group_cursor = len(self.app_core.group_data) - 1
                    if ui_manager:
                        await ui_manager.update_table_focus()
                    self.logger.debug("持仓表第一行向上移动，跳转到分组表最后一行")
                else:
                    # 正常向上移动
                    self.app_core.current_position_cursor -= 1
                    if ui_manager:
                        await ui_manager.update_position_cursor()
                    self.logger.debug(f"持仓光标向上移动到: {self.app_core.current_position_cursor}")
            elif self.app_core.active_table == "orders" and len(self.app_core.order_data) > 0:
                # 订单表：向上移动时，如果在第一行则跳转到持仓表最后一行
                if self.app_core.current_order_cursor == 0:
                    # 跳转到持仓表
                    self.app_core.active_table = "position"
                    if len(self.app_core.position_data) > 0:
                        self.app_core.current_position_cursor = len(self.app_core.position_data) - 1
                    if ui_manager:
                        await ui_manager.update_table_focus()
                    self.logger.debug("订单表第一行向上移动，跳转到持仓表最后一行")
                else:
                    # 正常向上移动
                    self.app_core.current_order_cursor -= 1
                    if ui_manager:
                        await ui_manager.update_order_cursor()
                    self.logger.debug(f"订单光标向上移动到: {self.app_core.current_order_cursor}")
            else:
                self.logger.debug(f"当前表格({self.app_core.active_table})无数据或非活跃状态，无法移动光标")
        except Exception as e:
            self.logger.error(f"光标向上移动失败: {e}")
    
    async def action_cursor_down(self) -> None:
        """光标向下移动 - 根据当前活跃表格决定移动哪个光标"""
        try:
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if self.app_core.active_table == "stock" and len(self.app_core.monitored_stocks) > 0:
                # 移动股票表格光标
                self.app_core.current_stock_cursor = (self.app_core.current_stock_cursor + 1) % len(self.app_core.monitored_stocks)
                if ui_manager:
                    await ui_manager.update_stock_cursor()
                self.logger.debug(f"股票光标向下移动到: {self.app_core.current_stock_cursor}")
            elif self.app_core.active_table == "group" and len(self.app_core.group_data) > 0:
                # 分组表：向下移动时，如果在最后一行则跳转到持仓表第一行
                if self.app_core.current_group_cursor == len(self.app_core.group_data) - 1:
                    # 跳转到持仓表
                    self.app_core.active_table = "position"
                    self.app_core.current_position_cursor = 0
                    if ui_manager:
                        await ui_manager.update_table_focus()
                    self.logger.debug("分组表最后一行向下移动，跳转到持仓表第一行")
                else:
                    # 正常向下移动
                    self.app_core.current_group_cursor += 1
                    if ui_manager:
                        await ui_manager.update_group_cursor()
                    self.logger.debug(f"分组光标向下移动到: {self.app_core.current_group_cursor}")
            elif self.app_core.active_table == "position" and len(self.app_core.position_data) > 0:
                # 持仓表：向下移动时，如果在最后一行则跳转到订单表第一行
                if self.app_core.current_position_cursor == len(self.app_core.position_data) - 1:
                    # 跳转到订单表
                    self.app_core.active_table = "orders"
                    self.app_core.current_order_cursor = 0
                    if ui_manager:
                        await ui_manager.update_table_focus()
                    self.logger.debug("持仓表最后一行向下移动，跳转到订单表第一行")
                else:
                    # 正常向下移动
                    self.app_core.current_position_cursor += 1
                    if ui_manager:
                        await ui_manager.update_position_cursor()
                    self.logger.debug(f"持仓光标向下移动到: {self.app_core.current_position_cursor}")
            elif self.app_core.active_table == "orders" and len(self.app_core.order_data) > 0:
                # 移动订单表格光标（循环移动）
                self.app_core.current_order_cursor = (self.app_core.current_order_cursor + 1) % len(self.app_core.order_data)
                if ui_manager:
                    await ui_manager.update_order_cursor()
                self.logger.debug(f"订单光标向下移动到: {self.app_core.current_order_cursor}")
            else:
                self.logger.debug(f"当前表格({self.app_core.active_table})无数据或非活跃状态，无法移动光标")
        except Exception as e:
            self.logger.error(f"光标向下移动失败: {e}")
    
    async def action_select_group(self) -> None:
        """空格键处理：根据当前活跃表格执行不同操作"""
        if self.app_core.active_table == "stock":
            # 当前在股票表格：为选中股票创建分析tab
            await self.create_stock_analysis_tab()
        elif self.app_core.active_table == "group":
            # 当前在分组表格：选择分组（原有逻辑）
            await self.select_current_group()
        elif self.app_core.active_table == "position":
            # 当前在持仓表格：触发卖出订单
            await self.action_sell_from_position()
        elif self.app_core.active_table == "orders":
            # 当前在订单表格：修改订单
            await self.action_modify_order()
    
    async def create_stock_analysis_tab(self) -> None:
        """为当前选中的股票创建分析tab"""
        try:
            if 0 <= self.app_core.current_stock_cursor < len(self.app_core.monitored_stocks):
                stock_code = self.app_core.monitored_stocks[self.app_core.current_stock_cursor]
                
                # 获取TabbedContent引用
                tabbed_content = self.app.query_one("#main_tabs", TabbedContent)
                
                # 检查是否已存在该股票的分析tab
                existing_tab_id = f"analysis_{stock_code.replace('.', '_')}"
                if tabbed_content.query(f"#{existing_tab_id}"):
                    # 如果已存在，直接激活
                    tabbed_content.active = existing_tab_id
                    self.logger.info(f"切换到已存在的分析页面: {stock_code}")
                    return
                
                # 创建分析内容
                from monitor.monitor_layout import AnalysisPanel
                analysis_content = AnalysisPanel(id="analysis_panel")
                
                # 设置应用引用
                analysis_content.set_app_reference(self.app)
                
                # 创建新的分析tab
                tab_title = f"📊 {stock_code}"
                new_pane = TabPane(tab_title, analysis_content, id=existing_tab_id)
                
                # 异步添加tab
                await tabbed_content.add_pane(new_pane)
                
                # 激活新创建的tab
                tabbed_content.active = existing_tab_id
                
                # 加载股票分析数据
                analysis_data_manager = getattr(self.app_core, 'analysis_data_manager', None)
                if analysis_data_manager:
                    # 异步设置当前股票并加载数据
                    success = await analysis_data_manager.set_current_stock(stock_code)
                    if success:
                        # 通知AnalysisPanel股票已切换
                        await analysis_content.on_stock_changed(stock_code)
                        self.logger.info(f"已为股票 {stock_code} 加载分析数据")
                    else:
                        self.logger.error(f"加载股票 {stock_code} 分析数据失败")
                else:
                    self.logger.error("AnalysisDataManager未初始化")
                
                self.logger.info(f"已创建股票分析页面: {stock_code}")
            else:
                self.logger.warning("没有选中的股票，无法创建分析页面")
        except Exception as e:
            self.logger.error(f"创建股票分析页面失败: {e}")
    
    async def select_current_group(self) -> None:
        """选择当前光标所在的分组（原有逻辑）"""
        if 0 <= self.app_core.current_group_cursor < len(self.app_core.group_data):
            group_data = self.app_core.group_data[self.app_core.current_group_cursor]
            self.app_core.selected_group_name = group_data['name']
            
            # 切换主界面监控的股票为该分组的股票
            group_manager = getattr(self.app_core.app, 'group_manager', None)
            if group_manager:
                await group_manager.switch_to_group_stocks(group_data)
                
                # 不更新分组股票显示
                #await group_manager.handle_group_selection(self.app_core.current_group_cursor)
                # 刷新用户持仓
                await group_manager.refresh_user_positions()
            
            self.logger.info(f"选择分组: {group_data['name']}, 包含 {group_data['stock_count']} 只股票")
    
    async def action_focus_left_table(self) -> None:
        """左移焦点：订单表 → 持仓表 → 分组表 → 股票表 → 订单表"""
        try:
            # 循环切换：orders → position → group → stock → orders
            if self.app_core.active_table == "orders":
                self.app_core.active_table = "position"
            elif self.app_core.active_table == "position":
                self.app_core.active_table = "group"
            elif self.app_core.active_table == "group":
                self.app_core.active_table = "stock"
            elif self.app_core.active_table == "stock":
                self.app_core.active_table = "orders"
            else:
                # 默认回到股票表
                self.app_core.active_table = "stock"

            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager:
                await ui_manager.update_table_focus()
            self.logger.debug(f"焦点左移切换到 {self.app_core.active_table} 表格")
        except Exception as e:
            self.logger.error(f"焦点左移切换失败: {e}")

    async def action_focus_right_table(self) -> None:
        """右移焦点：股票表 → 分组表 → 持仓表 → 订单表 → 股票表"""
        try:
            # 循环切换：stock → group → position → orders → stock
            if self.app_core.active_table == "stock":
                self.app_core.active_table = "group"
            elif self.app_core.active_table == "group":
                self.app_core.active_table = "position"
            elif self.app_core.active_table == "position":
                self.app_core.active_table = "orders"
            elif self.app_core.active_table == "orders":
                self.app_core.active_table = "stock"
            else:
                # 默认回到股票表
                self.app_core.active_table = "stock"

            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager:
                await ui_manager.update_table_focus()
            self.logger.debug(f"焦点右移切换到 {self.app_core.active_table} 表格")
        except Exception as e:
            self.logger.error(f"焦点右移切换失败: {e}")

    async def action_focus_orders_table(self) -> None:
        """切换焦点到订单表格"""
        try:
            if self.app_core.active_table != "orders":
                self.app_core.active_table = "orders"
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager:
                    await ui_manager.update_table_focus()
                self.logger.debug("焦点切换到订单表格")
        except Exception as e:
            self.logger.error(f"切换焦点到订单表格失败: {e}")

    async def action_sell_from_position(self) -> None:
        """从持仓表卖出 - 弹出卖出对话框"""
        self.app.run_worker(self._sell_from_position_worker, exclusive=True)

    async def _sell_from_position_worker(self) -> None:
        """从持仓表卖出的工作线程"""
        try:
            # 检查是否有持仓数据
            if not self.app_core.position_data or len(self.app_core.position_data) == 0:
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("没有持仓数据，无法卖出", "卖出操作")
                return

            # 获取当前选中的持仓
            if not (0 <= self.app_core.current_position_cursor < len(self.app_core.position_data)):
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("请选择要卖出的持仓", "卖出操作")
                return

            selected_position = self.app_core.position_data[self.app_core.current_position_cursor]

            # 提取持仓信息
            stock_code = selected_position.get('stock_code', '')
            stock_name = selected_position.get('stock_name', '')
            can_sell_qty = int(selected_position.get('can_sell_qty', 0))
            nominal_price = selected_position.get('nominal_price', 0)

            # 检查可卖数量
            if can_sell_qty <= 0:
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_warning(
                        f"股票 {stock_code} ({stock_name}) 可卖数量为0，无法卖出",
                        "卖出操作"
                    )
                return

            self.logger.info(f"准备卖出持仓: {stock_code} ({stock_name}), 可卖数量: {can_sell_qty}, 当前价: {nominal_price}")

            # 构建默认值字典
            default_values = {
                "code": stock_code,
                "price": nominal_price,
                "qty": can_sell_qty,
                "trd_side": "SELL"  # 强制设置为卖出
            }

            # 导入并显示下单对话框
            from monitor.widgets.order_dialog import show_place_order_dialog

            order_data = await show_place_order_dialog(
                app=self.app,
                title=f"卖出 - {stock_code} ({stock_name})",
                default_values=default_values,
                submit_callback=self._handle_place_submit,
                cancel_callback=self._handle_place_cancel
            )

            if order_data:
                self.logger.info(f"卖出订单数据已收集: {order_data}")
                # 提交订单请求
                await self._submit_place_order(order_data)
            else:
                self.logger.info("用户取消了卖出操作")

        except Exception as e:
            self.logger.error(f"卖出持仓失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"卖出持仓失败: {e}", "卖出操作")

    async def action_place_order(self) -> None:
        """新订单动作 - 弹出下单对话框"""
        self.app.run_worker(self._place_order_worker, exclusive=True)

    async def _place_order_worker(self) -> None:
        """新订单的工作线程"""
        try:
            # 获取当前选中的股票代码作为默认值
            default_stock_code = None
            if self.app_core.active_table == "stock" and 0 <= self.app_core.current_stock_cursor < len(self.app_core.monitored_stocks):
                default_stock_code = self.app_core.monitored_stocks[self.app_core.current_stock_cursor]

            self.logger.info(f"准备创建新订单，默认股票: {default_stock_code}")

            # 构建默认值字典
            default_values = {}
            if default_stock_code:
                default_values["code"] = default_stock_code

                # 尝试获取股票的当前价格作为默认价格
                if default_stock_code in self.app_core.stock_data:
                    stock_info = self.app_core.stock_data[default_stock_code]
                    if stock_info and hasattr(stock_info, 'current_price'):
                        default_values["price"] = stock_info.current_price

            # 导入并显示下单对话框
            from monitor.widgets.order_dialog import show_place_order_dialog

            order_data = await show_place_order_dialog(
                app=self.app,
                title="新建订单",
                default_values=default_values,
                submit_callback=self._handle_place_submit,
                cancel_callback=self._handle_place_cancel
            )

            if order_data:
                self.logger.info(f"订单数据已收集: {order_data}")
                # 提交订单请求
                await self._submit_place_order(order_data)
            else:
                self.logger.info("用户取消了下单操作")

        except Exception as e:
            self.logger.error(f"创建订单失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"创建订单失败: {e}", "下单操作")

    def _handle_place_submit(self, order_data) -> None:
        """下单提交回调函数"""
        self.logger.info(f"下单提交回调: {order_data}")

    def _handle_place_cancel(self) -> None:
        """下单取消回调函数"""
        self.logger.info("用户取消下单操作")

    async def _submit_place_order(self, order_data) -> None:
        """提交下单请求到富途API"""
        try:
            from base.order import OrderData

            # 确保order_data是OrderData对象
            if not isinstance(order_data, OrderData):
                self.logger.error(f"下单数据格式错误: {type(order_data)}")
                return

            # 获取futu_trade实例
            data_manager = getattr(self.app_core.app, 'data_manager', None)
            if not data_manager:
                self.logger.error("DataManager未初始化")
                return

            futu_trade = getattr(data_manager, 'futu_trade', None)
            if not futu_trade:
                self.logger.error("FutuTrade未初始化")
                return

            # 调用下单API
            self.logger.info(f"调用下单API: code={order_data.code}, "
                           f"price={order_data.price}, qty={order_data.qty}, "
                           f"trd_side={order_data.trd_side}, order_type={order_data.order_type}")

            result = futu_trade.place_order(
                code=order_data.code,
                price=order_data.price,
                qty=order_data.qty,
                trd_side=order_data.trd_side,
                order_type=order_data.order_type,
                trd_env=order_data.trd_env,
                market=order_data.market
            )

            # 处理结果
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if isinstance(result, dict) and result.get('success', False):
                # 下单成功
                order_id = result.get('order_id', 'N/A')
                self.logger.info(f"下单成功: {result}")
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info(
                        f"订单 {order_id} 创建成功 - {order_data.code} {order_data.trd_side} {order_data.qty}股 @ {order_data.price}",
                        "下单操作"
                    )

                # 刷新订单数据
                group_manager = getattr(self.app_core.app, 'group_manager', None)
                if group_manager:
                    await group_manager.refresh_user_orders()
                if ui_manager:
                    await ui_manager.update_orders_table()
            else:
                # 下单失败
                error_msg = result.get('message', str(result)) if isinstance(result, dict) else str(result)
                self.logger.error(f"下单失败: {error_msg}")
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info(
                        f"订单创建失败: {error_msg}",
                        "下单操作"
                    )

        except Exception as e:
            self.logger.error(f"提交下单请求失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"提交下单请求失败: {e}", "下单操作")

    async def action_modify_order(self) -> None:
        """修改订单动作 - 弹出改单对话框"""
        self.app.run_worker(self._modify_order_worker, exclusive=True)

    async def _modify_order_worker(self) -> None:
        """修改订单的工作线程"""
        try:
            # 检查订单表格是否为活跃表格
            if self.app_core.active_table != "orders":
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("请先切换到订单表格", "改单操作")
                return

            # 检查是否有订单数据
            if not self.app_core.order_data or len(self.app_core.order_data) == 0:
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("没有可修改的订单", "改单操作")
                return

            # 获取当前选中的订单
            if not (0 <= self.app_core.current_order_cursor < len(self.app_core.order_data)):
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info("请选择要修改的订单", "改单操作")
                return

            selected_order = self.app_core.order_data[self.app_core.current_order_cursor]

            # 提取订单关键信息
            order_id = selected_order.get('order_id', '')
            current_price = selected_order.get('price', None)
            current_qty = selected_order.get('qty', None)
            stock_code = selected_order.get('code', '')

            self.logger.info(f"准备修改订单: {order_id}, 股票: {stock_code}, 价格: {current_price}, 数量: {current_qty}")

            # 导入并显示改单对话框
            from monitor.widgets.order_dialog import show_modify_order_dialog

            modify_data = await show_modify_order_dialog(
                app=self.app,
                title=f"修改订单 - {stock_code}",
                order_id=order_id,
                current_price=current_price,
                current_qty=current_qty,
                submit_callback=self._handle_modify_submit,
                cancel_callback=self._handle_modify_cancel
            )

            if modify_data:
                self.logger.info(f"改单数据已收集: {modify_data}")
                # 提交改单请求
                await self._submit_modify_order(modify_data)
            else:
                self.logger.info("用户取消了改单操作")

        except Exception as e:
            self.logger.error(f"修改订单失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"修改订单失败: {e}", "改单操作")

    def _handle_modify_submit(self, modify_data) -> None:
        """改单提交回调函数"""
        self.logger.info(f"改单提交回调: {modify_data}")

    def _handle_modify_cancel(self) -> None:
        """改单取消回调函数"""
        self.logger.info("用户取消改单操作")

    async def _submit_modify_order(self, modify_data) -> None:
        """提交改单请求到富途API"""
        try:
            from base.order import ModifyOrderData

            # 确保modify_data是ModifyOrderData对象
            if not isinstance(modify_data, ModifyOrderData):
                self.logger.error(f"改单数据格式错误: {type(modify_data)}")
                return

            # 获取futu_trade实例
            data_manager = getattr(self.app_core.app, 'data_manager', None)
            if not data_manager:
                self.logger.error("DataManager未初始化")
                return

            futu_trade = getattr(data_manager, 'futu_trade', None)
            if not futu_trade:
                self.logger.error("FutuTrade未初始化")
                return

            # 调用改单API
            self.logger.info(f"调用改单API: order_id={modify_data.order_id}, "
                           f"price={modify_data.price}, qty={modify_data.qty}")

            result = futu_trade.modify_order(
                order_id=modify_data.order_id,
                price=modify_data.price,
                qty=modify_data.qty,
                trd_env=None,
                market=None
            )

            # 处理结果
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if isinstance(result, dict) and result.get('success', False):
                # 改单成功
                self.logger.info(f"改单成功: {result}")
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_info(
                        f"订单 {modify_data.order_id} 修改成功",
                        "改单操作"
                    )

                # 刷新订单数据
                group_manager = getattr(self.app_core.app, 'group_manager', None)
                if group_manager:
                    await group_manager.refresh_user_orders()
                if ui_manager:
                    await ui_manager.update_orders_table()
            else:
                # 改单失败
                error_msg = result.get('message', str(result)) if isinstance(result, dict) else str(result)
                self.logger.error(f"改单失败: {error_msg}")
                if ui_manager and ui_manager.info_panel:
                    await ui_manager.info_panel.log_warning(
                        f"订单 {modify_data.order_id} 修改失败: {error_msg}",
                        "改单操作"
                    )

        except Exception as e:
            self.logger.error(f"提交改单请求失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager and ui_manager.info_panel:
                await ui_manager.info_panel.log_info(f"提交改单请求失败: {e}", "改单操作")

