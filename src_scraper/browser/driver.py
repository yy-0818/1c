"""Playwright浏览器驱动模块"""
import asyncio
import json
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from ..core.config_loader import get_config, get_selectors
from ..utils.logger import get_logger

logger = get_logger("browser")

DATA_DIR = Path("data")


class BrowserDriver:
    """Playwright浏览器驱动"""
    
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._config = get_config()
        self._selectors = get_selectors()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("浏览器未初始化")
        return self._page
    
    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("浏览器上下文未初始化")
        return self._context
    
    @property
    def config(self):
        return self._config
    
    @property
    def selectors(self):
        return self._selectors
    
    @property
    def data_dir(self) -> Path:
        return DATA_DIR
    
    @property
    def workspace_url(self) -> str:
        """工作区主页URL"""
        return f"{self._config.clobus.url}/a/acc314/53211/en/"
    
    async def initialize(self, force_new: bool = False) -> None:
        if self._browser is not None and not force_new:
            return
        
        logger.info("正在初始化浏览器...")
        
        if self._browser:
            await self.close()
        
        self._playwright = await async_playwright().start()
        
        self._browser = await self._playwright.chromium.launch(
            headless=self._config.scraper.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self._config.scraper.user_agent,
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        session_file = DATA_DIR / "session.json"
        if session_file.exists():
            try:
                cookies = json.loads(session_file.read_text())
                await self._context.add_cookies(cookies)
                logger.info("已加载保存的会话")
            except Exception as e:
                logger.warning(f"加载会话失败: {e}")
        
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self._config.scraper.timeout)
        
        logger.info("浏览器初始化完成")
    
    async def save_session(self) -> None:
        if self._context is None:
            return
        cookies = await self._context.cookies()
        session_file = DATA_DIR / "session.json"
        session_file.write_text(json.dumps(cookies, indent=2))
        logger.info("会话已保存")
    
    async def clear_session(self) -> None:
        session_file = DATA_DIR / "session.json"
        if session_file.exists():
            session_file.unlink()
            logger.info("会话已清除")
    
    async def close(self) -> None:
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
            self._page = None
        
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        
        logger.info("浏览器已关闭")
    
    async def screenshot(self, name: str, full_page: bool = False) -> str:
        if not name.startswith('data/'):
            name = f"data/{name}"
        path = DATA_DIR / name.replace('data/', '')
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._page.screenshot(path=str(path), full_page=full_page)
        logger.info(f"截图已保存: {path}")
        return str(path)
    
    def is_current_page_logged_in(self) -> bool:
        """检查当前页面是否已登录（不导航）"""
        try:
            page_title = self._page.title()
            if '1C:Enterprise' in page_title:
                return True
            
            captionbar = self._page.query_selector("#captionbar")
            if captionbar:
                return True
            
            return True
        except Exception:
            return False
