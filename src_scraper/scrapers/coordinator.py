"""主爬虫协调器"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..browser.driver import BrowserDriver
from ..browser.auth import AuthManager
from ..storage.supabase_store import SupabaseStore, get_store
from ..scrapers.customers import CustomerScraper
from ..scrapers.products import ProductScraper
from ..scrapers.orders import OrderScraper
from ..utils.logger import get_logger

logger = get_logger("coordinator")


class ScraperCoordinator:
    """爬虫协调器 - 管理所有抓取任务"""

    def __init__(
        self,
        driver: Optional[BrowserDriver] = None,
        store: Optional[SupabaseStore] = None
    ):
        self.driver = driver
        self.store = store or get_store()
        self.auth = None
        self.scrapers = {}

    async def __aenter__(self):
        if self.driver is None:
            from ..browser.driver import BrowserDriver
            self.driver = BrowserDriver()
            await self.driver.initialize()

        self.auth = AuthManager(self.driver)

        # 初始化抓取器
        self.scrapers = {
            'customers': CustomerScraper(self.driver, self.store),
            'products': ProductScraper(self.driver, self.store),
            'orders': OrderScraper(self.driver, self.store),
        }

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()

    async def ensure_logged_in(self) -> bool:
        """确保已登录"""
        # 检查会话是否有效
        if await self.driver.is_logged_in():
            logger.info("会话有效，跳过登录")
            return True

        # 尝试登录
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

        # 同步日志ID
        sync_id = self.store.start_sync("all", mode="full")

        try:
            # 抓取客户
            logger.info("=" * 40)
            logger.info("开始抓取客户数据")
            logger.info("=" * 40)
            results['customers'] = await self.scrapers['customers'].scrape(**kwargs)

            # 抓取产品
            logger.info("=" * 40)
            logger.info("开始抓取产品数据")
            logger.info("=" * 40)
            results['products'] = await self.scrapers['products'].scrape(**kwargs)

            # 抓取订单
            logger.info("=" * 40)
            logger.info("开始抓取订单数据")
            logger.info("=" * 40)
            results['orders'] = await self.scrapers['orders'].scrape(**kwargs)

            # 计算总数
            total = sum(r.get('count', 0) for r in results.values())

            # 完成同步日志
            self.store.complete_sync(
                sync_id,
                processed=total,
                created=total,
                updated=0,
                deleted=0,
                failed=len([r for r in results.values() if not r.get('success')])
            )

            return {
                "success": True,
                "total": total,
                "results": results
            }

        except Exception as e:
            logger.error(f"抓取出错: {e}")
            self.store.fail_sync(sync_id, str(e))
            return {
                "success": False,
                "error": str(e),
                "results": results
            }

    async def scrape_customers(self, **kwargs) -> Dict[str, Any]:
        """只抓取客户"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("customers")
        try:
            result = await self.scrapers['customers'].scrape(**kwargs)
            self.store.complete_sync(
                sync_id,
                processed=result.get('count', 0),
                created=result.get('count', 0)
            )
            return result
        except Exception as e:
            self.store.fail_sync(sync_id, str(e))
            return {"success": False, "error": str(e)}

    async def scrape_products(self, **kwargs) -> Dict[str, Any]:
        """只抓取产品"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("products")
        try:
            result = await self.scrapers['products'].scrape(**kwargs)
            self.store.complete_sync(
                sync_id,
                processed=result.get('count', 0),
                created=result.get('count', 0)
            )
            return result
        except Exception as e:
            self.store.fail_sync(sync_id, str(e))
            return {"success": False, "error": str(e)}

    async def scrape_orders(self, **kwargs) -> Dict[str, Any]:
        """只抓取订单"""
        if not await self.ensure_logged_in():
            return {"success": False, "error": "登录失败"}

        sync_id = self.store.start_sync("orders")
        try:
            result = await self.scrapers['orders'].scrape(**kwargs)
            self.store.complete_sync(
                sync_id,
                processed=result.get('count', 0),
                created=result.get('count', 0)
            )
            return result
        except Exception as e:
            self.store.fail_sync(sync_id, str(e))
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
