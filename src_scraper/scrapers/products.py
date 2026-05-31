"""产品数据抓取模块"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from playwright.async_api import ElementHandle

from ..scrapers.base import PaginationScraper
from ..parsers.html_parser import DataCleaner, clean_and_validate
from ..utils.logger import get_logger

logger = get_logger("products")


class ProductScraper(PaginationScraper):
    """产品数据抓取器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleaner = DataCleaner()
        self.list_url = self.selectors.get('products', {}).get('list_url', '')

    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        抓取产品数据

        Args:
            incremental: 是否增量抓取
            max_pages: 最大页数

        Returns:
            Dict包含 success, count, data, errors
        """
        self.logger.info("开始抓取产品数据")

        if not self.list_url:
            self.logger.warning("未配置产品列表URL")
            return {"success": False, "count": 0, "data": [], "errors": ["未配置URL"]}

        # 构建完整URL
        base_url = self.config.clobus.url
        if not self.list_url.startswith('http'):
            full_url = f"{base_url}{self.list_url}" if self.list_url.startswith('/') else f"{base_url}/{self.list_url}"
        else:
            full_url = self.list_url

        self.logger.info(f"抓取URL: {full_url}")

        result = await self.scrape_with_pagination(
            url=full_url,
            rows_selector="table.dataGrid tbody tr, [class*='row']",
            parse_row_func=self._parse_product_row,
            max_pages=kwargs.get('max_pages', 100)
        )

        if result['success'] and result['data']:
            cleaned_data = []
            for item in result['data']:
                validated = clean_and_validate(item, self._get_schema())
                if validated.get('description'):
                    cleaned_data.append(validated)

            result['data'] = cleaned_data
            result['count'] = len(cleaned_data)

            if self.store and kwargs.get('save', True):
                await self._save_to_supabase(cleaned_data)

        return result

    async def _parse_product_row(self, row: ElementHandle) -> Dict[str, Any]:
        """解析产品行"""
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

                if i == 0:
                    data['article'] = text
                    if not data.get('ref_key'):
                        data['ref_key'] = str(uuid4())
                elif i == 1:
                    data['description'] = text
                elif i == 2:
                    data['unit_name'] = text
                elif i == 3:
                    data['product_type'] = text

            data['last_synced_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            self.logger.debug(f"解析行失败: {e}")

        return data

    def _get_schema(self) -> Dict[str, str]:
        """获取数据验证schema"""
        return {
            'ref_key': 'text',
            'article': 'text',
            'description': 'text',
            'description_full': 'text',
            'unit_name': 'text',
            'product_type': 'text',
            'parent_key': 'text',
            'deletion_mark': 'bool'
        }

    async def _save_to_supabase(self, products: List[Dict]) -> Dict[str, Any]:
        """保存到Supabase"""
        if not products:
            return {"count": 0}

        try:
            result = self.store.upsert_products(products)
            self.logger.info(f"已保存 {len(products)} 个产品到Supabase")
            return result
        except Exception as e:
            self.logger.error(f"保存产品失败: {e}")
            return {"error": str(e)}
