"""抓取基类模块"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..browser.driver import BrowserDriver
from ..storage.supabase_store import SupabaseStore, get_store
from ..utils.logger import get_logger


class BaseScraper(ABC):
    """抓取器基类"""

    def __init__(self, driver: BrowserDriver, store: Optional[SupabaseStore] = None):
        self.driver = driver
        self.store = store or get_store()
        self.logger = get_logger(self.__class__.__name__)
        self.config = self.driver.config
        self.selectors = self.driver.selectors

    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        执行抓取

        Returns:
            Dict包含:
                - success: bool
                - count: int 抓取数量
                - data: List[Dict] 抓取的数据
                - errors: List[str] 错误列表
        """
        pass

    async def wait_for_load(self, timeout: int = 10000) -> bool:
        """等待页面加载"""
        try:
            await asyncio.sleep(1)
            await self.driver.wait_for_element("body", timeout=timeout)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            self.logger.warning(f"等待页面加载失败: {e}")
            return False

    async def find_element(self, selector: str) -> Optional[Any]:
        """查找单个元素"""
        try:
            return await self.driver.page.query_selector(selector)
        except Exception:
            return None

    async def find_elements(self, selector: str) -> List[Any]:
        """查找多个元素"""
        try:
            return await self.driver.page.query_selector_all(selector)
        except Exception:
            return []

    async def click(self, selector: str) -> bool:
        """点击元素"""
        element = await self.find_element(selector)
        if element:
            await element.click()
            await asyncio.sleep(0.5)
            return True
        return False

    async def get_text(self, selector: str) -> Optional[str]:
        """获取元素文本"""
        element = await self.find_element(selector)
        if element:
            return await element.inner_text()
        return None

    async def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        """获取元素属性"""
        element = await self.find_element(selector)
        if element:
            return await element.get_attribute(attr)
        return None

    async def navigate_to(self, url: str) -> bool:
        """导航到URL"""
        try:
            await self.driver.page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"导航失败: {e}")
            return False

    async def take_screenshot(self, name: str) -> str:
        """截图"""
        path = f"data/{name}.png"
        await self.driver.screenshot(path)
        return path


class PaginationScraper(BaseScraper):
    """支持分页的抓取器基类"""

    async def scrape_with_pagination(
        self,
        url: str,
        rows_selector: str,
        parse_row_func,  # 解析每一行的函数
        page_size: int = 100,
        max_pages: int = 100
    ) -> Dict[str, Any]:
        """分页抓取"""
        all_data = []
        errors = []
        current_page = 1

        self.logger.info(f"开始分页抓取: {url}")

        # 导航到列表页
        if not await self.navigate_to(url):
            return {
                "success": False,
                "count": 0,
                "data": [],
                "errors": ["无法导航到页面"]
            }

        await self.wait_for_load()

        while current_page <= max_pages:
            self.logger.info(f"抓取第 {current_page} 页...")

            # 等待数据加载
            try:
                await self.driver.page.wait_for_selector(rows_selector, timeout=10000)
            except Exception:
                self.logger.warning(f"第 {current_page} 页未找到数据")
                break

            # 获取当前页数据
            rows = await self.find_elements(rows_selector)
            if not rows:
                self.logger.info("没有更多数据")
                break

            for row in rows:
                try:
                    data = await parse_row_func(row)
                    if data:
                        all_data.append(data)
                except Exception as e:
                    errors.append(str(e))
                    self.logger.debug(f"解析行失败: {e}")

            self.logger.info(f"第 {current_page} 页完成，已抓取 {len(all_data)} 条")

            # 检查是否有下一页
            if not await self._has_next_page():
                break

            # 点击下一页
            if not await self._click_next_page():
                break

            current_page += 1
            await asyncio.sleep(1)  # 避免请求过快

        return {
            "success": True,
            "count": len(all_data),
            "data": all_data,
            "errors": errors,
            "total_pages": current_page
        }

    async def _has_next_page(self) -> bool:
        """检查是否有下一页"""
        next_selectors = [
            "button[title*='следующ']",
            "button[title*='next']",
            "button[title*='Next']",
            "[class*='nextPage']",
            "[class*='next']"
        ]
        for sel in next_selectors:
            element = await self.find_element(sel)
            if element:
                is_disabled = await element.get_attribute("disabled")
                if is_disabled is None:
                    return True
        return False

    async def _click_next_page(self) -> bool:
        """点击下一页"""
        next_selectors = [
            "button[title*='следующ']",
            "button[title*='next']",
            "button[title*='Next']",
            "[class*='nextPage']"
        ]
        for sel in next_selectors:
            element = await self.find_element(sel)
            if element:
                is_disabled = await element.get_attribute("disabled")
                if is_disabled is None:
                    await element.click()
                    await asyncio.sleep(1)
                    return True
        return False
