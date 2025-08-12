#!/usr/bin/env python3
"""
统一配置管理器
提供集中式配置加载、验证和管理功能
"""

import os
import sys
import json
import hashlib
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

import yaml

# Import logger with fallback to avoid circular imports
try:
    from utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigManager:
    """
    统一配置管理器
    
    负责加载、验证和管理所有配置源：
    - INI配置文件
    - YAML配置文件
    - 环境变量
    - 程序化配置
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """初始化配置管理器"""
        # Initialize logger with fallback
        if hasattr(logger, 'get_logger'):
            self.logger = logger.get_logger("config_manager")
        else:
            self.logger = logger
            self.logger.setLevel(logging.INFO)
        
        # 设置配置目录
        if config_dir is None:
            self.config_dir = Path(__file__).parent.parent
        else:
            self.config_dir = Path(config_dir)
        
        # 配置文件路径
        self.config_ini_path = self.config_dir / 'config.ini'
        self.config_template_path = self.config_dir / 'config_template.ini'
        self.strategy_map_path = self.config_dir / 'stock_strategy_map.yml'
        self.strategy_template_path = self.config_dir / 'stock_strategy_map_template.yml'
        
        # 配置数据存储
        self._config_data = {}
        self._strategy_map = {}
        self._env_overrides = {}
        
        # 默认配置
        self._default_config = self._get_default_config()
        
        # 加载配置
        self._load_all_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'FutuOpenD.Config': {
                'Host': '127.0.0.1',
                'Port': '11111',
                'WebSocketPort': '33333',
                'TrdEnv': 'SIMULATE',
                'Timeout': '10',
                'EnableProtoEncrypt': 'false',
                'LogLevel': 'INFO'
            },
            'FutuOpenD.Credential': {
                'Username': '',
                'Password_md5': ''
            },
            'FutuOpenD.DataFormat': {
                'HistoryDataFormat': '["code","time_key","open","close","high","low","volume","turnover"]',
                'SubscribedDataFormat': 'None'
            },
            'TradePreference': {
                'LotSizeMultiplier': '1',
                'MaxPercPerAsset': '10',
                'StockList': '[]',
                'OrderSize': '100',
                'OrderType': 'NORMAL',
                'AutoNormalize': 'true',
                'MaxPositions': '10'
            },
            'Email': {
                'SmtpServer': '',
                'SmtpPort': '587',
                'EmailUser': '',
                'EmailPass': '',
                'EmailTo': '',
                'SubscriptionList': '[]'
            },
            'TuShare.Credential': {
                'Token': ''
            }
        }
    
    def _load_all_config(self):
        """加载所有配置源"""
        try:
            # 1. 加载默认配置
            self._config_data = self._default_config.copy()
            
            # 2. 加载INI配置文件
            self._load_ini_config()
            
            # 3. 加载YAML策略映射
            self._load_strategy_map()
            
            # 4. 加载环境变量覆盖
            self._load_env_overrides()
            
            # 5. 应用环境变量覆盖
            self._apply_env_overrides()
                        
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_ini_config(self):
        """加载INI配置文件"""
        config_path = self.config_ini_path
        
        # 检查配置文件是否存在
        if not config_path.exists():
            if self.config_template_path.exists():
                self.logger.warning(f"Config file not found, using template: {self.config_template_path}")
                config_path = self.config_template_path
            else:
                self.logger.warning("No config file found, using default configuration")
                return
        
        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding='utf-8')
            
            # 将INI数据合并到配置字典
            for section_name in parser.sections():
                if section_name not in self._config_data:
                    self._config_data[section_name] = {}
                
                for key, value in parser[section_name].items():
                    self._config_data[section_name][key] = value
            
        except Exception as e:
            self.logger.error(f"Failed to load INI config from {config_path}: {e}")
            raise
    
    def _load_strategy_map(self):
        """加载策略映射配置"""
        strategy_path = self.strategy_map_path
        
        if not strategy_path.exists():
            if self.strategy_template_path.exists():
                self.logger.warning(f"Strategy map not found, using template: {self.strategy_template_path}")
                strategy_path = self.strategy_template_path
            else:
                self.logger.warning("No strategy map found, using empty mapping")
                self._strategy_map = {}
                return
        
        try:
            with open(strategy_path, 'r', encoding='utf-8') as f:
                self._strategy_map = yaml.safe_load(f) or {}
            
            self.logger.info(f"Strategy mapping loaded from: {strategy_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load strategy map from {strategy_path}: {e}")
            self._strategy_map = {}
    
    def _load_env_overrides(self):
        """加载环境变量覆盖"""
        env_mapping = {
            'FUTU_HOST': ('FutuOpenD.Config', 'Host'),
            'FUTU_PORT': ('FutuOpenD.Config', 'Port'),
            'FUTU_TRADE_PWD': ('FutuOpenD.Credential', 'Password'),
            'FUTU_TRADE_PWD_MD5': ('FutuOpenD.Credential', 'Password_md5'),
            'FUTU_TRD_ENV': ('FutuOpenD.Config', 'TrdEnv'),
            'FUTU_TIMEOUT': ('FutuOpenD.Config', 'Timeout'),
            'FUTU_ENCRYPT': ('FutuOpenD.Config', 'EnableProtoEncrypt'),
            'FUTU_LOG_LEVEL': ('FutuOpenD.Config', 'LogLevel'),
            'FUTU_WEBSOCKET_PORT': ('FutuOpenD.Config', 'WebSocketPort'),
            'TUSHARE_TOKEN': ('TuShare.Credential', 'Token'),
            'EMAIL_SMTP_SERVER': ('Email', 'SmtpServer'),
            'EMAIL_SMTP_PORT': ('Email', 'SmtpPort'),
            'EMAIL_USER': ('Email', 'EmailUser'),
            'EMAIL_PASS': ('Email', 'EmailPass'),
            'EMAIL_TO': ('Email', 'EmailTo')
        }
        
        self._env_overrides = {}
        for env_var, (section, key) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                if section not in self._env_overrides:
                    self._env_overrides[section] = {}
                self._env_overrides[section][key] = value
                self.logger.info(f"Environment override: {env_var} -> [{section}].{key}")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        for section, overrides in self._env_overrides.items():
            if section not in self._config_data:
                self._config_data[section] = {}
            
            for key, value in overrides.items():
                self._config_data[section][key] = value
    
    def get_config(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """获取配置值"""
        try:
            if section not in self._config_data:
                return default
            
            if key is None:
                return self._config_data[section]
            
            return self._config_data[section].get(key, default)
            
        except Exception as e:
            self.logger.error(f"Failed to get config [{section}].{key}: {e}")
            return default
    
    def set_config(self, section: str, key: str, value: Any):
        """设置配置值"""
        try:
            if section not in self._config_data:
                self._config_data[section] = {}
            
            self._config_data[section][key] = str(value)
            self.logger.info(f"Config updated: [{section}].{key} = {value}")
            
        except Exception as e:
            self.logger.error(f"Failed to set config [{section}].{key}: {e}")
            raise
    
    def get_strategy_map(self) -> Dict[str, Any]:
        """获取策略映射"""
        return self._strategy_map.copy()
    
    def validate_config(self) -> ConfigValidationResult:
        """验证配置完整性"""
        errors = []
        warnings = []
        
        try:
            # 验证富途配置
            futu_config = self.get_config('FutuOpenD.Config', default={})
            
            # 检查必需的配置项
            required_keys = ['Host', 'Port', 'TrdEnv']
            for key in required_keys:
                if not futu_config.get(key):
                    errors.append(f"Missing required config: [FutuOpenD.Config].{key}")
            
            # 验证端口号
            try:
                port = int(futu_config.get('Port', '11111'))
                if port < 1 or port > 65535:
                    errors.append(f"Invalid port number: {port}")
            except ValueError:
                errors.append(f"Invalid port format: {futu_config.get('Port')}")
            
            # 验证交易环境
            trd_env = futu_config.get('TrdEnv', '').upper()
            if trd_env not in ['SIMULATE', 'REAL']:
                errors.append(f"Invalid trading environment: {trd_env}")
            
            # 验证凭证配置
            cred_config = self.get_config('FutuOpenD.Credential', default={})
            if not cred_config.get('Password_md5'):
                warnings.append("No trading password configured")
            
            # 验证邮件配置
            email_config = self.get_config('Email', default={})
            if email_config.get('SmtpServer') and not email_config.get('EmailUser'):
                warnings.append("Email server configured but no user specified")
            
            # 验证策略映射
            if not self._strategy_map:
                warnings.append("No strategy mapping configured")
            
            # 验证配置文件存在性
            if not self.config_ini_path.exists():
                warnings.append("Main config file does not exist, using template or defaults")
            
            result = ConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
            if result.is_valid:
                self.logger.info("Configuration validation passed")
            else:
                self.logger.warning(f"Configuration validation failed: {len(errors)} errors, {len(warnings)} warnings")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Validation exception: {e}"],
                warnings=[]
            )
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
            
            # 创建配置解析器
            parser = configparser.ConfigParser()
            
            # 添加所有配置节
            for section_name, section_data in self._config_data.items():
                parser.add_section(section_name)
                for key, value in section_data.items():
                    parser[section_name][key] = str(value)
            
            # 保存配置文件
            with open(self.config_ini_path, 'w', encoding='utf-8') as f:
                parser.write(f)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reload_config(self):
        """重新加载配置"""
        try:
            self._load_all_config()
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            raise
    
    def get_futu_config(self) -> Dict[str, Any]:
        """获取富途API配置"""
        config = self.get_config('FutuOpenD.Config', default={})
        cred = self.get_config('FutuOpenD.Credential', default={})
        
        return {
            'host': config.get('Host', '127.0.0.1'),
            'port': int(config.get('Port', '11111')),
            'websocket_port': int(config.get('WebSocketPort', '33333')),
            'trd_env': config.get('TrdEnv', 'SIMULATE'),
            'timeout': int(config.get('Timeout', '10')),
            'enable_proto_encrypt': config.get('EnableProtoEncrypt', 'false').lower() == 'true',
            'log_level': config.get('LogLevel', 'INFO'),
            'trade_pwd_md5': cred.get('Password_md5', ''),
            'username': cred.get('Username', '')
        }
    
    def get_email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        config = self.get_config('Email', default={})
        
        return {
            'smtp_server': config.get('SmtpServer', ''),
            'smtp_port': int(config.get('SmtpPort', '587')),
            'email_user': config.get('EmailUser', ''),
            'email_pass': config.get('EmailPass', ''),
            'email_to': config.get('EmailTo', ''),
            'subscription_list': self._parse_json_list(config.get('SubscriptionList', '[]'))
        }
    
    def get_trade_preference(self) -> Dict[str, Any]:
        """获取交易偏好配置"""
        config = self.get_config('TradePreference', default={})
        
        return {
            'lot_size_multiplier': int(config.get('LotSizeMultiplier', '1')),
            'max_perc_per_asset': float(config.get('MaxPercPerAsset', '10')),
            'stock_list': self._parse_json_list(config.get('StockList', '[]')),
            'order_size': int(config.get('OrderSize', '100')),
            'order_type': config.get('OrderType', 'NORMAL'),
            'auto_normalize': config.get('AutoNormalize', 'true').lower() == 'true',
            'max_positions': int(config.get('MaxPositions', '10'))
        }
    
    def _parse_json_list(self, json_str: str) -> List[str]:
        """解析JSON列表字符串"""
        try:
            return json.loads(json_str) if json_str else []
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON list: {json_str}")
            return []
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'config_dir': str(self.config_dir),
            'config_file': str(self.config_ini_path),
            'config_exists': self.config_ini_path.exists(),
            'strategy_map_exists': self.strategy_map_path.exists(),
            'sections': list(self._config_data.keys()),
            'env_overrides': list(self._env_overrides.keys()) if self._env_overrides else [],
            'validation': self.validate_config(),
            'last_loaded': datetime.now().isoformat()
        }


# 全局配置管理器实例
_global_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def reload_global_config():
    """重新加载全局配置"""
    global _global_config_manager
    if _global_config_manager is not None:
        _global_config_manager.reload_config()
    else:
        _global_config_manager = ConfigManager()


# 兼容性函数，保持向后兼容
def get_config(section: str, key: Optional[str] = None, default: Any = None) -> Any:
    """获取配置值（兼容性函数）"""
    return get_config_manager().get_config(section, key, default)


def get_strategy_map() -> Dict[str, Any]:
    """获取策略映射（兼容性函数）"""
    return get_config_manager().get_strategy_map()