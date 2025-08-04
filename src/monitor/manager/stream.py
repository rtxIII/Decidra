"""
实时数据流管理器 - 类似浏览器的实时更新机制

该模块提供多频率数据流，支持不同数据类型的差异化更新策略。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Set, List
from dataclasses import dataclass, field
from enum import Enum


class StreamStatus(Enum):
    """数据流状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StreamConfig:
    """数据流配置"""
    name: str
    interval: float  # 更新间隔（秒）
    retry_count: int = 3
    timeout: float = 10.0
    enabled: bool = True


@dataclass
class StreamStats:
    """数据流统计"""
    name: str
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    update_count: int = 0
    error_count: int = 0
    success_rate: float = 0.0
    average_latency: float = 0.0
    total_latency: float = 0.0


class RealTimeDataStreamManager:
    """实时数据流管理器 - 类似浏览器的实时更新机制"""

    def __init__(self, analysis_data_manager=None, data_event_bus=None, data_cache_manager=None):
        self.analysis_data_manager = analysis_data_manager
        self.data_event_bus = data_event_bus
        self.data_cache_manager = data_cache_manager
        
        # 数据流配置
        self.stream_configs = {
            'quote': StreamConfig('quote', 1.0),        # 报价1秒更新
            'orderbook': StreamConfig('orderbook', 1.0), # 五档1秒更新
            'tick': StreamConfig('tick', 0.5),          # 逐笔0.5秒更新
            'kline': StreamConfig('kline', 60.0),       # K线1分钟更新
            'broker_queue': StreamConfig('broker_queue', 2.0), # 经纪队列2秒更新
            'capital_flow': StreamConfig('capital_flow', 5.0), # 资金流向5秒更新
        }
        
        # 运行时状态
        self.active_subscriptions: Dict[str, Set[str]] = {}  # stream_type -> set of stock_codes
        self.stream_tasks: Dict[str, asyncio.Task] = {}
        self.stream_stats: Dict[str, StreamStats] = {}
        self.stream_status: Dict[str, StreamStatus] = {}
        
        # 回调函数
        self.data_callbacks: Dict[str, List[Callable]] = {}
        
        # 全局状态
        self.is_running = False
        self.current_stock_code: Optional[str] = None
        
        self.logger = logging.getLogger(__name__)

    async def start_realtime_updates(self, stock_code: str) -> bool:
        """启动实时数据更新 - 类似浏览器页面加载"""
        try:
            if not stock_code:
                self.logger.error("股票代码为空，无法启动实时更新")
                return False

            self.logger.info(f"启动实时数据流: {stock_code}")
            self.current_stock_code = stock_code
            self.is_running = True

            # 初始化统计信息
            for stream_name in self.stream_configs.keys():
                if stream_name not in self.stream_stats:
                    self.stream_stats[stream_name] = StreamStats(stream_name)
                self.stream_status[stream_name] = StreamStatus.STARTING

            # 启动各类数据的实时更新任务
            success_count = 0
            for stream_name, config in self.stream_configs.items():
                if config.enabled:
                    success = await self._start_stream(stream_name, stock_code)
                    if success:
                        success_count += 1

            # 发布启动完成事件
            if self.data_event_bus:
                await self.data_event_bus.publish('realtime_streams_started', {
                    'stock_code': stock_code,
                    'streams_started': success_count,
                    'total_streams': len([c for c in self.stream_configs.values() if c.enabled])
                })

            self.logger.info(f"实时数据流启动完成: {stock_code}, 成功启动 {success_count} 个流")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"启动实时数据流失败: {e}")
            return False

    async def stop_all_streams(self) -> None:
        """停止所有实时更新 - 类似浏览器页面卸载"""
        try:
            if not self.is_running:
                return

            self.logger.info("停止所有实时数据流")
            self.is_running = False

            # 停止所有任务
            stop_tasks = []
            for stream_name in list(self.stream_tasks.keys()):
                stop_tasks.append(self._stop_stream(stream_name))

            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)

            # 清理状态
            self.active_subscriptions.clear()
            self.current_stock_code = None

            # 发布停止事件
            if self.data_event_bus:
                await self.data_event_bus.publish('realtime_streams_stopped', {
                    'timestamp': datetime.now()
                })

            self.logger.info("所有实时数据流已停止")

        except Exception as e:
            self.logger.error(f"停止实时数据流失败: {e}")

    async def pause_stream(self, stream_name: str) -> bool:
        """暂停指定数据流"""
        try:
            if stream_name in self.stream_tasks:
                self.stream_status[stream_name] = StreamStatus.PAUSED
                self.logger.info(f"数据流已暂停: {stream_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"暂停数据流失败 [{stream_name}]: {e}")
            return False

    async def resume_stream(self, stream_name: str) -> bool:
        """恢复指定数据流"""
        try:
            if stream_name in self.stream_status and self.stream_status[stream_name] == StreamStatus.PAUSED:
                self.stream_status[stream_name] = StreamStatus.RUNNING
                self.logger.info(f"数据流已恢复: {stream_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"恢复数据流失败 [{stream_name}]: {e}")
            return False

    async def _start_stream(self, stream_name: str, stock_code: str) -> bool:
        """启动单个数据流"""
        try:
            # 创建并启动任务
            if stream_name == 'quote':
                task = asyncio.create_task(self._update_quote_stream(stock_code))
            elif stream_name == 'orderbook':
                task = asyncio.create_task(self._update_orderbook_stream(stock_code))
            elif stream_name == 'tick':
                task = asyncio.create_task(self._update_tick_stream(stock_code))
            elif stream_name == 'kline':
                task = asyncio.create_task(self._update_kline_stream(stock_code))
            elif stream_name == 'broker_queue':
                task = asyncio.create_task(self._update_broker_queue_stream(stock_code))
            elif stream_name == 'capital_flow':
                task = asyncio.create_task(self._update_capital_flow_stream(stock_code))
            else:
                self.logger.warning(f"未知的数据流类型: {stream_name}")
                return False

            self.stream_tasks[stream_name] = task
            self.stream_status[stream_name] = StreamStatus.RUNNING
            self.stream_stats[stream_name].start_time = datetime.now()

            # 添加订阅
            if stream_name not in self.active_subscriptions:
                self.active_subscriptions[stream_name] = set()
            self.active_subscriptions[stream_name].add(stock_code)

            self.logger.debug(f"数据流已启动: {stream_name} -> {stock_code}")
            return True

        except Exception as e:
            self.logger.error(f"启动数据流失败 [{stream_name}]: {e}")
            self.stream_status[stream_name] = StreamStatus.ERROR
            return False

    async def _stop_stream(self, stream_name: str) -> None:
        """停止单个数据流"""
        try:
            task = self.stream_tasks.get(stream_name)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 清理状态
            self.stream_tasks.pop(stream_name, None)
            self.stream_status[stream_name] = StreamStatus.STOPPED
            self.active_subscriptions.pop(stream_name, None)

            self.logger.debug(f"数据流已停止: {stream_name}")

        except Exception as e:
            self.logger.error(f"停止数据流失败 [{stream_name}]: {e}")

    async def _update_quote_stream(self, stock_code: str) -> None:
        """报价数据流更新"""
        stream_name = 'quote'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                # 检查是否暂停
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(1.0)
                    continue

                start_time = datetime.now()

                # 获取报价数据
                quote_data = await self._get_quote_data(stock_code)
                
                if quote_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"quote_{stock_code}", quote_data, "quote", "hot"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('realtime_quote', {
                            'stock_code': stock_code,
                            'data': quote_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"报价数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)  # 错误后加倍等待时间

        self.logger.debug(f"报价数据流已退出: {stock_code}")

    async def _update_orderbook_stream(self, stock_code: str) -> None:
        """五档数据流更新"""
        stream_name = 'orderbook'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(1.0)
                    continue

                start_time = datetime.now()

                # 获取五档数据
                orderbook_data = await self._get_orderbook_data(stock_code)
                
                if orderbook_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"orderbook_{stock_code}", orderbook_data, "orderbook", "hot"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('orderbook_data', {
                            'stock_code': stock_code,
                            'data': orderbook_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"五档数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)

        self.logger.debug(f"五档数据流已退出: {stock_code}")

    async def _update_tick_stream(self, stock_code: str) -> None:
        """逐笔数据流更新"""
        stream_name = 'tick'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(1.0)
                    continue

                start_time = datetime.now()

                # 获取逐笔数据
                tick_data = await self._get_tick_data(stock_code)
                
                if tick_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"tick_{stock_code}", tick_data, "tick", "hot"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('tick_data', {
                            'stock_code': stock_code,
                            'data': tick_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"逐笔数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)

        self.logger.debug(f"逐笔数据流已退出: {stock_code}")

    async def _update_kline_stream(self, stock_code: str) -> None:
        """K线数据流更新"""
        stream_name = 'kline'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(5.0)
                    continue

                start_time = datetime.now()

                # 获取K线数据
                kline_data = await self._get_kline_data(stock_code)
                
                if kline_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"kline_{stock_code}", kline_data, "kline", "warm"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('kline_data', {
                            'stock_code': stock_code,
                            'data': kline_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"K线数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)

        self.logger.debug(f"K线数据流已退出: {stock_code}")

    async def _update_broker_queue_stream(self, stock_code: str) -> None:
        """经纪队列数据流更新"""
        stream_name = 'broker_queue'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(1.0)
                    continue

                start_time = datetime.now()

                # 获取经纪队列数据
                broker_data = await self._get_broker_queue_data(stock_code)
                
                if broker_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"broker_{stock_code}", broker_data, "broker", "hot"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('broker_queue_data', {
                            'stock_code': stock_code,
                            'data': broker_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"经纪队列数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)

        self.logger.debug(f"经纪队列数据流已退出: {stock_code}")

    async def _update_capital_flow_stream(self, stock_code: str) -> None:
        """资金流向数据流更新"""
        stream_name = 'capital_flow'
        config = self.stream_configs[stream_name]
        stats = self.stream_stats[stream_name]

        while self.is_running and self.stream_status[stream_name] != StreamStatus.STOPPED:
            try:
                if self.stream_status[stream_name] == StreamStatus.PAUSED:
                    await asyncio.sleep(2.0)
                    continue

                start_time = datetime.now()

                # 获取资金流向数据
                capital_data = await self._get_capital_flow_data(stock_code)
                
                if capital_data:
                    # 缓存数据
                    if self.data_cache_manager:
                        await self.data_cache_manager.store_data(
                            f"capital_{stock_code}", capital_data, "capital", "warm"
                        )

                    # 发布事件
                    if self.data_event_bus:
                        await self.data_event_bus.publish('capital_flow_data', {
                            'stock_code': stock_code,
                            'data': capital_data,
                            'timestamp': datetime.now()
                        })

                    # 更新统计
                    stats.last_update = datetime.now()
                    stats.update_count += 1
                    
                    latency = (datetime.now() - start_time).total_seconds()
                    stats.total_latency += latency
                    stats.average_latency = stats.total_latency / stats.update_count

                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                stats.error_count += 1
                self.logger.error(f"资金流向数据流更新失败: {e}")
                await asyncio.sleep(config.interval * 2)

        self.logger.debug(f"资金流向数据流已退出: {stock_code}")

    # 数据获取方法（占位符 - 实际实现时需要连接到analysis_data_manager）
    async def _get_quote_data(self, stock_code: str) -> Optional[Dict]:
        """获取报价数据"""
        if self.analysis_data_manager:
            try:
                return await self.analysis_data_manager._get_realtime_quote(stock_code)
            except Exception as e:
                self.logger.error(f"获取报价数据失败: {e}")
        return None

    async def _get_orderbook_data(self, stock_code: str) -> Optional[Dict]:
        """获取五档数据"""
        if self.analysis_data_manager:
            try:
                return await self.analysis_data_manager._get_orderbook_data(stock_code)
            except Exception as e:
                self.logger.error(f"获取五档数据失败: {e}")
        return None

    async def _get_tick_data(self, stock_code: str) -> Optional[Dict]:
        """获取逐笔数据"""
        if self.analysis_data_manager:
            try:
                return await self.analysis_data_manager._get_tick_data(stock_code)
            except Exception as e:
                self.logger.error(f"获取逐笔数据失败: {e}")
        return None

    async def _get_kline_data(self, stock_code: str) -> Optional[Dict]:
        """获取K线数据"""
        if self.analysis_data_manager:
            try:
                return await self.analysis_data_manager._get_kline_data(stock_code)
            except Exception as e:
                self.logger.error(f"获取K线数据失败: {e}")
        return None

    async def _get_broker_queue_data(self, stock_code: str) -> Optional[Dict]:
        """获取经纪队列数据"""
        if self.analysis_data_manager:
            try:
                return await self.analysis_data_manager._get_broker_queue_data(stock_code)
            except Exception as e:
                self.logger.error(f"获取经纪队列数据失败: {e}")
        return None

    async def _get_capital_flow_data(self, stock_code: str) -> Optional[Dict]:
        """获取资金流向数据（模拟数据）"""
        # 模拟资金流向数据
        return {
            'main_inflow': 2.3e8,
            'super_large_inflow': 1.8e8,
            'large_inflow': 0.5e8,
            'medium_outflow': -1.2e8,
            'small_outflow': -1.1e8,
            'north_bound_inflow': 0.85e8,
            'timestamp': datetime.now()
        }

    def get_stream_stats(self) -> Dict[str, Any]:
        """获取数据流统计信息"""
        stats = {}
        for stream_name, stream_stats in self.stream_stats.items():
            total_requests = stream_stats.update_count + stream_stats.error_count
            success_rate = (stream_stats.update_count / total_requests * 100) if total_requests > 0 else 0

            stats[stream_name] = {
                'status': self.stream_status.get(stream_name, StreamStatus.STOPPED).value,
                'start_time': stream_stats.start_time.isoformat() if stream_stats.start_time else None,
                'last_update': stream_stats.last_update.isoformat() if stream_stats.last_update else None,
                'update_count': stream_stats.update_count,
                'error_count': stream_stats.error_count,
                'success_rate': round(success_rate, 2),
                'average_latency': round(stream_stats.average_latency, 3),
                'active_subscriptions': len(self.active_subscriptions.get(stream_name, set()))
            }

        return {
            'streams': stats,
            'global_status': {
                'is_running': self.is_running,
                'current_stock': self.current_stock_code,
                'active_stream_count': len([s for s in self.stream_status.values() if s == StreamStatus.RUNNING])
            }
        }

    def update_stream_config(self, stream_name: str, **kwargs) -> bool:
        """更新数据流配置"""
        try:
            config = self.stream_configs.get(stream_name)
            if not config:
                return False

            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            self.logger.info(f"数据流配置已更新: {stream_name}")
            return True

        except Exception as e:
            self.logger.error(f"更新数据流配置失败 [{stream_name}]: {e}")
            return False