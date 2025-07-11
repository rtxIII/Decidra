
import configparser
import time
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

# 路径常量
PATH = Path(__file__).parent.parent

PATH_RUNTIME = PATH / '.runtime'
PATH_CONFIG = PATH_RUNTIME / 'config'
PATH_DATA = PATH_RUNTIME / 'data'
PATH_DATABASE = PATH_RUNTIME / 'database'  # Obsoleted
PATH_LOG = PATH_RUNTIME / 'log'

PATH_FILTERS = PATH / 'filters'
PATH_STRATEGIES = PATH / 'strategies'
PATH_FILTER_REPORT = PATH / 'stock_filter_report'
PATH_STRATEGY_REPORT = PATH / 'stock_strategy_report'

# 常量定义
DATETIME_FORMAT_DW = '%Y-%m-%d'
DATETIME_FORMAT_M = ''
ORDER_RETRY_MAX = 3

# 导入新的配置管理器
try:
    from utils.config_manager import get_config_manager, get_config, get_strategy_map
    
    # 使用新的配置管理器
    _config_manager = get_config_manager()
    
    # 向后兼容的配置对象
    class CompatibilityConfigProxy:
        """向后兼容的配置代理对象"""
        
        def __init__(self, config_manager):
            self._config_manager = config_manager
        
        def __getitem__(self, section):
            """支持 config[section] 语法"""
            return self._config_manager.get_config(section, default={})
        
        def get(self, section, key=None, fallback=None):
            """支持 config.get() 方法"""
            return self._config_manager.get_config(section, key, fallback)
        
        def sections(self):
            """获取所有配置节名称"""
            return list(self._config_manager._config_data.keys())
        
        def has_section(self, section):
            """检查配置节是否存在"""
            return section in self._config_manager._config_data
        
        def items(self, section):
            """获取配置节的所有项"""
            section_data = self._config_manager.get_config(section, default={})
            return section_data.items() if isinstance(section_data, dict) else []
    
    # 创建兼容性配置对象
    config = CompatibilityConfigProxy(_config_manager)
    
    # 获取策略映射
    stock_strategy_map = get_strategy_map()
    
except ImportError as e:
    # 如果新配置管理器不可用，回退到旧方式
    print(f"Warning: New config manager not available ({e}), using legacy config loading")
    
    # 原有的配置加载逻辑
    if not (PATH_CONFIG / 'config.ini').is_file():
        if not (PATH_CONFIG / 'config_template.ini').is_file():
            raise SystemExit(
                "Missing config/config.ini. Please use the config/config_template.ini to create your configuration.")
        else:
            print("Please rename config_template.ini to config.ini and update it.")

    config = configparser.ConfigParser()
    config.read(
        PATH_CONFIG / 'config.ini' if (PATH_CONFIG / 'config.ini').is_file() else PATH_CONFIG / 'config_template.ini')

    if not (PATH_CONFIG / "stock_strategy_map.yml").is_file():
        if not (PATH_CONFIG / "stock_strategy_map_template.yml").is_file():
            raise SystemExit(
                "Missing stock_strategy_map.yml. Please use the stock_strategy_map_template.yml to create your configuration.")
        else:
            print("Please rename stock_strategy_map_template.yml to stock_strategy_map.yml and update it.")

    with open(PATH_CONFIG / "stock_strategy_map.yml" if (PATH_CONFIG / "stock_strategy_map.yml").is_file()
              else PATH_CONFIG / "stock_strategy_map_template.yml", 'r') as infile:
        stock_strategy_map = yaml.safe_load(infile)


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed
