"""爬虫包初始化"""
from .browser import BrowserDriver, get_driver
from .core import load_config, get_config, get_selectors
from .utils import setup_logger, get_logger

__version__ = "1.0.0"
