"""客户数据抓取模块"""
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from playwright.async_api import ElementHandle

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

            # 提取数据
            result = await self._extract_customers()

            if result.get('data'):
                if hasattr(self.store, 'upsert_customers'):
                    self.store.upsert_customers(result['data'])

                self.logger.info(f"成功抓取 {result['count']} 条客户数据")

            return result

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")
            await self.screenshot("customers_error.png")
            return {"success": False, "count": 0, "data": [], "errors": [str(e)]}

    async def _extract_customers(self) -> Dict[str, Any]:
        """从页面提取客户数据"""
        all_data = []

        # 方法: 使用JavaScript提取1C的gridBody数据
        js_data = await self._extract_grid_data()
        if js_data:
            self.logger.info(f"JS提取到 {len(js_data)} 条数据")
            all_data.extend(js_data)

        # 去重
        seen = set()
        unique_data = []
        for customer in all_data:
            key = customer.get('name', '') + customer.get('inn', '')
            if key and key not in seen:
                seen.add(key)
                unique_data.append(customer)

        return {
            "success": True,
            "count": len(unique_data),
            "data": unique_data
        }

    async def _extract_grid_data(self) -> List[Dict[str, Any]]:
        """从1C的gridBody提取客户数据"""
        try:
            # 等待gridBody加载
            await asyncio.sleep(5)

            # 首先检查gridBody状态
            grid_check = await self.driver.page.evaluate("""() => {
                const gridBody = document.querySelector('.gridBody');
                if (!gridBody) return { error: 'No gridBody' };

                const lines = gridBody.querySelectorAll('.gridLine');
                return { lines: lines.length };
            }""")

            self.logger.info(f"Grid检查: {grid_check}")

            if grid_check.get('error'):
                return []

            # 使用Playwright方法提取数据（更可靠）
            all_data = []
            grid_lines = await self.driver.page.query_selector_all(".gridLine")
            self.logger.info(f"找到 {len(grid_lines)} 行")

            for idx, line in enumerate(grid_lines):
                try:
                    # 使用Playwright inner_text方法
                    row_text = await line.inner_text()
                    
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
                    # 清理名称
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
                    self.logger.debug(f"解析行 {idx} 失败: {e}")
                    continue

            return all_data

        except Exception as e:
            self.logger.error(f"提取失败: {e}")
            return []

    async def _extract_by_selector(self) -> List[Dict[str, Any]]:
        """通过选择器提取客户数据（备用方法）"""
        all_data = []

        selectors = [
            ".gridBody .gridLine",
            "[class*='gridLine']",
        ]

        for sel in selectors:
            try:
                rows = await self.find_elements(sel)
                self.logger.info(f"选择器 {sel}: 找到 {len(rows)} 行")

                for row in rows:
                    try:
                        cells = await row.query_selector_all(".gridBox")
                        if cells:
                            cell_texts = []
                            for cell in cells:
                                text = (await cell.inner_text()).strip()
                                text = re.sub(r'\s+', ' ', text)
                                cell_texts.append(text)

                            if cell_texts and any(t for t in cell_texts):
                                name = cell_texts[0].strip('"\'')
                                if name and len(name) > 0:
                                    all_data.append({
                                        'name': name,
                                        'code': '',
                                        'inn': cell_texts[1] if len(cell_texts) > 1 else '',
                                        'full_name': cell_texts[2] if len(cell_texts) > 2 else name,
                                        'ref_key': '',
                                        'synced_at': datetime.now().isoformat()
                                    })
                    except:
                        pass

                if all_data:
                    break

            except Exception as e:
                self.logger.debug(f"选择器 {sel} 失败: {e}")

        return all_data

    async def find_element_by_text(self, text: str, exact: bool = False) -> Optional[Any]:
        """通过文本查找元素"""
        try:
            if exact:
                locator = self.driver.page.get_by_text(text, exact=True)
            else:
                locator = self.driver.page.get_by_text(text, exact=False)

            if await locator.count() > 0:
                return locator.first
        except:
            pass

        return None
