"""
Supabase数据操作模块

基于supabase-py实现的云端数据库操作类
提供完整的Supabase数据库接口，用于云端数据存储和操作
支持实时数据同步、用户认证、文件存储等功能
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

try:
    from supabase import create_client, Client
    from postgrest import APIError
except ImportError:
    raise ImportError("请先安装supabase包: pip install supabase")

from utils.global_vars import get_logger


class SupabaseManager:
    """
    Supabase数据管理器
    
    提供完整的Supabase云端数据库操作功能
    支持实时数据同步、用户认证、文件存储等特性
    """
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        初始化Supabase数据管理器
        
        Args:
            url: Supabase项目URL，如果为None则从环境变量获取
            key: Supabase API密钥，如果为None则从环境变量获取
        """
        self.logger = get_logger(__name__)
        
        # 获取Supabase配置
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL和KEY必须提供，可通过参数或环境变量设置")
        
        # 初始化Supabase客户端
        try:
            self.client: Client = create_client(self.url, self.key)
            self.logger.info("Supabase客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Supabase客户端初始化失败: {e}")
            raise
    
    # ================== 基础CRUD操作 ==================
    
    def insert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        插入数据到指定表
        
        Args:
            table: 表名
            data: 要插入的数据，可以是单个字典或字典列表
            
        Returns:
            Dict: 插入结果
        """
        try:
            # 添加时间戳
            timestamp = datetime.now().isoformat()
            
            if isinstance(data, dict):
                data['created_at'] = timestamp
                data['updated_at'] = timestamp
            elif isinstance(data, list):
                for item in data:
                    item['created_at'] = timestamp
                    item['updated_at'] = timestamp
            
            result = self.client.table(table).insert(data).execute()
            
            if result.data:
                count = len(result.data) if isinstance(result.data, list) else 1
                self.logger.debug(f"成功插入 {count} 条记录到表 {table}")
            
            return result.data
            
        except APIError as e:
            self.logger.error(f"插入数据到表 {table} 失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"插入数据时发生未知错误: {e}")
            raise
    
    def select(self, table: str, columns: str = "*", 
               filters: Optional[Dict[str, Any]] = None,
               order_by: Optional[str] = None,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        从指定表查询数据
        
        Args:
            table: 表名
            columns: 要查询的列，默认为所有列
            filters: 查询条件字典
            order_by: 排序字段
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 查询结果列表
        """
        try:
            query = self.client.table(table).select(columns)
            
            # 应用过滤条件
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # 支持复杂查询条件，如 {'age': {'gte': 18}}
                        for op, val in value.items():
                            query = getattr(query, op)(key, val)
                    else:
                        # 简单等值查询
                        query = query.eq(key, value)
            
            # 应用排序
            if order_by:
                if order_by.startswith('-'):
                    # 降序排序
                    query = query.order(order_by[1:], desc=True)
                else:
                    # 升序排序
                    query = query.order(order_by)
            
            # 应用限制
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            
            self.logger.debug(f"从表 {table} 查询到 {len(result.data)} 条记录")
            return result.data
            
        except APIError as e:
            self.logger.error(f"从表 {table} 查询数据失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"查询数据时发生未知错误: {e}")
            raise
    
    def update(self, table: str, data: Dict[str, Any], 
               filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        更新指定表的数据
        
        Args:
            table: 表名
            data: 要更新的数据
            filters: 更新条件
            
        Returns:
            List[Dict]: 更新后的记录
        """
        try:
            # 添加更新时间戳
            data['updated_at'] = datetime.now().isoformat()
            
            query = self.client.table(table).update(data)
            
            # 应用过滤条件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            
            count = len(result.data) if result.data else 0
            self.logger.debug(f"成功更新表 {table} 中的 {count} 条记录")
            
            return result.data
            
        except APIError as e:
            self.logger.error(f"更新表 {table} 数据失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"更新数据时发生未知错误: {e}")
            raise
    
    def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        删除指定表的数据
        
        Args:
            table: 表名
            filters: 删除条件
            
        Returns:
            List[Dict]: 被删除的记录
        """
        try:
            query = self.client.table(table).delete()
            
            # 应用过滤条件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            
            count = len(result.data) if result.data else 0
            self.logger.debug(f"成功删除表 {table} 中的 {count} 条记录")
            
            return result.data
            
        except APIError as e:
            self.logger.error(f"删除表 {table} 数据失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"删除数据时发生未知错误: {e}")
            raise
    
    def upsert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
               on_conflict: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        插入或更新数据（如果存在则更新，不存在则插入）
        
        Args:
            table: 表名
            data: 要插入或更新的数据
            on_conflict: 冲突时的处理字段
            
        Returns:
            List[Dict]: 操作结果
        """
        try:
            # 添加时间戳
            timestamp = datetime.now().isoformat()
            
            if isinstance(data, dict):
                data['updated_at'] = timestamp
                if 'created_at' not in data:
                    data['created_at'] = timestamp
            elif isinstance(data, list):
                for item in data:
                    item['updated_at'] = timestamp
                    if 'created_at' not in item:
                        item['created_at'] = timestamp
            
            query = self.client.table(table).upsert(data)
            
            if on_conflict:
                query = query.on_conflict(on_conflict)
            
            result = query.execute()
            
            count = len(result.data) if result.data else 0
            self.logger.debug(f"成功upsert表 {table} 中的 {count} 条记录")
            
            return result.data
            
        except APIError as e:
            self.logger.error(f"Upsert表 {table} 数据失败: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Upsert数据时发生未知错误: {e}")
            raise    
 
   # ================== 业务特定方法 ==================
    
    def save_stock_data(self, stock_code: str, data: Dict[str, Any], 
                       data_type: str = "realtime") -> Dict[str, Any]:
        """
        保存股票数据
        
        Args:
            stock_code: 股票代码
            data: 股票数据
            data_type: 数据类型（realtime, kline, snapshot等）
            
        Returns:
            Dict: 保存结果
        """
        document = {
            'stock_code': stock_code,
            'data_type': data_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.insert('stock_data', document)
    
    def get_stock_data(self, stock_code: str, data_type: Optional[str] = None,
                      start_time: Optional[str] = None, end_time: Optional[str] = None,
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            data_type: 数据类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 股票数据列表
        """
        filters = {'stock_code': stock_code}
        
        if data_type:
            filters['data_type'] = data_type
        
        # 时间范围过滤需要在查询中处理
        query_filters = filters.copy()
        if start_time:
            query_filters['timestamp'] = {'gte': start_time}
        if end_time:
            if 'timestamp' in query_filters:
                query_filters['timestamp']['lte'] = end_time
            else:
                query_filters['timestamp'] = {'lte': end_time}
        
        return self.select('stock_data', filters=query_filters, 
                          order_by='-timestamp', limit=limit)
    
    def save_trading_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存交易记录
        
        Args:
            record: 交易记录数据
            
        Returns:
            Dict: 保存结果
        """
        document = {
            'stock_code': record.get('stock_code'),
            'action': record.get('action'),  # buy, sell
            'quantity': record.get('quantity'),
            'price': record.get('price'),
            'amount': record.get('amount'),
            'order_id': record.get('order_id'),
            'trade_time': record.get('trade_time', datetime.now().isoformat()),
            'status': record.get('status', 'completed'),
            'market': record.get('market', 'HK'),
            'record_data': record
        }
        
        return self.insert('trading_records', document)
    
    def get_trading_records(self, stock_code: Optional[str] = None,
                           action: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取交易记录
        
        Args:
            stock_code: 股票代码过滤
            action: 交易动作过滤（buy/sell）
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 交易记录列表
        """
        filters = {}
        
        if stock_code:
            filters['stock_code'] = stock_code
        if action:
            filters['action'] = action
        
        # 时间范围过滤
        if start_date:
            filters['trade_time'] = {'gte': start_date}
        if end_date:
            if 'trade_time' in filters:
                filters['trade_time']['lte'] = end_date
            else:
                filters['trade_time'] = {'lte': end_date}
        
        return self.select('trading_records', filters=filters,
                          order_by='-trade_time', limit=limit)
    
    def save_user_config(self, user_id: str, config_key: str, 
                        config_value: Any) -> Dict[str, Any]:
        """
        保存用户配置
        
        Args:
            user_id: 用户ID
            config_key: 配置键
            config_value: 配置值
            
        Returns:
            Dict: 保存结果
        """
        document = {
            'user_id': user_id,
            'config_key': config_key,
            'config_value': config_value
        }
        
        # 使用upsert确保配置唯一性
        return self.upsert('user_configs', document, 
                          on_conflict='user_id,config_key')
    
    def get_user_config(self, user_id: str, config_key: str, 
                       default_value: Any = None) -> Any:
        """
        获取用户配置
        
        Args:
            user_id: 用户ID
            config_key: 配置键
            default_value: 默认值
            
        Returns:
            Any: 配置值
        """
        results = self.select('user_configs', 
                             filters={'user_id': user_id, 'config_key': config_key})
        
        if results:
            return results[0].get('config_value', default_value)
        return default_value
    
    def save_market_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存市场分析数据
        
        Args:
            analysis_data: 分析数据
            
        Returns:
            Dict: 保存结果
        """
        document = {
            'analysis_type': analysis_data.get('analysis_type'),
            'market': analysis_data.get('market', 'HK'),
            'analysis_result': analysis_data.get('result'),
            'parameters': analysis_data.get('parameters'),
            'confidence_score': analysis_data.get('confidence_score'),
            'analysis_data': analysis_data
        }
        
        return self.insert('market_analysis', document)
    
    def get_market_analysis(self, analysis_type: Optional[str] = None,
                           market: Optional[str] = None,
                           start_date: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取市场分析数据
        
        Args:
            analysis_type: 分析类型过滤
            market: 市场过滤
            start_date: 开始日期
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 分析数据列表
        """
        filters = {}
        
        if analysis_type:
            filters['analysis_type'] = analysis_type
        if market:
            filters['market'] = market
        if start_date:
            filters['created_at'] = {'gte': start_date}
        
        return self.select('market_analysis', filters=filters,
                          order_by='-created_at', limit=limit)
    
    def save_watchlist(self, user_id: str, stock_code: str, 
                      notes: Optional[str] = None) -> Dict[str, Any]:
        """
        保存自选股
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            notes: 备注信息
            
        Returns:
            Dict: 保存结果
        """
        document = {
            'user_id': user_id,
            'stock_code': stock_code,
            'notes': notes,
            'added_at': datetime.now().isoformat()
        }
        
        return self.upsert('watchlist', document, 
                          on_conflict='user_id,stock_code')
    
    def get_watchlist(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户自选股列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 自选股列表
        """
        return self.select('watchlist', filters={'user_id': user_id},
                          order_by='-added_at')
    
    def remove_from_watchlist(self, user_id: str, stock_code: str) -> List[Dict[str, Any]]:
        """
        从自选股中移除股票
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            
        Returns:
            List[Dict]: 删除结果
        """
        return self.delete('watchlist', 
                          {'user_id': user_id, 'stock_code': stock_code})
    
    # ================== 实时数据订阅 ==================
    
    def subscribe_realtime(self, table: str, callback_func, 
                          filters: Optional[Dict[str, Any]] = None):
        """
        订阅实时数据变化
        
        Args:
            table: 表名
            callback_func: 回调函数
            filters: 过滤条件
        """
        try:
            channel = self.client.channel(f'realtime-{table}')
            
            # 构建订阅配置
            event_config = {
                'event': '*',
                'table': table,
                'callback': callback_func
            }
            
            if filters:
                event_config['filter'] = filters
            
            channel.on('postgres_changes', **event_config)
            channel.subscribe()
            
            self.logger.info(f"成功订阅表 {table} 的实时数据变化")
            return channel
            
        except Exception as e:
            self.logger.error(f"订阅实时数据失败: {e}")
            raise
    
    def unsubscribe_realtime(self, channel):
        """
        取消实时数据订阅
        
        Args:
            channel: 订阅频道对象
        """
        try:
            if channel:
                channel.unsubscribe()
                self.logger.info("成功取消实时数据订阅")
        except Exception as e:
            self.logger.error(f"取消实时数据订阅失败: {e}")
    
    # ================== 文件存储操作 ==================
    
    def upload_file(self, bucket: str, file_path: str, file_data: bytes,
                   content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        上传文件到Supabase存储
        
        Args:
            bucket: 存储桶名称
            file_path: 文件路径
            file_data: 文件数据
            content_type: 文件类型
            
        Returns:
            Dict: 上传结果
        """
        try:
            result = self.client.storage.from_(bucket).upload(
                file_path, file_data, 
                file_options={'content-type': content_type} if content_type else None
            )
            
            self.logger.info(f"成功上传文件到 {bucket}/{file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"上传文件失败: {e}")
            raise
    
    def download_file(self, bucket: str, file_path: str) -> bytes:
        """
        从Supabase存储下载文件
        
        Args:
            bucket: 存储桶名称
            file_path: 文件路径
            
        Returns:
            bytes: 文件数据
        """
        try:
            result = self.client.storage.from_(bucket).download(file_path)
            self.logger.info(f"成功下载文件 {bucket}/{file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"下载文件失败: {e}")
            raise
    
    def delete_file(self, bucket: str, file_path: str) -> Dict[str, Any]:
        """
        删除Supabase存储中的文件
        
        Args:
            bucket: 存储桶名称
            file_path: 文件路径
            
        Returns:
            Dict: 删除结果
        """
        try:
            result = self.client.storage.from_(bucket).remove([file_path])
            self.logger.info(f"成功删除文件 {bucket}/{file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            raise
    
    def get_file_url(self, bucket: str, file_path: str, 
                    expires_in: int = 3600) -> str:
        """
        获取文件的公开访问URL
        
        Args:
            bucket: 存储桶名称
            file_path: 文件路径
            expires_in: URL过期时间（秒）
            
        Returns:
            str: 文件访问URL
        """
        try:
            result = self.client.storage.from_(bucket).create_signed_url(
                file_path, expires_in
            )
            
            if result.get('signedURL'):
                self.logger.debug(f"成功生成文件URL: {bucket}/{file_path}")
                return result['signedURL']
            else:
                raise Exception("生成文件URL失败")
                
        except Exception as e:
            self.logger.error(f"获取文件URL失败: {e}")
            raise
    
    # ================== 用户认证操作 ==================
    
    def sign_up(self, email: str, password: str, 
               user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            email: 邮箱
            password: 密码
            user_metadata: 用户元数据
            
        Returns:
            Dict: 注册结果
        """
        try:
            result = self.client.auth.sign_up({
                'email': email,
                'password': password,
                'options': {'data': user_metadata} if user_metadata else None
            })
            
            self.logger.info(f"用户注册成功: {email}")
            return result
            
        except Exception as e:
            self.logger.error(f"用户注册失败: {e}")
            raise
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            email: 邮箱
            password: 密码
            
        Returns:
            Dict: 登录结果
        """
        try:
            result = self.client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            self.logger.info(f"用户登录成功: {email}")
            return result
            
        except Exception as e:
            self.logger.error(f"用户登录失败: {e}")
            raise
    
    def sign_out(self) -> Dict[str, Any]:
        """
        用户登出
        
        Returns:
            Dict: 登出结果
        """
        try:
            result = self.client.auth.sign_out()
            self.logger.info("用户登出成功")
            return result
            
        except Exception as e:
            self.logger.error(f"用户登出失败: {e}")
            raise
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        获取当前登录用户信息
        
        Returns:
            Optional[Dict]: 用户信息，未登录返回None
        """
        try:
            user = self.client.auth.get_user()
            if user and user.user:
                return user.user.model_dump()
            return None
            
        except Exception as e:
            self.logger.error(f"获取当前用户信息失败: {e}")
            return None
    
    # ================== 工具方法 ==================
    
    def execute_rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        执行Supabase存储过程/函数
        
        Args:
            function_name: 函数名称
            params: 函数参数
            
        Returns:
            Any: 函数执行结果
        """
        try:
            result = self.client.rpc(function_name, params or {}).execute()
            self.logger.debug(f"成功执行函数 {function_name}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"执行函数 {function_name} 失败: {e}")
            raise
    
    def get_table_count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        获取表记录数量
        
        Args:
            table: 表名
            filters: 过滤条件
            
        Returns:
            int: 记录数量
        """
        try:
            query = self.client.table(table).select('*', count='exact')
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            count = result.count if hasattr(result, 'count') else len(result.data)
            
            self.logger.debug(f"表 {table} 记录数量: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"获取表 {table} 记录数量失败: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            # 尝试执行简单查询来检查连接状态
            result = self.client.table('_health_check').select('*').limit(1).execute()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'url': self.url
            }
            
        except Exception as e:
            self.logger.warning(f"健康检查失败: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'url': self.url
            }


# ================== 便捷函数 ==================

def get_default_manager() -> SupabaseManager:
    """获取默认的Supabase管理器实例"""
    return SupabaseManager()


def quick_save(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """快速保存数据"""
    manager = get_default_manager()
    return manager.insert(table, data)


def quick_query(table: str, filters: Optional[Dict[str, Any]] = None, 
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """快速查询数据"""
    manager = get_default_manager()
    return manager.select(table, filters=filters, limit=limit)