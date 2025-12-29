import datetime
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from colorama import init, Fore, Style, Back
init(autoreset=True)

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")

class ColorFormatter(logging.Formatter):
    # Change this dictionary to suit your coloring needs!
    COLORS = {
        "WARNING": Fore.RED,
        "ERROR": Fore.RED + Back.WHITE,
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "CRITICAL": Fore.RED + Back.WHITE
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)


class ColorLogger(logging.Logger):

    log_file_name   = "decidra_monitor.log"
    log_folder_name = ".runtime/log/"

    def __init__(self, name, app_config=None, path=None):
        """初始化ColorLogger

        Args:
            name: logger名称
            app_config: 应用配置字典，如果为None则使用默认配置
        """
        if path is None:
            path = Path(__file__).parent.parent
        log_folder = os.path.join(path, self.log_folder_name)
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_folder, f"{self.log_file_name}")
        # 从配置获取日志等级，默认DEBUG
        default_level = logging.DEBUG
        if app_config:
            level_str = app_config.get('log_level', 'DEBUG')
            default_level = getattr(logging, level_str, logging.DEBUG)

        logging.Logger.__init__(self, name, default_level)

        # 根据配置决定是否添加文件处理器
        if app_config is None or app_config.get('log_to_file', True):
            # 使用配置的文件大小和备份数量
            max_bytes = (app_config.get('log_file_max_size', 10) * 1024 * 1024) if app_config else (10 * 1024 * 1024)
            backup_count = app_config.get('log_file_backup_count', 5) if app_config else 5

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(FORMATTER)
            self.addHandler(file_handler)

        # 根据配置决定是否添加控制台处理器
        if app_config and app_config.get('log_to_console', False):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ColorFormatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s"))
            self.addHandler(console_handler)

        self.propagate = False

def get_logger(logger_name, log_level=None, app_config=None, path=None):
    """获取logger实例

    Args:
        logger_name: logger名称
        log_level: 日志等级，如果为None则使用配置中的等级
        app_config: 应用配置字典，如果为None则使用默认配置

    Returns:
        ColorLogger实例
    """
    logger = ColorLogger(logger_name, app_config, path)

    # 如果明确指定了日志等级，则覆盖配置
    if log_level is not None:
        logger.setLevel(log_level)
    elif app_config:
        level_str = app_config.get('log_level', 'DEBUG')
        level = getattr(logging, level_str, logging.DEBUG)
        logger.setLevel(level)

    return logger

def setup_logger(logger_name=__name__):
    """设置logger（向后兼容函数）"""
    return ColorLogger(logger_name)