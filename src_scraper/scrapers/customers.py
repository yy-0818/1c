"""客户数据抓取模块"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..scrapers.base import PaginationScraper
from ..browser.navigation import create_navigation_helper, NavigationHelper
from ..utils.logger import get_logger

logger = get_logger("customers")


class CustomerScraper(PaginationScraper):
    """客户数据抓取器 - 支持1C云版本侧边栏导航"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nav: Optional[NavigationHelper] = None

    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """抓取客户数据"""
        self.logger.info("开始抓取客户数据")

        try:
            # 初始化导航辅助
            self.nav = create_navigation_helper(self.driver.page)

            # 通过侧边栏导航到客户模块
            success = await self.nav.navigate_to("customers")
            if not success:
                self.logger.error("无法导航到客户模块")
                return {"success": False, "count": 0, "data": [], "errors": ["导航失败"]}

            # 等待数据加载
            await asyncio.sleep(3)

            # 展开所有层级分组
            self.logger.info("尝试展开层级分组...")
            await self.nav.expand_all_hierarchical_items()
            await asyncio.sleep(2)

            # 截图诊断
            await self.screenshot("customers_list.png")

            # 滚动加载所有数据（基于数据内容检测）
            self.logger.info("开始滚动加载数据...")
            all_data = await self.scroll_and_extract_all()

            # 去重
            seen = set()
            unique_data = []
            for customer in all_data:
                key = customer.get('name', '') + customer.get('inn', '')
                if key and key not in seen:
                    seen.add(key)
                    unique_data.append(customer)

            self.logger.info(f"共抓取 {len(unique_data)} 条客户数据（去重后）")

            if unique_data:
                if hasattr(self.store, 'upsert_customers'):
                    self.store.upsert_customers(unique_data)

            return {
                "success": True,
                "count": len(unique_data),
                "data": unique_data
            }

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")
            await self.screenshot("customers_error.png")
            return {"success": False, "count": 0, "data": [], "errors": [str(e)]}

    async def scroll_and_extract_all(self) -> List[Dict[str, Any]]:
        """
        滚动页面并提取所有数据
        基于实际数据内容变化来判断是否加载了新数据
        """
        all_data = []
        seen_keys = set()  # 用于检测新数据
        max_scrolls = 100
        scroll_delay = 1.5
        no_new_data_count = 0

        self.logger.info("开始滚动提取数据...")

        # 聚焦gridBody
        await self.page.evaluate("""() => {
            const gridBody = document.querySelector('.gridBody');
            if (gridBody) {
                gridBody.focus();
            }
        }""")

        for i in range(max_scrolls):
            # 滚动
            await self.page.keyboard.press('PageDown')
            await asyncio.sleep(scroll_delay)

            # 额外设置scrollTop确保滚动
            await self.page.evaluate("""() => {
                const gridBody = document.querySelector('.gridBody');
                if (gridBody) {
                    gridBody.scrollTop = gridBody.scrollHeight;
                }
            }""")
            await asyncio.sleep(0.3)

            # 提取当前页数据
            page_data = await self._extract_grid_data()

            # 检测新数据
            new_count = 0
            for item in page_data:
                key = item.get('name', '') + item.get('code', '')
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_data.append(item)
                    new_count += 1

            if new_count > 0:
                self.logger.info(f"滚动 {i + 1}: 发现 {new_count} 条新数据 (总计 {len(all_data)})")
                no_new_data_count = 0
            else:
                no_new_data_count += 1
                self.logger.info(f"滚动 {i + 1}: 无新数据，连续 {no_new_data_count} 次")

                # 连续5次无新数据则停止
                if no_new_data_count >= 5:
                    self.logger.info("连续多次无新数据，停止滚动")
                    break

        self.logger.info(f"滚动提取完成: 共 {len(all_data)} 条数据")
        return all_data

    async def _extract_grid_data(self) -> List[Dict[str, Any]]:
        """从1C的gridBody提取客户数据"""
        try:
            await asyncio.sleep(0.5)

            all_data = []
            grid_lines = await self.driver.page.query_selector_all(".gridLine")

            for idx, line in enumerate(grid_lines):
                try:
                    grid_boxes = await line.query_selector_all(".gridBox")
                    cell_texts = []
                    for box in grid_boxes:
                        text = await box.inner_text()
                        cell_texts.append(text.strip())

                    has_content = any(t and len(t) > 0 for t in cell_texts)
                    if not has_content:
                        continue

                    name = cell_texts[1] if len(cell_texts) > 1 else cell_texts[0]
                    name = name.strip('"\'').strip()

                    if name and len(name) > 0:
                        if name.lower() not in ['description', 'наименование', 'код']:
                            all_data.append({
                                'name': name,
                                'code': cell_texts[0] if cell_texts else '',
                                'inn': cell_texts[2] if len(cell_texts) > 2 else '',
                                'full_name': cell_texts[3] if len(cell_texts) > 3 else name,
                                'ref_key': '',
                                'synced_at': datetime.now().isoformat()
                            })

                except Exception as e:
                    continue

            return all_data

        except Exception as e:
            self.logger.error(f"提取失败: {e}")
            return []

    @property
    def page(self):
        """获取page对象"""
        return self.driver.page
