"""
统一日志管理模块
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from core.config import app_config


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 定义颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "news_crawler",
    level: str = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = level or app_config.log_level
    logger.setLevel(getattr(logging, log_level))
    
    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    if sys.stdout.isatty():  # 终端环境使用彩色
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
    else:
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器"""
    if name is None:
        name = "news_crawler"
    return logging.getLogger(name)


# 创建默认日志记录器
default_logger = setup_logger(
    log_file=f"logs/news_crawler_{datetime.now().strftime('%Y%m%d')}.log"
)
