"""Playwright浏览器驱动模块"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config_loader import get_config, get_selectors
from ..utils.logger import get_logger

logger = get_logger("browser")


class BrowserDriver:
    """Playwright浏览器驱动"""
    
    _instance: Optional['BrowserDriver'] = None
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self) -> None:
        """初始化浏览器"""
        if self._browser is not None:
            return
        
        config = get_config()
        selectors = get_selectors()
        
        logger.info("正在初始化浏览器...")
        
        self._playwright = await async_playwright().start()
        
        # 启动浏览器
        self._browser = await self._playwright.chromium.launch(
            headless=config.scraper.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # 创建上下文（隔离会话）
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=config.scraper.user_agent,
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        
        # 隐藏webdriver特征
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
        
        # 尝试加载保存的会话
        session_file = Path("data/session.json")
        if session_file.exists():
            try:
                cookies = json.loads(session_file.read_text())
                await self._context.add_cookies(cookies)
                logger.info("已加载保存的会话")
            except Exception as e:
                logger.warning(f"加载会话失败: {e}")
        
        # 创建页面
        self._page = await self._context.new_page()
        
        # 设置默认超时
        self._page.set_default_timeout(config.scraper.timeout)
        
        logger.info("浏览器初始化完成")
    
    @property
    def page(self) -> Page:
        """获取当前页面"""
        if self._page is None:
            raise RuntimeError("浏览器未初始化")
        return self._page
    
    @property
    def context(self) -> BrowserContext:
        """获取当前上下文"""
        if self._context is None:
            raise RuntimeError("浏览器上下文未初始化")
        return self._context
    
    async def save_session(self) -> None:
        """保存会话到文件"""
        if self._context is None:
            return
        
        cookies = await self._context.cookies()
        session_file = Path("data/session.json")
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(cookies, indent=2))
        logger.info("会话已保存")
    
    async def close(self) -> None:
        """关闭浏览器"""
        if self._page:
            await self._page.close()
            self._page = None
        
        if self._context:
            await self._context.close()
            self._context = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        logger.info("浏览器已关闭")
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        config = get_config()
        selectors = get_selectors()
        
        try:
            # 尝试访问主页
            await self._page.goto(config.clobus.url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(1)
            
            # 检查是否有退出按钮或其他登录成功的标志
            success_indicator = selectors.get('login', {}).get('success_indicator', '')
            if success_indicator:
                element = await self._page.query_selector(success_indicator)
                return element is not None
            
            # 检查URL是否包含登录相关路径
            current_url = self._page.url
            if 'login' in current_url.lower():
                return False
            
            return True
        except Exception:
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def wait_for_element(
        self,
        selector: str,
        timeout: Optional[int] = None,
        state: str = "visible"
    ) -> Optional[Any]:
        """等待元素出现"""
        config = get_config()
        timeout = timeout or config.scraper.timeout
        
        try:
            element = await self._page.wait_for_selector(
                selector,
                timeout=timeout,
                state=state
            )
            return element
        except Exception as e:
            logger.debug(f"等待元素 {selector} 超时: {e}")
            return None
    
    async def click_safe(self, selector: str, delay: float = 0.5) -> bool:
        """安全点击元素"""
        config = get_config()
        
        try:
            element = await self.wait_for_element(selector)
            if element:
                await element.click()
                await asyncio.sleep(delay)
                return True
            return False
        except Exception as e:
            logger.error(f"点击元素失败 {selector}: {e}")
            return False
    
    async def type_safe(self, selector: str, text: str, delay: float = 0.1) -> bool:
        """安全输入文本"""
        config = get_config()
        
        try:
            element = await self.wait_for_element(selector)
            if element:
                await element.fill("")
                await element.type(text, delay=delay)
                return True
            return False
        except Exception as e:
            logger.error(f"输入文本失败 {selector}: {e}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """获取元素文本"""
        try:
            element = await self.wait_for_element(selector)
            if element:
                return await element.inner_text()
            return None
        except Exception:
            return None
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """获取元素属性"""
        try:
            element = await self.wait_for_element(selector)
            if element:
                return await element.get_attribute(attribute)
            return None
        except Exception:
            return None
    
    async def screenshot(self, path: str, full_page: bool = False) -> None:
        """截图"""
        config = get_config()
        await self._page.screenshot(path=path, full_page=full_page)
        logger.info(f"截图已保存: {path}")


@asynccontextmanager
async def get_driver():
    """获取浏览器驱动的上下文管理器"""
    driver = BrowserDriver()
    await driver.initialize()
    try:
        yield driver
    finally:
        await driver.close()
