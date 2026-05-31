"""配置加载模块"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ClobusConfig(BaseModel):
    """Clobus配置"""
    url: str
    username: str
    password: str


class SupabaseConfig(BaseModel):
    """Supabase配置"""
    url: str
    anon_key: str
    service_key: str = ""


class ScraperConfig(BaseModel):
    """爬虫配置"""
    headless: bool = False
    timeout: int = 60000
    retry_count: int = 3
    delay_between_pages: int = 2
    delay_between_actions: float = 0.5
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    file: str = "logs/scraper.log"
    max_size: int = 10 * 1024 * 1024
    backup_count: int = 5


class Config(BaseModel):
    """主配置"""
    clobus: ClobusConfig
    supabase: SupabaseConfig
    scraper: ScraperConfig
    logging: LoggingConfig


_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置文件"""
    global _config
    
    if _config is not None:
        return _config
    
    if config_path is None:
        config_dir = Path(__file__).parent.parent.parent / "config"
        config_path = config_dir / "settings.yaml"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    _config = Config(**data)
    return _config


def load_selectors(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载页面选择器配置"""
    if config_path is None:
        config_dir = Path(__file__).parent.parent.parent / "config"
        config_path = config_dir / "selectors.yaml"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"选择器配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_config() -> Config:
    """获取已加载的配置"""
    global _config
    if _config is None:
        return load_config()
    return _config


def get_selectors() -> Dict[str, Any]:
    """获取页面选择器"""
    return load_selectors()
