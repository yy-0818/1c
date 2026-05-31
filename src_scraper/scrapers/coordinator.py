"""主爬虫协调器"""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from ..browser.driver import BrowserDriver
from ..browser.auth import AuthManager
from ..storage.local_store import LocalStore, get_local_store
from ..scrapers.customers import CustomerScraper
from ..scrapers.products import ProductScraper
from ..scrapers.orders import OrderScraper
from ..utils.logger import get_logger

logger = get_logger("coordinator")


def get_store():
    """获取存储实例 - 强制使用本地存储"""
    logger.info("使用本地存储")
    return get_local_store()


class ScraperCoordinator:
    """爬虫协调器 - 管理所有抓取任务"""

    def __init__(
        self,
        driver: Optional[BrowserDriver] = None,
        store: Optional[LocalStore] = None,
        skip_login_check: bool = False,
        close_driver_on_exit: bool = True
    ):
        self.driver = driver
        self.store = store or get_store()
        self.auth = None
        self.scrapers = {}
        self._skip_login_check = skip_login_check
        self._close_driver_on_exit = close_driver_on_exit

    async def __aenter__(self):
        if self.driver is None:
            from ..browser.driver import BrowserDriver
            self.driver = BrowserDriver()
            await self.driver.initialize()

        self.auth = AuthManager(self.driver)

        self.scrapers = {
            'customers': CustomerScraper(self.driver, self.store),
            'products': ProductScraper(self.driver, self.store),
            'orders': OrderScraper(self.driver, self.store),
        }

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._close_driver_on_exit and self.driver:
            await self.driver.close()

    async def ensure_logged_in(self) -> bool:
        """确保已登录"""
        if self._skip_login_check:
            logger.info("跳过登录检查（交互模式已验证）")
            return True
        
        if self.driver is None:
            return False

        if self.driver.is_current_page_logged_in():
            logger.info("当前页面已登录")
            return True

        try:
            return await self.auth.login()
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False

    async def scrape_all(self, **kwargs) -> Dict[str, Any]:
        """抓取所有数据"""
        results = {}

        if not await self.ensure_logged_in():
            return {
                "success": False,
                "errors": ["登录失败"]
            }

        sync_id = self.store.start_sync("all", mode="full")

        try:
            logger.info("=" * 40)
            logger.info("开始抓取客户数据")
            logger.info("=" * 40)
            results['customers'] = await self.scrapers['customers'].scrape(**kwargs)

            logger.info("=" * 40)
            logger.info("开始抓取产品数据")
            logger.info("=" * 40)
            results['products'] = await self.scrapers['products'].scrape(**kwargs)

            logger.info("=" * 40)
            logger.info("开始抓取订单数据")
            logger.info("=" * 40)
            results['orders'] = await self.scrapers['orders'].scrape(**kwargs)

            total = sum(r.get('count', 0) for r in results.values())

            self.store.end_sync(sync_id, success=True, records_synced=total)

            return {
                "success": True,
                "total": total,
                "results": results
            }

        except Exception as e:
            logger.error(f"抓取出错: {e}")
            self.store.end_sync(sync_id, success=False)
            return {
                "success": False,
                "error": str(e),
                "results": results
            }

    async def scrape_customers(self, **kwargs) -> Dict[str, Any]:
        """只抓取客户"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("customers", mode="incremental")

        try:
            result = await self.scrapers['customers'].scrape(**kwargs)
            self.store.end_sync(sync_id, success=True, records_synced=result.get('count', 0))
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"抓取客户出错: {e}")
            self.store.end_sync(sync_id, success=False)
            return {"success": False, "error": str(e)}

    async def scrape_products(self, **kwargs) -> Dict[str, Any]:
        """只抓取产品"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("products", mode="incremental")

        try:
            result = await self.scrapers['products'].scrape(**kwargs)
            self.store.end_sync(sync_id, success=True, records_synced=result.get('count', 0))
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"抓取产品出错: {e}")
            self.store.end_sync(sync_id, success=False)
            return {"success": False, "error": str(e)}

    async def scrape_orders(self, **kwargs) -> Dict[str, Any]:
        """只抓取订单"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("orders", mode="incremental")

        try:
            result = await self.scrapers['orders'].scrape(**kwargs)
            self.store.end_sync(sync_id, success=True, records_synced=result.get('count', 0))
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"抓取订单出错: {e}")
            self.store.end_sync(sync_id, success=False)
            return {"success": False, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.store.get_stats()
        sync_history = self.store.get_sync_history(limit=5)

        return {
            "data_stats": stats,
            "sync_history": sync_history,
            "last_sync": sync_history[0] if sync_history else None
        }


async def run_scraper(task: str = "all", **kwargs):
    """运行爬虫的便捷函数"""
    async with ScraperCoordinator() as coordinator:
        if task == "all":
            return await coordinator.scrape_all(**kwargs)
        elif task == "customers":
            return await coordinator.scrape_customers(**kwargs)
        elif task == "products":
            return await coordinator.scrape_products(**kwargs)
        elif task == "orders":
            return await coordinator.scrape_orders(**kwargs)
        else:
            return {"success": False, "error": f"未知任务: {task}"}
