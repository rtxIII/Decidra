"""
JsonLite数据操作模块

基于jsonlite包实现的轻量级本地JSON数据库操作类
提供类似MongoDB的API接口，用于本地数据存储和操作
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from jsonlite import JSONlite
except ImportError:
    raise ImportError("请先安装jsonlite包: pip install jsonlite")

from utils.global_vars import get_logger
from utils.global_vars import PATH_DATA


class JsonLiteManager:
    """
    JsonLite数据管理器
    
    提供轻量级的本地JSON数据库操作功能
    支持类似MongoDB的CRUD操作接口
    """
    
    def __init__(self, database_name: str = "decidra_data.json"):
        """
        初始化JsonLite数据管理器
        
        Args:
            database_name: 数据库文件名
        """
        self.logger = get_logger(__name__)
        self.database_name = database_name
        
        # 确保数据目录存在
        os.makedirs(PATH_DATA, exist_ok=True)
        self.db_path = PATH_DATA / database_name
        
        # 初始化数据库连接
        self.db = JSONlite(str(self.db_path))
        
        self.logger.info(f"JsonLite数据库初始化完成: {self.db_path}")
    
    # ================== 基础CRUD操作 ==================
    
    def insert_one(self, document: Dict[str, Any]) -> str:
        """
        插入单个文档
        
        Args:
            document: 要插入的文档数据
            
        Returns:
            str: 插入文档的ID
        """
        try:
            # 添加时间戳
            document['created_at'] = datetime.now().isoformat()
            document['updated_at'] = datetime.now().isoformat()
            
            result = self.db.insert_one(document)
            self.logger.debug(f"插入文档成功: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            self.logger.error(f"插入文档失败: {e}")
            raise
    
    def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        插入多个文档
        
        Args:
            documents: 要插入的文档列表
            
        Returns:
            List[str]: 插入文档的ID列表
        """
        try:
            # 为每个文档添加时间戳
            timestamp = datetime.now().isoformat()
            for doc in documents:
                doc['created_at'] = timestamp
                doc['updated_at'] = timestamp
            
            result = self.db.insert_many(documents)
            ids = [str(obj_id) for obj_id in result.inserted_ids]
            self.logger.debug(f"批量插入文档成功: {len(ids)} 个文档")
            return ids
            
        except Exception as e:
            self.logger.error(f"批量插入文档失败: {e}")
            raise
    
    def find_one(self, filter_dict: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        查找单个文档
        
        Args:
            filter_dict: 查询条件
            
        Returns:
            Optional[Dict]: 查找到的文档，未找到返回None
        """
        try:
            result = self.db.find_one(filter_dict or {})
            if result:
                self.logger.debug(f"查找到文档: {result.get('_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"查找单个文档失败: {e}")
            raise
    
    def find(self, filter_dict: Optional[Dict[str, Any]] = None, 
             limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        查找多个文档
        
        Args:
            filter_dict: 查询条件
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 查找到的文档列表
        """
        try:
            cursor = self.db.find(filter_dict or {})
            results = list(cursor)
            
            if limit:
                results = results[:limit]
            
            self.logger.debug(f"查找到 {len(results)} 个文档")
            return results
            
        except Exception as e:
            self.logger.error(f"查找多个文档失败: {e}")
            raise
    
    def update_one(self, filter_dict: Dict[str, Any], 
                   update_dict: Dict[str, Any]) -> bool:
        """
        更新单个文档
        
        Args:
            filter_dict: 查询条件
            update_dict: 更新数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 添加更新时间戳
            if '$set' in update_dict:
                update_dict['$set']['updated_at'] = datetime.now().isoformat()
            else:
                update_dict['$set'] = {'updated_at': datetime.now().isoformat()}
            
            result = self.db.update_one(filter_dict, update_dict)
            success = result.modified_count > 0
            
            if success:
                self.logger.debug(f"更新文档成功: 修改了 {result.modified_count} 个文档")
            else:
                self.logger.debug("未找到匹配的文档进行更新")
                
            return success
            
        except Exception as e:
            self.logger.error(f"更新单个文档失败: {e}")
            raise
    
    def update_many(self, filter_dict: Dict[str, Any], 
                    update_dict: Dict[str, Any]) -> int:
        """
        更新多个文档
        
        Args:
            filter_dict: 查询条件
            update_dict: 更新数据
            
        Returns:
            int: 更新的文档数量
        """
        try:
            # 添加更新时间戳
            if '$set' in update_dict:
                update_dict['$set']['updated_at'] = datetime.now().isoformat()
            else:
                update_dict['$set'] = {'updated_at': datetime.now().isoformat()}
            
            result = self.db.update_many(filter_dict, update_dict)
            count = result.modified_count
            
            self.logger.debug(f"批量更新文档成功: 修改了 {count} 个文档")
            return count
            
        except Exception as e:
            self.logger.error(f"批量更新文档失败: {e}")
            raise
    
    def delete_one(self, filter_dict: Dict[str, Any]) -> bool:
        """
        删除单个文档
        
        Args:
            filter_dict: 查询条件
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result = self.db.delete_one(filter_dict)
            success = result.deleted_count > 0
            
            if success:
                self.logger.debug(f"删除文档成功: 删除了 {result.deleted_count} 个文档")
            else:
                self.logger.debug("未找到匹配的文档进行删除")
                
            return success
            
        except Exception as e:
            self.logger.error(f"删除单个文档失败: {e}")
            raise
    
    def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """
        删除多个文档
        
        Args:
            filter_dict: 查询条件
            
        Returns:
            int: 删除的文档数量
        """
        try:
            result = self.db.delete_many(filter_dict)
            count = result.deleted_count
            
            self.logger.debug(f"批量删除文档成功: 删除了 {count} 个文档")
            return count
            
        except Exception as e:
            self.logger.error(f"批量删除文档失败: {e}")
            raise
    
    # ================== 业务特定方法 ==================
    
    def save_stock_data(self, stock_code: str, data: Dict[str, Any]) -> str:
        """
        保存股票数据
        
        Args:
            stock_code: 股票代码
            data: 股票数据
            
        Returns:
            str: 文档ID
        """
        document = {
            'type': 'stock_data',
            'stock_code': stock_code,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.insert_one(document)
    
    def get_stock_data(self, stock_code: str, 
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 股票数据列表
        """
        filter_dict = {
            'type': 'stock_data',
            'stock_code': stock_code
        }
        
        return self.find(filter_dict, limit)
    
    def save_trading_record(self, record: Dict[str, Any]) -> str:
        """
        保存交易记录
        
        Args:
            record: 交易记录数据
            
        Returns:
            str: 文档ID
        """
        document = {
            'type': 'trading_record',
            'record': record,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.insert_one(document)
    
    def get_trading_records(self, stock_code: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取交易记录
        
        Args:
            stock_code: 股票代码（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 交易记录列表
        """
        filter_dict = {'type': 'trading_record'}
        
        if stock_code:
            filter_dict['record.stock_code'] = stock_code
        
        # 注意: jsonlite可能不支持复杂的日期查询，这里提供基础实现
        results = self.find(filter_dict)
        
        # 在Python中进行日期过滤
        if start_date or end_date:
            filtered_results = []
            for record in results:
                record_date = record.get('timestamp', '')
                if start_date and record_date < start_date:
                    continue
                if end_date and record_date > end_date:
                    continue
                filtered_results.append(record)
            results = filtered_results
        
        return results
    
    def save_user_config(self, config_key: str, config_value: Any) -> str:
        """
        保存用户配置
        
        Args:
            config_key: 配置键
            config_value: 配置值
            
        Returns:
            str: 文档ID
        """
        # 检查是否已存在该配置
        existing = self.find_one({
            'type': 'user_config',
            'config_key': config_key
        })
        
        if existing:
            # 更新现有配置
            self.update_one(
                {'_id': existing['_id']},
                {'$set': {'config_value': config_value}}
            )
            return str(existing['_id'])
        else:
            # 创建新配置
            document = {
                'type': 'user_config',
                'config_key': config_key,
                'config_value': config_value
            }
            return self.insert_one(document)
    
    def get_user_config(self, config_key: str, default_value: Any = None) -> Any:
        """
        获取用户配置
        
        Args:
            config_key: 配置键
            default_value: 默认值
            
        Returns:
            Any: 配置值
        """
        result = self.find_one({
            'type': 'user_config',
            'config_key': config_key
        })
        
        if result:
            return result.get('config_value', default_value)
        return default_value
    
    # ================== 工具方法 ==================
    
    def count_documents(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        统计文档数量
        
        Args:
            filter_dict: 查询条件
            
        Returns:
            int: 文档数量
        """
        try:
            results = self.find(filter_dict or {})
            count = len(results)
            self.logger.debug(f"统计文档数量: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"统计文档数量失败: {e}")
            raise
    
    def clear_all_data(self) -> bool:
        """
        清空所有数据（危险操作）
        
        Returns:
            bool: 是否成功
        """
        try:
            count = self.delete_many({})
            self.logger.warning(f"清空所有数据完成，删除了 {count} 个文档")
            return True
            
        except Exception as e:
            self.logger.error(f"清空数据失败: {e}")
            return False
    
    def backup_data(self, backup_path: Optional[str] = None) -> str:
        """
        备份数据
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            str: 备份文件路径
        """
        import shutil
        
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(PATH_DATA / f"backup_{timestamp}_{self.database_name}")
        
        try:
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"数据备份完成: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"数据备份失败: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        获取数据库信息
        
        Returns:
            Dict: 数据库信息
        """
        try:
            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            total_documents = self.count_documents()
            
            # 统计不同类型的文档数量
            type_counts = {}
            all_docs = self.find()
            for doc in all_docs:
                doc_type = doc.get('type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            info = {
                'database_path': str(self.db_path),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'total_documents': total_documents,
                'document_types': type_counts,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(self.db_path)).isoformat() if os.path.exists(self.db_path) else None
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取数据库信息失败: {e}")
            raise


# ================== 便捷函数 ==================

def get_default_manager() -> JsonLiteManager:
    """获取默认的JsonLite管理器实例"""
    return JsonLiteManager()


def quick_save(key: str, value: Any) -> str:
    """快速保存数据"""
    manager = get_default_manager()
    return manager.save_user_config(key, value)


def quick_load(key: str, default: Any = None) -> Any:
    """快速加载数据"""
    manager = get_default_manager()
    return manager.get_user_config(key, default)