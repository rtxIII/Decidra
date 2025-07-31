"""
数据流管理模块
提供数据处理流程协调和连接管理功能
"""

from typing import List
import asyncio
import logging

from base.monitor import (
    DataUpdateResult, ConnectionStatus, ErrorCode
)
from modules.futu_market import FutuMarket
from .indicators import IndicatorsManager


logger = logging.getLogger(__name__)


class DataFlowManager:
    """数据流管理器 - 协调所有数据处理流程"""
    
    def __init__(self, futu_market=None):
        if futu_market is not None:
            # 使用传入的共享实例
            self.futu_market = futu_market
        else:
            # 如果没有传入，创建新实例（向后兼容）
            from modules.futu_market import FutuMarket
            self.futu_market = FutuMarket()
        
        self.indicators_manager = IndicatorsManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._running_tasks = set()  # 跟踪运行中的任务
    
    def close(self):
        self.futu_market.close()
        
    
    async def data_update_cycle(self, stock_codes: List[str]) -> DataUpdateResult:
        """
        数据更新周期
        
        执行流程:
        1. 获取监控股票列表 -> get_watch_list()
        2. 并发获取实时数据 -> get_real_time_quotes(stock_codes)
        3. 更新历史数据缓存 -> update_cache(stock_data)
        4. 计算技术指标 -> calculate_indicators(stock_codes)
        5. 数据验证和清洗 -> validate_data(data)
        6. 通知界面更新 -> notify_ui_update(processed_data)
        
        数据流转图:
        富途API -> 实时数据 -> 数据验证 -> 缓存更新 -> 指标计算 -> 界面更新
        """
        task = asyncio.current_task()
        if task:
            self._running_tasks.add(task)
        
        try:
            # 1. 获取实时数据
            loop = asyncio.get_event_loop()
            market_snapshots = await loop.run_in_executor(
                None,
                self.futu_market.get_market_snapshot,
                stock_codes
            )
            
            # 2. 计算技术指标
            indicators_data = await self.indicators_manager.update_all_indicators(stock_codes)
            
            # 3. 返回更新结果
            return DataUpdateResult(
                success=True,
                stock_data=stock_data,
                indicators_data=indicators_data
            )
            
        except Exception as e:
            self.logger.error(f"数据更新周期失败: {e}")
            return DataUpdateResult(
                success=False,
                stock_data={},
                indicators_data={},
                error_message=str(e)
            )
        finally:
            if task:
                self._running_tasks.discard(task)
    
    async def cleanup(self):
        """清理数据流管理器的所有资源"""
        self.logger.info("开始清理 DataFlowManager...")
        
        try:
            # 1. 取消所有跟踪的任务
            if self._running_tasks:
                self.logger.info(f"取消 {len(self._running_tasks)} 个运行中的任务")
                
                # 创建任务列表副本，避免在迭代时修改集合
                tasks_to_cancel = list(self._running_tasks)
                
                for task in tasks_to_cancel:
                    if not task.done():
                        task.cancel()
                        self.logger.debug(f"已取消任务: {task}")
                
                # 等待任务取消完成
                if tasks_to_cancel:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                            timeout=1.5  # 缩短到1.5秒
                        )
                        self.logger.info("所有任务取消完成")
                    except asyncio.TimeoutError:
                        self.logger.warning("部分任务取消超时")
                
                # 清空任务集合
                self._running_tasks.clear()
            
            # 2. 清理富途市场连接（如果不是共享实例）
            if hasattr(self, 'futu_market') and self.futu_market:
                # 检查是否为自己创建的实例（非共享）
                if not hasattr(self.futu_market, '_is_shared_instance'):
                    try:
                        self.futu_market.close()
                        self.logger.info("富途市场连接已关闭")
                    except Exception as e:
                        self.logger.warning(f"关闭富途市场连接失败: {e}")
                else:
                    self.logger.info("跳过共享富途实例的关闭")
            
            # 3. 清理指标管理器
            if hasattr(self.indicators_manager, 'cleanup'):
                try:
                    await self.indicators_manager.cleanup()
                    self.logger.info("指标管理器清理完成")
                except Exception as e:
                    self.logger.warning(f"指标管理器清理失败: {e}")
            
            self.logger.info("DataFlowManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"DataFlowManager 清理过程中出错: {e}")
            raise


class ConnectionManager:
    """连接管理器"""
    
    def __init__(self, futu_client):
        self.client = futu_client
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.retry_count = 0
        self.max_retries = 3
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def ensure_connection(self) -> bool:
        """
        确保API连接正常
        
        输出数据: bool - 连接是否成功
        
        处理流程:
        1. 检查当前连接状态
        2. 如果断开则尝试重连
        3. 更新连接状态
        4. 记录错误日志
        """
        try:
            # 实际实现需要根据富途API连接检查方式
            # if self.client.is_connected():
            #     self.connection_status = ConnectionStatus.CONNECTED
            #     return True
            
            # 模拟连接检查
            self.connection_status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            self.logger.error(f"连接检查失败: {e}")
            self.connection_status = ConnectionStatus.ERROR
            return False
        
    async def handle_api_error(self, error: Exception, operation: str) -> bool:
        """
        处理API错误
        
        输入数据: error - 异常对象, operation - 操作名称
        输出数据: bool - 是否应该重试
        
        错误类型处理:
        1. 网络连接错误 -> 自动重连
        2. API限流错误 -> 等待后重试
        3. 权限错误 -> 停止操作，记录日志
        4. 数据错误 -> 跳过该次请求
        """
        error_msg = str(error)
        
        if "network" in error_msg.lower() or "connection" in error_msg.lower():
            self.logger.warning(f"{ErrorCode.get_message(ErrorCode.NETWORK_ERROR)} - {operation}")
            return await self._retry_with_backoff()
            
        elif "limit" in error_msg.lower() or "rate" in error_msg.lower():
            self.logger.warning(f"{ErrorCode.get_message(ErrorCode.API_LIMIT_ERROR)} - {operation}")
            await asyncio.sleep(5)  # 等待5秒
            return True
            
        elif "permission" in error_msg.lower() or "auth" in error_msg.lower():
            self.logger.error(f"{ErrorCode.get_message(ErrorCode.PERMISSION_ERROR)} - {operation}")
            return False
            
        else:
            self.logger.error(f"{ErrorCode.get_message(ErrorCode.DATA_ERROR)} - {operation}: {error}")
            return False
    
    async def _retry_with_backoff(self) -> bool:
        """带退避策略的重试"""
        if self.retry_count >= self.max_retries:
            self.logger.error(f"重试次数超过限制: {self.max_retries}")
            return False
            
        self.retry_count += 1
        wait_time = 2 ** self.retry_count  # 指数退避
        await asyncio.sleep(wait_time)
        
        return await self.ensure_connection()