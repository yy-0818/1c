"""日志配置模块"""
import os
import sys
from pathlib import Path
from loguru import logger


def setup_logger(
    log_file: str = "logs/scraper.log",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
) -> None:
    """配置日志系统"""
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=level,
        format=format_string,
        colorize=True
    )
    
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加文件输出
    logger.add(
        log_file,
        level=level,
        format=format_string,
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True
    )


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger
