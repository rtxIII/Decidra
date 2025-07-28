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
from utils.logger import get_logger


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
    
    async def action_help(self) -> None:
        """显示帮助动作"""
        # TODO: 实现帮助对话框
        self.logger.info("帮助功能待实现")
    
    async def action_go_back(self) -> None:
        """返回主界面动作"""
        # 切换到主界面标签页
        tabs = self.app.query_one(TabbedContent)
        tabs.active = "main"
    
    async def action_switch_tab(self) -> None:
        """切换标签页动作"""
        tabs = self.app.query_one(TabbedContent)
        if tabs.active == "main":
            tabs.active = "analysis"
        else:
            tabs.active = "main"
    
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
                # 移动分组表格光标
                self.app_core.current_group_cursor = (self.app_core.current_group_cursor + 1) % len(self.app_core.group_data)
                if ui_manager:
                    await ui_manager.update_group_cursor()
                self.logger.debug(f"分组光标向下移动到: {self.app_core.current_group_cursor}")
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
                from monitor.ui import AnalysisPanel
                analysis_content = AnalysisPanel(id="analysis_panel")
                
                # 创建新的分析tab
                tab_title = f"📊 {stock_code}"
                new_pane = TabPane(tab_title, analysis_content, id=existing_tab_id)
                
                # 异步添加tab
                await tabbed_content.add_pane(new_pane)
                
                # 激活新创建的tab
                tabbed_content.active = existing_tab_id
                
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
                
                # 同时更新分组股票显示
                await group_manager.handle_group_selection(self.app_core.current_group_cursor)
            
            self.logger.info(f"选择分组: {group_data['name']}, 包含 {group_data['stock_count']} 只股票")
    
    async def action_focus_left_table(self) -> None:
        """左移焦点到股票表格"""
        try:
            if self.app_core.active_table != "stock":
                self.app_core.active_table = "stock"
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager:
                    await ui_manager.update_table_focus()
                self.logger.debug("焦点切换到股票表格")
        except Exception as e:
            self.logger.error(f"切换焦点到股票表格失败: {e}")
    
    async def action_focus_right_table(self) -> None:
        """右移焦点到分组表格"""
        try:
            if self.app_core.active_table != "group":
                self.app_core.active_table = "group"
                ui_manager = getattr(self.app_core.app, 'ui_manager', None)
                if ui_manager:
                    await ui_manager.update_table_focus()
                self.logger.debug("焦点切换到分组表格")
        except Exception as e:
            self.logger.error(f"切换焦点到分组表格失败: {e}")
    
    async def action_enter_analysis(self) -> None:
        """进入分析界面动作"""
        if self.app_core.current_stock_code:
            # 切换到分析标签页
            tabs = self.app.query_one(TabbedContent)
            tabs.active = "analysis"
            
            # 更新分析界面内容
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if ui_manager:
                await ui_manager.update_analysis_interface()
            
            self.logger.info(f"进入分析界面: {self.app_core.current_stock_code}")