"""
数据缓存管理器 - 分层缓存优化

该模块提供热/温/冷三层缓存策略，优化实时数据的性能。
"""

import asyncio
import logging
import time
import sys
from typing import Dict, Any, Optional, Callable, Union, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import json
import pickle


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_time: datetime
    last_accessed: datetime
    access_count: int = 0
    data_type: str = ""
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """计算数据大小（字节）"""
        try:
            return sys.getsizeof(pickle.dumps(self.data))
        except:
            return sys.getsizeof(str(self.data))


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
        
    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存项"""
        if key in self.cache:
            entry = self.cache[key]
            # 更新访问信息
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            # 移到最前面（最近使用）
            self.cache.move_to_end(key)
            self.stats.hits += 1
            return entry
        
        self.stats.misses += 1
        return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """放入缓存项"""
        try:
            if key in self.cache:
                # 更新现有项
                old_entry = self.cache[key]
                self.stats.total_size_bytes -= old_entry.size_bytes
                
            self.cache[key] = entry
            self.cache.move_to_end(key)
            self.stats.total_size_bytes += entry.size_bytes
            
            # LRU淘汰
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                self.evict(oldest_key)
            
            self.stats.entry_count = len(self.cache)
            return True
            
        except Exception as e:
            logging.error(f"LRU缓存put操作失败: {e}")
            return False
    
    def evict(self, key: str) -> bool:
        """淘汰缓存项"""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.evictions += 1
            self.stats.entry_count = len(self.cache)
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.stats = CacheStats()


class DataCacheManager:
    """数据缓存管理器 - 优化实时数据性能"""

    def __init__(self, max_memory_mb: int = 100):
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # 三层缓存系统
        self.cache_layers = {
            'hot': LRUCache(max_size=500),      # 热数据 - 当前显示的股票
            'warm': LRUCache(max_size=1000),    # 温数据 - 最近访问的股票  
            'cold': LRUCache(max_size=2000)     # 冷数据 - 历史数据
        }
        
        self.cleanup_interval = 300  # 清理间隔（秒）
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        self.logger = logging.getLogger(__name__)

    async def start_cache_manager(self) -> None:
        """启动缓存管理器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("数据缓存管理器已启动")

    async def stop_cache_manager(self) -> None:
        """停止缓存管理器"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
                
        self.logger.info("数据缓存管理器已停止")

    async def get_data(self, key: str, data_type: str, 
                      fetch_func: Optional[Callable] = None) -> Any:
        """分层数据获取"""
        try:
            # 1. 从热缓存获取
            entry = self.cache_layers['hot'].get(key)
            if entry:
                self.logger.debug(f"热缓存命中: {key}")
                return entry.data

            # 2. 从温缓存获取并提升到热缓存
            entry = self.cache_layers['warm'].get(key)
            if entry:
                self.logger.debug(f"温缓存命中: {key}")
                await self._promote_to_hot(key, entry)
                return entry.data

            # 3. 从冷缓存获取并提升到温缓存
            entry = self.cache_layers['cold'].get(key)
            if entry:
                self.logger.debug(f"冷缓存命中: {key}")
                await self._promote_to_warm(key, entry)
                return entry.data

            # 4. 从数据源获取
            if fetch_func:
                self.logger.debug(f"缓存未命中，从数据源获取: {key}")
                data = await self._safe_fetch(fetch_func)
                if data is not None:
                    await self.store_data(key, data, data_type, 'hot')
                return data

            return None

        except Exception as e:
            self.logger.error(f"获取数据失败 [{key}]: {e}")
            return None

    async def store_data(self, key: str, data: Any, data_type: str, 
                        layer: str = 'hot') -> bool:
        """存储数据到指定缓存层"""
        try:
            entry = CacheEntry(
                key=key,
                data=data,
                created_time=datetime.now(),
                last_accessed=datetime.now(),
                data_type=data_type
            )

            cache = self.cache_layers.get(layer)
            if not cache:
                self.logger.error(f"无效的缓存层: {layer}")
                return False

            success = cache.put(key, entry)
            if success:
                await self._manage_memory_usage()
                self.logger.debug(f"数据存储成功 [{layer}]: {key}")
            
            return success

        except Exception as e:
            self.logger.error(f"存储数据失败 [{key}]: {e}")
            return False

    async def invalidate(self, key: str, layer: Optional[str] = None) -> bool:
        """使缓存失效"""
        try:
            if layer:
                cache = self.cache_layers.get(layer)
                if cache:
                    return cache.evict(key)
                return False
            else:
                # 从所有层移除
                success = False
                for cache in self.cache_layers.values():
                    if cache.evict(key):
                        success = True
                return success

        except Exception as e:
            self.logger.error(f"使缓存失效失败 [{key}]: {e}")
            return False

    async def clear_layer(self, layer: str) -> bool:
        """清空指定缓存层"""
        try:
            cache = self.cache_layers.get(layer)
            if cache:
                cache.clear()
                self.logger.info(f"缓存层已清空: {layer}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"清空缓存层失败 [{layer}]: {e}")
            return False

    async def clear_all_cache(self) -> None:
        """清理所有缓存"""
        try:
            for layer_name, cache in self.cache_layers.items():
                cache.clear()
                self.logger.debug(f"缓存层已清空: {layer_name}")
                
            self.logger.info("所有缓存已清空")

        except Exception as e:
            self.logger.error(f"清空所有缓存失败: {e}")

    async def _promote_to_hot(self, key: str, entry: CacheEntry) -> None:
        """提升到热缓存"""
        # 从温缓存移除
        self.cache_layers['warm'].evict(key)
        # 添加到热缓存
        self.cache_layers['hot'].put(key, entry)

    async def _promote_to_warm(self, key: str, entry: CacheEntry) -> None:
        """提升到温缓存"""
        # 从冷缓存移除
        self.cache_layers['cold'].evict(key)
        # 添加到温缓存
        self.cache_layers['warm'].put(key, entry)

    async def _safe_fetch(self, fetch_func: Callable) -> Any:
        """安全的数据获取"""
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                return await fetch_func()
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, fetch_func)
        except Exception as e:
            self.logger.error(f"数据获取异常: {e}")
            return None

    async def _manage_memory_usage(self) -> None:
        """内存使用管理"""
        try:
            current_usage = self._calculate_total_memory_usage()
            
            if current_usage > self.max_memory_bytes:
                self.logger.warning(f"内存使用超限: {current_usage / 1024 / 1024:.1f}MB")
                
                # 1. 清理冷数据
                await self._evict_cold_data()
                
                # 2. 如果还是超出，清理部分温数据
                current_usage = self._calculate_total_memory_usage()
                if current_usage > self.max_memory_bytes * 0.9:
                    await self._evict_warm_data()

        except Exception as e:
            self.logger.error(f"内存管理失败: {e}")

    async def _evict_cold_data(self) -> None:
        """淘汰冷数据"""
        cold_cache = self.cache_layers['cold']
        # 清理最老的25%数据
        evict_count = max(1, len(cold_cache.cache) // 4)
        
        keys_to_evict = list(cold_cache.cache.keys())[:evict_count]
        for key in keys_to_evict:
            cold_cache.evict(key)
            
        self.logger.debug(f"淘汰冷数据: {evict_count} 项")

    async def _evict_warm_data(self) -> None:
        """淘汰温数据"""
        warm_cache = self.cache_layers['warm']
        # 清理最老的10%数据
        evict_count = max(1, len(warm_cache.cache) // 10)
        
        keys_to_evict = list(warm_cache.cache.keys())[:evict_count]
        for key in keys_to_evict:
            warm_cache.evict(key)
            
        self.logger.debug(f"淘汰温数据: {evict_count} 项")

    def _calculate_total_memory_usage(self) -> int:
        """计算总内存使用量"""
        total_bytes = 0
        for cache in self.cache_layers.values():
            total_bytes += cache.stats.total_size_bytes
        return total_bytes

    async def _cleanup_loop(self) -> None:
        """缓存清理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._periodic_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"缓存清理循环异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟

    async def _periodic_cleanup(self) -> None:
        """定期清理"""
        try:
            # 清理过期数据（超过1小时未访问的冷数据）
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            cold_cache = self.cache_layers['cold']
            expired_keys = []
            
            for key, entry in cold_cache.cache.items():
                if entry.last_accessed < cutoff_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                cold_cache.evict(key)
            
            if expired_keys:
                self.logger.debug(f"清理过期数据: {len(expired_keys)} 项")
            
            # 内存管理
            await self._manage_memory_usage()
            
        except Exception as e:
            self.logger.error(f"定期清理失败: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {}
        total_stats = CacheStats()
        
        for layer_name, cache in self.cache_layers.items():
            layer_stats = cache.stats
            stats[layer_name] = {
                'hits': layer_stats.hits,
                'misses': layer_stats.misses,
                'evictions': layer_stats.evictions,
                'entry_count': layer_stats.entry_count,
                'size_mb': layer_stats.total_size_bytes / 1024 / 1024,
                'hit_rate': layer_stats.hit_rate
            }
            
            # 累加总统计
            total_stats.hits += layer_stats.hits
            total_stats.misses += layer_stats.misses
            total_stats.evictions += layer_stats.evictions
            total_stats.entry_count += layer_stats.entry_count
            total_stats.total_size_bytes += layer_stats.total_size_bytes
        
        stats['total'] = {
            'hits': total_stats.hits,
            'misses': total_stats.misses,
            'evictions': total_stats.evictions,
            'entry_count': total_stats.entry_count,
            'size_mb': total_stats.total_size_bytes / 1024 / 1024,
            'hit_rate': total_stats.hit_rate,
            'memory_usage_percent': (total_stats.total_size_bytes / self.max_memory_bytes) * 100
        }
        
        return stats

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_cache_manager()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop_cache_manager()