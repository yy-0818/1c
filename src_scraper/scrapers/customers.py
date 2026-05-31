"""客户数据抓取模块"""
import asyncio
import re
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

            # 分页抓取所有数据
            all_data = []
            page_num = 1

            while True:
                self.logger.info(f"抓取第 {page_num} 页...")

                # 截图诊断（只截第一页）
                if page_num == 1:
                    await self.screenshot("customers_list.png")

                # 提取当前页数据
                page_data = await self._extract_grid_data()
                if page_data:
                    self.logger.info(f"第 {page_num} 页提取到 {len(page_data)} 条")
                    all_data.extend(page_data)
                else:
                    self.logger.info(f"第 {page_num} 页无数据")

                # 检查是否有下一页
                has_next = await self.nav.has_next_page()
                if not has_next:
                    self.logger.info("已到达最后一页")
                    break

                # 点击下一页
                success = await self.nav.go_to_next_page()
                if not success:
                    self.logger.info("无法跳转下一页，停止")
                    break

                # 等待数据加载
                await asyncio.sleep(2)
                page_num += 1

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
                "data": unique_data,
                "pages": page_num
            }

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")
            await self.screenshot("customers_error.png")
            return {"success": False, "count": 0, "data": [], "errors": [str(e)]}

    async def _extract_grid_data(self) -> List[Dict[str, Any]]:
        """从1C的gridBody提取客户数据"""
        try:
            # 等待gridBody加载
            await asyncio.sleep(1)

            all_data = []
            grid_lines = await self.driver.page.query_selector_all(".gridLine")

            for idx, line in enumerate(grid_lines):
                try:
                    # 获取所有gridBox
                    grid_boxes = await line.query_selector_all(".gridBox")
                    cell_texts = []
                    for box in grid_boxes:
                        text = await box.inner_text()
                        cell_texts.append(text.strip())

                    # 检查是否有内容
                    has_content = any(t and len(t) > 0 for t in cell_texts)

                    if not has_content:
                        continue

                    # 第一列通常是名称
                    name = cell_texts[1] if len(cell_texts) > 1 else cell_texts[0]
                    name = name.strip('"\'').strip()

                    if name and len(name) > 0:
                        # 排除表头行
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
