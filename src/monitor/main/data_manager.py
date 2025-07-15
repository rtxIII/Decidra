"""
DataManager - 股票数据和API管理模块

负责股票数据获取、API调用管理、数据刷新和格式转换
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Any, List

from base.monitor import StockData, MarketStatus, ConnectionStatus
from modules.futu_market import FutuMarket
from monitor.data_flow import DataFlowManager
from monitor.indicators import IndicatorsManager
from monitor.performance import PerformanceMonitor
from base.futu_class import MarketSnapshot
from utils.logger import get_logger

SNAPSHOT_REFRESH_INTERVAL = 300


class DataManager:
    """
    数据管理器
    负责股票数据获取、API调用管理和数据处理
    """
    
    def __init__(self, app_core, futu_market: FutuMarket):
        """初始化数据管理器"""
        self.app_core = app_core
        self.logger = get_logger(__name__)
        
        # 富途市场实例
        self.futu_market = futu_market
        
        # 初始化其他管理器
        self.data_flow_manager = DataFlowManager(futu_market=self.futu_market)
        self.indicators_manager = IndicatorsManager()
        self.performance_monitor = PerformanceMonitor()
        
        # 定时器
        self.refresh_timer: Optional[asyncio.Task] = None
        
        self.logger.info("DataManager 初始化完成")
    
    async def initialize_data_managers(self) -> None:
        """初始化数据管理器"""
        try:
            # 主动建立富途连接
            try:
                self.logger.info("正在连接富途API...")
                loop = asyncio.get_event_loop()
                
                # 在线程池中执行连接操作
                connect_success = await loop.run_in_executor(
                    None, 
                    self.futu_market.client.connect
                )
                
                if connect_success:
                    self.app_core.connection_status = ConnectionStatus.CONNECTED
                    self.logger.info("富途API连接成功")
                    
                    # 连接成功后立即加载股票基本信息
                    await self.load_stock_basicinfo()
                else:
                    self.app_core.connection_status = ConnectionStatus.DISCONNECTED
                    self.logger.warning("富途API连接失败")
                    
            except Exception as e:
                self.app_core.connection_status = ConnectionStatus.ERROR
                self.logger.error(f"富途API连接失败: {e}")
            
            # 初始化数据流管理器
            if hasattr(self.data_flow_manager, 'initialize'):
                await self.data_flow_manager.initialize()
            
        except Exception as e:
            self.logger.error(f"数据管理器初始化失败: {e}")
            self.app_core.connection_status = ConnectionStatus.ERROR
    
    async def attempt_reconnect(self) -> bool:
        """尝试重新连接富途API"""
        if self.app_core._reconnect_attempts >= self.app_core._max_reconnect_attempts:
            self.logger.error(f"超过最大重连次数 {self.app_core._max_reconnect_attempts}")
            return False
            
        self.app_core._reconnect_attempts += 1
        self.logger.info(f"尝试重连富途API (第 {self.app_core._reconnect_attempts} 次)")
        
        try:
            # 关闭旧连接
            if hasattr(self.futu_market, 'close'):
                self.futu_market.close()
            
            # 等待一段时间后重新创建连接
            await asyncio.sleep(2.0)
            
            # 重新创建富途市场实例
            self.futu_market = FutuMarket()
            self.futu_market._is_shared_instance = True
            
            # 检查新连接状态
            loop = asyncio.get_event_loop()
            connection_state = await loop.run_in_executor(
                None, 
                self.futu_market.get_connection_state
            )
            
            if connection_state[0]:
                self.app_core.connection_status = ConnectionStatus.CONNECTED
                self.app_core._reconnect_attempts = 0  # 重置重连计数
                self.logger.info("富途API重连成功")
                return True
            else:
                self.app_core.connection_status = ConnectionStatus.DISCONNECTED
                self.logger.warning(f"富途API重连失败: {connection_state[1]}")
                return False
                
        except Exception as e:
            self.logger.error(f"重连过程中出错: {e}")
            self.app_core.connection_status = ConnectionStatus.ERROR
            return False
    
    async def detect_market_status(self) -> MarketStatus:
        """检测市场状态"""
        try:
            # 简化的市场状态检测
            current_time = datetime.now()
            hour = current_time.hour
            
            # 简单判断：9:30-16:00为开盘时间
            if 9 <= hour < 16:
                return MarketStatus.OPEN
            else:
                return MarketStatus.CLOSE
                
        except Exception as e:
            self.logger.error(f"检测市场状态失败: {e}")
            return MarketStatus.CLOSE
    
    async def start_data_refresh(self) -> None:
        """启动数据刷新"""
        try:
            # 判断市场状态并设置刷新模式
            market_status = await self.detect_market_status()
            
            if market_status == MarketStatus.OPEN:
                self.app_core.refresh_mode = "实时模式"
                # 启动实时数据订阅
                await self.start_realtime_subscription()
            else:
                self.app_core.refresh_mode = "快照模式"
                # 启动快照数据刷新
                await self.start_snapshot_refresh()
            
            self.logger.info(f"数据刷新启动: {self.app_core.refresh_mode}")
            
        except Exception as e:
            self.logger.error(f"启动数据刷新失败: {e}")
    
    async def start_realtime_subscription(self) -> None:
        """启动实时数据订阅"""
        try:
            if self.app_core.connection_status == ConnectionStatus.CONNECTED:
                # 订阅实时数据
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    None,
                    self.futu_market.subscribe,
                    self.app_core.monitored_stocks,
                    ["QUOTE"],  # 订阅类型：实时报价
                    True,       # is_first_push
                    True        # is_unlimit_push
                )
                if success:
                    self.logger.info("实时数据订阅启动")
                else:
                    raise Exception("订阅失败")
        except Exception as e:
            self.logger.error(f"实时数据订阅失败: {e}")
            # 降级到快照模式
            await self.start_snapshot_refresh()
    
    async def start_snapshot_refresh(self) -> None:
        """启动快照数据刷新"""
        # 检查是否已有刷新任务在运行
        if self.refresh_timer and not self.refresh_timer.done():
            self.logger.info("快照数据刷新已在运行，跳过重复启动")
            return
            
        # 取消现有任务（如果存在）
        if self.refresh_timer:
            self.refresh_timer.cancel()
            try:
                await self.refresh_timer
            except asyncio.CancelledError:
                pass
        
        # 创建定时刷新任务
        self.refresh_timer = asyncio.create_task(self.snapshot_refresh_loop())
        self.logger.info("快照数据刷新启动")
    
    async def snapshot_refresh_loop(self) -> None:
        """快照数据刷新循环"""
        while True:
            try:
                await self.refresh_stock_data()
                await asyncio.sleep(SNAPSHOT_REFRESH_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"快照数据刷新错误: {e}")
                await asyncio.sleep(SNAPSHOT_REFRESH_INTERVAL)
    
    async def refresh_stock_data(self) -> None:
        """刷新股票数据"""
        try:
            # 直接调用API获取实时行情数据
            loop = asyncio.get_event_loop()
            market_snapshots = await loop.run_in_executor(
                None,
                self.futu_market.get_market_snapshot,
                self.app_core.monitored_stocks
            )
            self.logger.info("%s" % market_snapshots)
            
            # 转换数据格式并更新
            if market_snapshots:
                # 更新连接状态为已连接
                self.app_core.connection_status = ConnectionStatus.CONNECTED
                
                for snapshot in market_snapshots:
                    # 修复：snapshot现在是MarketSnapshot对象，不是字典
                    if hasattr(snapshot, 'code'):
                        stock_code = snapshot.code
                        stock_info = self.convert_snapshot_to_stock_data(snapshot)
                        # 只有转换成功的数据才存储
                        if stock_info is not None:
                            self.app_core.stock_data[stock_code] = stock_info
                
                self.logger.info("股票数据刷新成功")
            else:
                # API调用返回空数据，可能是连接问题
                self.app_core.connection_status = ConnectionStatus.DISCONNECTED
                self.logger.warning("API调用返回空数据，可能存在连接问题")
            
        except Exception as e:
            # API调用失败，更新连接状态
            self.app_core.connection_status = ConnectionStatus.ERROR
            self.logger.error(f"刷新股票数据失败: {e}")
    
    def convert_snapshot_to_stock_data(self, snapshot: MarketSnapshot) -> StockData:
        """将富途快照数据转换为标准StockData格式"""
        try:
            # 数据清理和验证
            current_price = snapshot.last_price
            prev_close = snapshot.prev_close_price
            
            if current_price <= 0:
                self.logger.warning(f"股票 {snapshot.code} 价格数据异常: {current_price}, 跳过此次更新")
                return None
                
            if prev_close <= 0:
                prev_close = current_price  # 如果昨收价异常，使用当前价格
                
            # 计算涨跌幅，并限制在合理范围内
            change_rate = 0.0
            if prev_close > 0:
                change_rate = ((current_price - prev_close) / prev_close) * 100
            
            # 计算涨跌额
            change_amount = current_price - prev_close
            
            # 从snapshot获取股票名称，如果没有则使用股票代码
            stock_name = getattr(snapshot, 'name', snapshot.code) or snapshot.code
            
            return StockData(
                code=snapshot.code,
                name=stock_name,
                current_price=current_price,
                open_price=snapshot.open_price,
                prev_close=prev_close,
                change_rate=change_rate,
                change_amount=change_amount,
                volume=max(0, snapshot.volume),  # 确保成交量非负
                turnover=snapshot.turnover,
                high_price=snapshot.high_price,
                low_price=snapshot.low_price,
                update_time=datetime.now(),
                market_status=MarketStatus.OPEN
            )
            
        except Exception as e:
            self.logger.error(f"转换股票数据时发生错误: {e}")
            return None
    
    async def on_realtime_data_received(self, data: Dict[str, Any]) -> None:
        """处理实时数据回调"""
        try:
            # 处理实时推送数据
            stock_code = data.get('stock_code')
            if stock_code in self.app_core.monitored_stocks:
                # 更新股票数据
                stock_info = StockData(
                    code=stock_code,
                    name=data.get('name', ''),
                    current_price=data.get('price', 0.0),
                    open_price=data.get('open_price', 0.0),
                    prev_close=data.get('prev_close', 0.0),
                    change_rate=data.get('change_rate', 0.0),
                    change_amount=data.get('change_amount', 0.0),
                    volume=data.get('volume', 0),
                    turnover=data.get('turnover', 0.0),
                    high_price=data.get('high_price', 0.0),
                    low_price=data.get('low_price', 0.0),
                    update_time=datetime.now(),
                    market_status=MarketStatus.OPEN
                )
                
                self.app_core.stock_data[stock_code] = stock_info
                
        except Exception as e:
            self.logger.error(f"处理实时数据失败: {e}")
    
    async def cleanup(self) -> None:
        """清理数据管理器资源"""
        try:
            # 停止刷新定时器
            if self.refresh_timer:
                self.refresh_timer.cancel()
                self.refresh_timer = None
            
            # 清理数据流管理器
            if hasattr(self.data_flow_manager, 'cleanup'):
                await self.data_flow_manager.cleanup()
                
            self.logger.info("DataManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"DataManager 清理失败: {e}")
    
    def cleanup_futu_market(self) -> None:
        """清理富途市场连接"""
        try:
            if hasattr(self.futu_market, 'close'):
                self.futu_market.close()
                self.logger.info("富途市场连接已清理")
        except Exception as e:
            self.logger.warning(f"清理富途市场连接时出错: {e}")
    
    async def load_stock_basicinfo(self) -> None:
        """加载股票基本信息并缓存"""
        try:
            if self.app_core.connection_status != ConnectionStatus.CONNECTED:
                self.logger.warning("富途API未连接，无法加载股票基本信息")
                return
            
            # 为监控的股票加载基本信息
            if not self.app_core.monitored_stocks:
                self.logger.info("没有监控的股票，跳过基本信息加载")
                return
            
            self.logger.info(f"开始加载 {len(self.app_core.monitored_stocks)} 只股票的基本信息...")
            
            # 在线程池中执行同步的富途API调用
            loop = asyncio.get_event_loop()
            
            # 根据股票代码确定市场
            hk_stocks = [code for code in self.app_core.monitored_stocks if code.startswith('HK.')]
            us_stocks = [code for code in self.app_core.monitored_stocks if code.startswith('US.')]
            sh_stocks = [code for code in self.app_core.monitored_stocks if code.startswith('SH.')]
            sz_stocks = [code for code in self.app_core.monitored_stocks if code.startswith('SZ.')]
            
            # 分别获取不同市场的股票基本信息
            market_groups = [
                ("HK", hk_stocks),
                ("US", us_stocks),
                ("SH", sh_stocks),
                ("SZ", sz_stocks)
            ]
            
            total_loaded = 0
            for market, stocks in market_groups:
                if not stocks:
                    continue
                    
                try:
                    basicinfo_list = await loop.run_in_executor(
                        None,
                        self.futu_market.get_stock_basicinfo,
                        market,
                        "STOCK"
                    )
                    
                    if basicinfo_list:
                        for basicinfo in basicinfo_list:
                            if hasattr(basicinfo, 'code'):
                                stock_code = basicinfo.code
                                self.app_core.stock_basicinfo_cache[stock_code] = {
                                    'code': basicinfo.code,
                                    'name': getattr(basicinfo, 'name', ''),
                                    'lot_size': getattr(basicinfo, 'lot_size', 0),
                                    'stock_type': getattr(basicinfo, 'stock_type', ''),
                                    'main_contract': getattr(basicinfo, 'main_contract', False),
                                    'stock_child_type': getattr(basicinfo, 'stock_child_type', ''),
                                    'listing_date': getattr(basicinfo, 'listing_date', None),
                                    'delisting_date': getattr(basicinfo, 'delisting_date', None),
                                    'last_update': datetime.now().isoformat()
                                }
                                total_loaded += 1
                            elif isinstance(basicinfo, dict):
                                stock_code = basicinfo.get('code', '')
                                if stock_code:
                                    self.app_core.stock_basicinfo_cache[stock_code] = {
                                        'code': stock_code,
                                        'name': basicinfo.get('name', ''),
                                        'lot_size': basicinfo.get('lot_size', 0),
                                        'stock_type': basicinfo.get('stock_type', ''),
                                        'main_contract': basicinfo.get('main_contract', False),
                                        'stock_child_type': basicinfo.get('stock_child_type', ''),
                                        'listing_date': basicinfo.get('listing_date', None),
                                        'delisting_date': basicinfo.get('delisting_date', None),
                                        'last_update': datetime.now().isoformat()
                                    }
                                    total_loaded += 1
                    
                    self.logger.info(f"加载 {market} 市场 {len(stocks)} 只股票基本信息完成")
                    
                except Exception as e:
                    self.logger.error(f"加载 {market} 市场股票基本信息失败: {e}")
                    continue
            
            self.logger.info(f"股票基本信息加载完成，共缓存 {total_loaded} 只股票")
            
        except Exception as e:
            self.logger.error(f"加载股票基本信息失败: {e}")
    
    async def refresh_stock_basicinfo(self) -> None:
        """刷新股票基本信息缓存"""
        try:
            self.logger.info("开始刷新股票基本信息缓存...")
            
            # 清空现有缓存
            self.app_core.stock_basicinfo_cache.clear()
            
            # 重新加载基本信息
            await self.load_stock_basicinfo()
            
            self.logger.info("股票基本信息缓存刷新完成")
            
        except Exception as e:
            self.logger.error(f"刷新股票基本信息缓存失败: {e}")
    
    def get_stock_basicinfo_from_cache(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从缓存中获取股票基本信息"""
        try:
            return self.app_core.stock_basicinfo_cache.get(stock_code)
        except Exception as e:
            self.logger.error(f"从缓存获取股票基本信息失败: {e}")
            return None
    
    def search_stock_by_text(self, search_text: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        根据用户输入的文本搜索股票代码
        
        Args:
            search_text: 用户输入的搜索文本
            max_results: 最大返回结果数量
            
        Returns:
            包含匹配股票信息的列表，按相似度排序
        """
        try:
            if not search_text or not search_text.strip():
                return []
            
            search_text = search_text.strip().upper()
            matches = []
            
            # 遍历缓存中的股票信息
            for stock_code, basic_info in self.app_core.stock_basicinfo_cache.items():
                if not basic_info:
                    continue
                    
                stock_name = basic_info.get('name', '').upper()
                stock_code_upper = stock_code.upper()
                
                # 计算相似度分数
                similarity_score = self._calculate_similarity(search_text, stock_code_upper, stock_name)
                
                if similarity_score > 0:
                    matches.append({
                        'stock_code': stock_code,
                        'stock_name': basic_info.get('name', ''),
                        'similarity_score': similarity_score,
                        'basic_info': basic_info
                    })
            
            # 按相似度分数排序（降序）
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # 返回最多max_results个结果
            return matches[:max_results]
            
        except Exception as e:
            self.logger.error(f"搜索股票失败: {e}")
            return []
    
    def _calculate_similarity(self, search_text: str, stock_code: str, stock_name: str) -> float:
        """
        计算搜索文本与股票代码/名称的相似度
        
        Args:
            search_text: 搜索文本
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            相似度分数（0-100）
        """
        try:
            # 精确匹配股票代码（最高权重）
            if search_text == stock_code:
                return 100.0
            
            # 股票代码包含搜索文本
            if search_text in stock_code:
                return 90.0
            
            # 股票代码开头匹配
            if stock_code.startswith(search_text):
                return 85.0
            
            # 股票名称精确匹配
            if search_text == stock_name:
                return 95.0
            
            # 股票名称包含搜索文本
            if search_text in stock_name:
                return 80.0
            
            # 股票名称开头匹配
            if stock_name.startswith(search_text):
                return 75.0
            
            # 计算编辑距离相似度
            code_similarity = self._levenshtein_similarity(search_text, stock_code)
            name_similarity = self._levenshtein_similarity(search_text, stock_name)
            
            # 股票代码相似度权重更高
            max_similarity = max(code_similarity * 0.7, name_similarity * 0.6)
            
            # 只返回相似度超过阈值的结果
            return max_similarity if max_similarity > 30 else 0.0
            
        except Exception as e:
            self.logger.error(f"计算相似度失败: {e}")
            return 0.0
    
    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """
        计算两个字符串的编辑距离相似度
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            相似度百分比（0-100）
        """
        try:
            if not s1 or not s2:
                return 0.0
            
            # 计算编辑距离
            distance = self._levenshtein_distance(s1, s2)
            max_len = max(len(s1), len(s2))
            
            if max_len == 0:
                return 100.0
            
            # 转换为相似度百分比
            similarity = ((max_len - distance) / max_len) * 100
            return max(0.0, similarity)
            
        except Exception as e:
            self.logger.error(f"计算编辑距离相似度失败: {e}")
            return 0.0
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        计算两个字符串的编辑距离
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]