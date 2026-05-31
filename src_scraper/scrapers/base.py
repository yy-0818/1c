"""抓取基类模块"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..browser.driver import BrowserDriver
from ..utils.logger import get_logger


def get_store():
    """获取存储实例 - 强制使用本地存储"""
    from ..storage.local_store import LocalStore
    return LocalStore()


class BaseScraper(ABC):
    """抓取器基类"""

    def __init__(self, driver: BrowserDriver, store=None):
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

    async def screenshot(self, name: str) -> str:
        """截图"""
        return await self.driver.screenshot(name)


class PaginationScraper(BaseScraper, ABC):
    """带分页的抓取器基类"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_page = 1
        self.max_pages = 100
        self.total_pages = 1

    async def navigate_with_pagination(self, url: str, page: int = 1) -> bool:
        """
        带分页的导航
        
        Args:
            url: 基础URL
            page: 页码（从1开始）
            
        Returns:
            是否导航成功
        """
        page_param = f"page={page}" if "?" in url else f"?page={page}"
        full_url = f"{url}{page_param}" if page == 1 else f"{url.split('?')[0]}{page_param}"
        
        try:
            await self.driver.page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            self.current_page = page
            return True
        except Exception as e:
            self.logger.error(f"导航失败: {e}")
            return False

    async def scrape_with_pagination(
        self,
        url: str,
        rows_selector: str,
        parse_row_func,
        max_pages: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带分页的抓取

        Args:
            url: 列表页URL
            rows_selector: 行选择器
            parse_row_func: 解析每行的函数
            max_pages: 最大页数

        Returns:
            Dict包含 success, count, data
        """
        all_data = []
        errors = []
        self.max_pages = max_pages

        self.logger.info(f"开始抓取: {url}")

        for page in range(1, max_pages + 1):
            self.logger.info(f"抓取第 {page} 页...")

            # 导航到页面
            if page > 1:
                success = await self.navigate_with_pagination(url, page)
                if not success:
                    errors.append(f"第 {page} 页导航失败")
                    break

            await asyncio.sleep(2)

            # 检查是否为空页
            rows = await self.find_elements(rows_selector)
            if not rows:
                self.logger.info(f"第 {page} 页无数据，停止")
                break

            # 解析数据
            page_data = []
            for row in rows:
                try:
                    item = await parse_row_func(row)
                    if item:
                        page_data.append(item)
                except Exception as e:
                    self.logger.debug(f"解析行失败: {e}")

            if page_data:
                all_data.extend(page_data)
                self.logger.info(f"第 {page} 页: 获取 {len(page_data)} 条")
            else:
                self.logger.info(f"第 {page} 页无有效数据")

            # 检查是否有下一页
            has_next = await self._check_next_page()
            if not has_next:
                self.logger.info("已到达最后一页")
                break

        return {
            "success": True,
            "count": len(all_data),
            "data": all_data,
            "errors": errors if errors else None
        }

    async def _check_next_page(self) -> bool:
        """检查是否有下一页"""
        try:
            # 检查分页按钮
            next_buttons = await self.find_elements("button[title*='следующ'], button[title*='next']")
            for btn in next_buttons:
                is_disabled = await btn.get_attribute("disabled")
                if is_disabled is None:
                    return True
            return False
        except Exception:
            return False
