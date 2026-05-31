"""订单数据抓取模块"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from playwright.async_api import ElementHandle

from ..scrapers.base import PaginationScraper
from ..parsers.html_parser import DataCleaner, clean_and_validate
from ..utils.logger import get_logger

logger = get_logger("orders")


class OrderScraper(PaginationScraper):
    """订单数据抓取器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleaner = DataCleaner()
        self.list_url = self.selectors.get('orders', {}).get('list_url', '')

    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        抓取订单数据

        Args:
            date_from: 开始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            status: 订单状态筛选
            max_pages: 最大页数

        Returns:
            Dict包含 success, count, data, errors
        """
        self.logger.info("开始抓取订单数据")

        if not self.list_url:
            self.logger.warning("未配置订单列表URL")
            return {"success": False, "count": 0, "data": [], "errors": ["未配置URL"]}

        # 构建完整URL
        base_url = self.config.clobus.url
        full_url = f"{base_url}{self.list_url}" if not self.list_url.startswith('http') else self.list_url

        self.logger.info(f"抓取URL: {full_url}")

        # 应用日期筛选
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')

        if date_from or date_to:
            await self._apply_date_filter(date_from, date_to)

        result = await self.scrape_with_pagination(
            url=full_url,
            rows_selector="table.dataGrid tbody tr, [class*='row']",
            parse_row_func=self._parse_order_row,
            max_pages=kwargs.get('max_pages', 100)
        )

        if result['success'] and result['data']:
            cleaned_data = []
            for item in result['data']:
                validated = clean_and_validate(item, self._get_schema())
                if validated.get('ref_key'):
                    cleaned_data.append(validated)

            result['data'] = cleaned_data
            result['count'] = len(cleaned_data)

            if self.store and kwargs.get('save', True):
                await self._save_to_supabase(cleaned_data)

        return result

    async def _apply_date_filter(self, date_from: str = None, date_to: str = None):
        """应用日期筛选"""
        try:
            page = self.driver.page

            # 查找日期输入框
            date_selectors = [
                "[id*='Period']",
                "[name*='Period']",
                "[id*='dateFrom']",
                "[id*='dateTo']",
                "input[placeholder*='от']",
                "input[placeholder*='до']"
            ]

            if date_from:
                for sel in date_selectors:
                    element = await page.query_selector(sel)
                    if element:
                        await element.fill(date_from)
                        break

            if date_to:
                for sel in date_selectors:
                    element = await page.query_selector(sel)
                    if element:
                        await element.fill(date_to)
                        break

            # 点击刷新/应用按钮
            apply_buttons = [
                "button[title*='Обновить']",
                "button[title*='Refresh']",
                "button:has-text('Обновить')"
            ]
            for sel in apply_buttons:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    break

            self.logger.info(f"已应用日期筛选: {date_from} - {date_to}")

        except Exception as e:
            self.logger.warning(f"应用日期筛选失败: {e}")

    async def _parse_order_row(self, row: ElementHandle) -> Dict[str, Any]:
        """解析订单行"""
        data = {}

        try:
            cells = await row.query_selector_all('td')
            if not cells:
                return data

            for i, cell in enumerate(cells):
                text = await cell.inner_text()
                text = self.cleaner.clean_text(text)

                link = await cell.query_selector('a')
                if link:
                    href = await link.get_attribute('href') or ""
                    import re
                    ref_match = re.search(r'ref=(.*?)(&|$)', href)
                    if ref_match:
                        data['ref_key'] = ref_match.group(1)

                # 根据列位置解析
                if i == 0:
                    data['order_number'] = text
                    if not data.get('ref_key'):
                        data['ref_key'] = str(uuid4())
                elif i == 1:
                    data['order_date'] = self.cleaner.parse_date(text)
                elif i == 2:
                    data['customer_name'] = text
                elif i == 3:
                    data['total_amount'] = self.cleaner.parse_number(text)
                elif i == 4:
                    data['status'] = text
                elif i == 5:
                    data['posted'] = 'Проведен' in text or 'Posted' in text

            data['document_type'] = 'sales_order'
            data['last_synced_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            self.logger.debug(f"解析行失败: {e}")

        return data

    def _get_schema(self) -> Dict[str, str]:
        """获取数据验证schema"""
        return {
            'ref_key': 'text',
            'order_number': 'text',
            'order_date': 'date',
            'customer_name': 'text',
            'customer_inn': 'inn',
            'total_amount': 'number',
            'status': 'text',
            'currency': 'text',
            'posted': 'bool',
            'document_type': 'text'
        }

    async def _save_to_supabase(self, orders: List[Dict]) -> Dict[str, Any]:
        """保存到Supabase"""
        if not orders:
            return {"count": 0}

        try:
            result = self.store.upsert_orders(orders)
            self.logger.info(f"已保存 {len(orders)} 个订单到Supabase")
            return result
        except Exception as e:
            self.logger.error(f"保存订单失败: {e}")
            return {"error": str(e)}

    async def scrape_order_items(self, order_ref_key: str) -> Dict[str, Any]:
        """
        抓取订单明细

        Args:
            order_ref_key: 订单Ref_Key

        Returns:
            订单明细列表
        """
        self.logger.info(f"抓取订单明细: {order_ref_key}")

        detail_url = f"{self.config.clobus.url}/e1cib/app/Document.ЗаказКлиента.Form?ref={order_ref_key}"

        try:
            await self.navigate_to(detail_url)
            await self.wait_for_load()

            items = await self._parse_order_items()

            # 保存到Supabase
            if items and self.store:
                # 获取order_id
                orders = self.store.get_orders()
                order = next((o for o in orders if o.get('ref_key') == order_ref_key), None)
                if order:
                    self.store.upsert_order_items(order['id'], items)

            return {
                "success": True,
                "count": len(items),
                "data": items
            }

        except Exception as e:
            self.logger.error(f"抓取订单明细失败: {e}")
            return {"success": False, "error": str(e)}

    async def _parse_order_items(self) -> List[Dict[str, Any]]:
        """解析订单明细表格"""
        items = []

        try:
            page = self.driver.page

            # 查找明细表格
            table = await page.query_selector("table.object扒, [class*='itemList'], table")
            if not table:
                return items

            rows = await table.query_selector_all('tbody tr, tr')
            line_number = 0

            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) < 4:
                    continue

                line_number += 1
                item = {'line_number': line_number}

                for i, cell in enumerate(cells):
                    text = await cell.inner_text()
                    text = self.cleaner.clean_text(text)

                    if i == 0:
                        item['product_name'] = text
                    elif i == 1:
                        item['unit_name'] = text
                    elif i == 2:
                        item['quantity'] = self.cleaner.parse_number(text)
                    elif i == 3:
                        item['unit_price'] = self.cleaner.parse_number(text)
                    elif i == 4:
                        item['amount'] = self.cleaner.parse_number(text)

                if item.get('product_name'):
                    items.append(item)

        except Exception as e:
            self.logger.debug(f"解析订单明细失败: {e}")

        return items
