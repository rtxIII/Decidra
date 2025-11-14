"""
TabStateManager - 分析标签页状态管理模块

基于JsonLiteManager实现分析标签页状态的保存和恢复功能
只处理分析标签页，不处理主界面标签页
恢复时保持激活标签页在主界面
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from utils.global_vars import get_logger
from modules.jsonlite_data import JsonLiteManager


class TabStateManager:
    """
    分析标签页状态管理器
    负责分析标签页状态的保存、加载和恢复
    只处理分析标签页，跳过主界面标签页
    """
    
    # 配置键名
    TAB_STATE_CONFIG_KEY = "ui_tab_state"
    
    def __init__(self, app_core):
        """初始化标签页状态管理器"""
        self.app_core = app_core
        self.app = app_core.app
        self.logger = get_logger(__name__)
        
        # 初始化JsonLite管理器
        self.json_manager = JsonLiteManager("decidra_ui_state.json")
        
        self.logger.info("TabStateManager 初始化完成")
    
    async def save_tab_state(self) -> bool:
        """
        保存当前标签页状态
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 获取当前标签页状态
            tab_state = await self._collect_current_tab_state()
            
            if not tab_state:
                self.logger.info("没有分析标签页需要保存")
                return True  # 没有分析标签页也算成功
            
            # 使用JsonLiteManager保存状态
            self.json_manager.save_user_config(
                self.TAB_STATE_CONFIG_KEY, 
                tab_state
            )
            
            self.logger.info(f"分析标签页状态保存成功: {len(tab_state.get('analysis_tabs', []))} 个分析标签页")
            return True
            
        except Exception as e:
            self.logger.error(f"保存标签页状态失败: {e}")
            return False
    
    async def load_tab_state(self) -> Optional[Dict[str, Any]]:
        """
        加载标签页状态
        
        Returns:
            Optional[Dict]: 标签页状态数据，加载失败返回None
        """
        try:
            tab_state = self.json_manager.get_user_config(
                self.TAB_STATE_CONFIG_KEY, 
                None
            )
            
            if tab_state:
                self.logger.info(f"分析标签页状态加载成功: {len(tab_state.get('analysis_tabs', []))} 个分析标签页")
                return tab_state
            else:
                self.logger.info("没有找到保存的分析标签页状态")
                return None
            
        except Exception as e:
            self.logger.error(f"加载标签页状态失败: {e}")
            return None
    
    async def restore_tab_state(self) -> bool:
        """
        恢复标签页状态
        
        Returns:
            bool: 恢复是否成功
        """
        try:
            # 加载保存的状态
            tab_state = await self.load_tab_state()
            if not tab_state:
                return False
            
            # 验证状态数据
            if not self._validate_tab_state(tab_state):
                self.logger.warning("标签页状态数据无效，跳过恢复")
                return False
            
            # 恢复标签页
            success = await self._restore_tabs_from_state(tab_state)
            
            if success:
                self.logger.info("分析标签页状态恢复成功")
                # 记录到分析面板信息
                if hasattr(self.app_core.app, 'lifecycle_manager'):
                    await self.app_core.app.lifecycle_manager.log_to_analysis_info_panel(
                        "分析标签页状态已恢复", "系统"
                    )
            else:
                self.logger.warning("分析标签页状态恢复失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"恢复标签页状态失败: {e}")
            return False
    
    async def _collect_current_tab_state(self) -> Optional[Dict[str, Any]]:
        """收集当前标签页状态（只收集分析标签页）"""
        try:
            # 获取主标签页容器
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                return None
            
            # 获取所有标签页
            all_panes = list(main_tabs.query("TabPane"))
            analysis_tabs = []
            
            for pane in all_panes:
                tab_id = pane.id
                if not tab_id:
                    continue
                
                # 只收集分析标签页，跳过main主界面
                if tab_id.startswith("analysis_"):
                    # 提取股票代码
                    stock_code = tab_id.replace("analysis_", "")
                    analysis_tabs.append({
                        "id": tab_id,
                        "type": "analysis", 
                        "stock_code": stock_code,
                        "title": f"分析 - {stock_code}"
                    })
            
            # 如果没有分析标签页，返回None
            if not analysis_tabs:
                return None
            
            tab_state = {
                "analysis_tabs": analysis_tabs,
                "save_time": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            return tab_state
            
        except Exception as e:
            self.logger.error(f"收集标签页状态失败: {e}")
            return None
    
    def _validate_tab_state(self, tab_state: Dict[str, Any]) -> bool:
        """验证分析标签页状态数据"""
        try:
            # 检查必需的键
            required_keys = ["analysis_tabs", "save_time"]
            for key in required_keys:
                if key not in tab_state:
                    self.logger.warning(f"分析标签页状态缺少必需键: {key}")
                    return False
            
            # 检查分析标签页数据
            analysis_tabs = tab_state.get("analysis_tabs", [])
            if not isinstance(analysis_tabs, list):
                self.logger.warning("分析标签页数据格式无效")
                return False
            
            # 检查是否有分析标签页
            if not analysis_tabs:
                self.logger.warning("没有分析标签页需要恢复")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证分析标签页状态失败: {e}")
            return False
    
    async def _restore_tabs_from_state(self, tab_state: Dict[str, Any]) -> bool:
        """从状态数据恢复分析标签页"""
        try:
            analysis_tabs = tab_state.get("analysis_tabs", [])
            
            # 获取主标签页容器
            main_tabs = self.app.query_one("#main_tabs", expect_type=None)
            if not main_tabs:
                self.logger.error("找不到主标签页容器")
                return False
            
            # 恢复分析标签页
            restored_count = 0
            for tab in analysis_tabs:
                if tab.get("type") == "analysis":
                    stock_code = tab.get("stock_code")
                    if stock_code:
                        success = await self._restore_analysis_tab(stock_code)
                        if success:
                            restored_count += 1
            
            # 等待标签页创建完成
            if restored_count > 0:
                await asyncio.sleep(0.5)  # 给标签页创建一些时间
            
            # 确保激活标签页在主界面
            try:
                main_tabs.active = "main"
                self.logger.info("设置激活标签页为主界面")
                    
            except Exception as e:
                self.logger.warning(f"设置激活标签页失败: {e}")
            
            self.logger.info(f"成功恢复 {restored_count} 个分析标签页")
            return True
            
        except Exception as e:
            self.logger.error(f"从状态恢复标签页失败: {e}")
            return False
    
    async def _restore_analysis_tab(self, stock_code: str) -> bool:
        """恢复单个分析标签页"""
        try:
            # 检查UI管理器是否可用
            ui_manager = getattr(self.app_core.app, 'ui_manager', None)
            if not ui_manager:
                self.logger.error("UI管理器不可用，无法恢复分析标签页")
                return False
            
            # 使用UI管理器的方法创建分析标签页
            success = await ui_manager.create_analysis_tab(stock_code)
            
            if success:
                self.logger.info(f"成功恢复分析标签页: {stock_code}")
                
                # 记录到分析面板信息
                if hasattr(self.app_core.app, 'lifecycle_manager'):
                    await self.app_core.app.lifecycle_manager.log_to_analysis_info_panel(
                        f"恢复分析标签页: {stock_code}", "系统"
                    )
            else:
                self.logger.warning(f"恢复分析标签页失败: {stock_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"恢复分析标签页 {stock_code} 失败: {e}")
            return False
    
    async def clear_saved_state(self) -> bool:
        """清除保存的标签页状态"""
        try:
            # 删除配置
            result = self.json_manager.delete_one({
                'type': 'user_config',
                'config_key': self.TAB_STATE_CONFIG_KEY
            })
            
            if result:
                self.logger.info("已清除保存的标签页状态")
                return True
            else:
                self.logger.info("没有找到需要清除的标签页状态")
                return True  # 没有状态也算成功
                
        except Exception as e:
            self.logger.error(f"清除保存的标签页状态失败: {e}")
            return False
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        try:
            tab_state = self.json_manager.get_user_config(
                self.TAB_STATE_CONFIG_KEY, 
                None
            )
            
            if tab_state:
                return {
                    "has_saved_state": True,
                    "analysis_tab_count": len(tab_state.get("analysis_tabs", [])),
                    "save_time": tab_state.get("save_time", "unknown"),
                    "version": tab_state.get("version", "unknown")
                }
            else:
                return {
                    "has_saved_state": False,
                    "analysis_tab_count": 0,
                    "save_time": None,
                    "version": None
                }
                
        except Exception as e:
            self.logger.error(f"获取状态信息失败: {e}")
            return {
                "has_saved_state": False,
                "error": str(e)
            }