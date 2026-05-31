"""订单数据抓取模块"""
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..scrapers.base import PaginationScraper
from ..browser.navigation import create_navigation_helper, NavigationHelper
from ..utils.logger import get_logger

logger = get_logger("orders")


class OrderScraper(PaginationScraper):
    """订单数据抓取器 - 支持1C云版本侧边栏导航"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nav: Optional[NavigationHelper] = None

    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """抓取订单数据"""
        self.logger.info("开始抓取订单数据")

        try:
            # 初始化导航辅助
            self.nav = create_navigation_helper(self.driver.page)

            # 通过侧边栏导航到订单模块
            success = await self.nav.navigate_to("orders")
            if not success:
                self.logger.error("无法导航到订单模块")
                return {"success": False, "count": 0, "data": [], "errors": ["导航失败"]}

            # 等待数据加载
            await asyncio.sleep(3)

            # 截图诊断
            await self.screenshot("orders_list.png")

            # 提取数据
            result = await self._extract_orders()

            if result.get('data') and hasattr(self.store, 'upsert_orders'):
                self.store.upsert_orders(result['data'])
                self.logger.info(f"成功抓取 {result['count']} 条订单数据")

            return result

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")
            await self.screenshot("orders_error.png")
            return {"success": False, "count": 0, "data": [], "errors": [str(e)]}

    async def _extract_orders(self) -> Dict[str, Any]:
        """从页面提取订单数据"""
        all_data = []

        # 使用与customers相同的grid提取方法
        js_data = await self._extract_grid_data()
        if js_data:
            self.logger.info(f"JS提取到 {len(js_data)} 条数据")
            all_data.extend(js_data)

        # 去重
        seen = set()
        unique_data = []
        for order in all_data:
            key = order.get('number', '') + order.get('date', '')
            if key and key not in seen:
                seen.add(key)
                unique_data.append(order)

        return {
            "success": True,
            "count": len(unique_data),
            "data": unique_data
        }

    async def _extract_grid_data(self) -> List[Dict[str, Any]]:
        """从1C的gridBody提取订单数据"""
        try:
            # 等待gridBody加载
            await asyncio.sleep(5)

            # 检查gridBody状态
            grid_check = await self.driver.page.evaluate("""() => {
                const gridBody = document.querySelector('.gridBody');
                if (!gridBody) return { error: 'No gridBody' };
                const lines = gridBody.querySelectorAll('.gridLine');
                return { lines: lines.length };
            }""")

            self.logger.info(f"Grid检查: {grid_check}")

            if grid_check.get('error'):
                return []

            # 使用Playwright方法提取数据
            all_data = []
            grid_lines = await self.driver.page.query_selector_all(".gridLine")
            self.logger.info(f"找到 {len(grid_lines)} 行")

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

                    # 解析订单数据
                    # 通常结构: 号码(Номер), 日期(Дата), 客户(Контрагент), 金额(Сумма), 状态(Статус)
                    # 订单列表可能有不同的列结构
                    number = cell_texts[0] if cell_texts else ''
                    date = cell_texts[1] if len(cell_texts) > 1 else ''
                    customer = cell_texts[2] if len(cell_texts) > 2 else ''
                    amount = cell_texts[3] if len(cell_texts) > 3 else ''
                    status = cell_texts[4] if len(cell_texts) > 4 else ''

                    # 清理文本
                    number = number.strip('"\'').strip()
                    date = date.strip('"\'').strip()
                    customer = customer.strip('"\'').strip()
                    amount = amount.strip('"\'').strip()
                    status = status.strip('"\'').strip()

                    if number and number not in ['Номер', 'Number', 'Document']:
                        all_data.append({
                            'number': number,
                            'date': date,
                            'customer': customer,
                            'amount': amount,
                            'status': status,
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
