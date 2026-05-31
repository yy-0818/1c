"""客户数据抓取模块"""
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from playwright.async_api import ElementHandle

from ..scrapers.base import PaginationScraper
from ..parsers.html_parser import DataCleaner, clean_and_validate
from ..utils.logger import get_logger

logger = get_logger("customers")


class CustomerScraper(PaginationScraper):
    """客户数据抓取器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleaner = DataCleaner()
        self.list_url = self.selectors.get('customers', {}).get('list_url', '')

    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        抓取客户数据

        Args:
            incremental: 是否增量抓取（只抓取新增/修改的）
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            Dict包含 success, count, data, errors
        """
        self.logger.info("开始抓取客户数据")

        # 如果没有指定URL，使用默认URL
        if not self.list_url:
            self.logger.warning("未配置客户列表URL，尝试从主页面导航")
            return {"success": False, "count": 0, "data": [], "errors": ["未配置URL"]}

        # 构建完整URL
        base_url = self.config.clobus.url
        if not self.list_url.startswith('http'):
            full_url = f"{base_url}{self.list_url}" if self.list_url.startswith('/') else f"{base_url}/{self.list_url}"
        else:
            full_url = self.list_url

        self.logger.info(f"抓取URL: {full_url}")

        # 分页抓取
        result = await self.scrape_with_pagination(
            url=full_url,
            rows_selector="table.dataGrid tbody tr, [class*='row']",
            parse_row_func=self._parse_customer_row,
            max_pages=kwargs.get('max_pages', 100)
        )

        if result['success'] and result['data']:
            # 清洗数据
            cleaned_data = []
            for item in result['data']:
                validated = clean_and_validate(item, self._get_schema())
                if validated.get('description'):  # 必须有名称
                    cleaned_data.append(validated)

            result['data'] = cleaned_data
            result['count'] = len(cleaned_data)

            # 存储到Supabase
            if self.store and kwargs.get('save', True):
                await self._save_to_supabase(cleaned_data)

        return result

    async def _parse_customer_row(self, row: ElementHandle) -> Dict[str, Any]:
        """解析客户行"""
        data = {}

        try:
            # 获取所有单元格
            cells = await row.query_selector_all('td')
            if not cells:
                return data

            # 根据列位置获取数据（需要根据实际结构调整）
            # 通常1C列表的列顺序是: 代码, 名称, INN, 其他信息

            for i, cell in enumerate(cells):
                text = await cell.inner_text()
                text = self.cleaner.clean_text(text)

                # 尝试提取链接（通常是第一列）
                link = await cell.query_selector('a')
                if link:
                    href = await link.get_attribute('href') or ""
                    # 提取ref_key
                    ref_match = re.search(r'ref=(.*?)(&|$)', href)
                    if ref_match:
                        data['ref_key'] = ref_match.group(1)

                # 根据位置赋值
                if i == 0:
                    data['description'] = text
                    if not data.get('ref_key'):
                        data['ref_key'] = str(uuid4())
                elif i == 1:
                    data['code'] = text
                elif i == 2:
                    data['inn'] = self.cleaner.parse_inn(text)
                elif i == 3:
                    data['kpp'] = text
                elif i == 4:
                    data['phone_work'] = self.cleaner.parse_phone(text)
                elif i == 5:
                    data['email'] = text

            # 提取更多信息
            data['last_synced_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            self.logger.debug(f"解析行失败: {e}")

        return data

    def _get_schema(self) -> Dict[str, str]:
        """获取数据验证schema"""
        return {
            'ref_key': 'text',
            'code': 'text',
            'description': 'text',
            'inn': 'inn',
            'kpp': 'text',
            'phone_work': 'phone',
            'email': 'text',
            'deletion_mark': 'bool'
        }

    async def _save_to_supabase(self, customers: List[Dict]) -> Dict[str, Any]:
        """保存到Supabase"""
        if not customers:
            return {"count": 0}

        try:
            result = self.store.upsert_customers(customers)
            self.logger.info(f"已保存 {len(customers)} 个客户到Supabase")
            return result
        except Exception as e:
            self.logger.error(f"保存客户失败: {e}")
            return {"error": str(e)}

    async def scrape_single(self, ref_key: str) -> Dict[str, Any]:
        """
        抓取单个客户的详细信息

        Args:
            ref_key: 客户Ref_Key

        Returns:
            客户详细数据
        """
        self.logger.info(f"抓取客户详情: {ref_key}")

        # 导航到客户详情页
        detail_url = f"{self.config.clobus.url}/e1cib/app/Catalog.Партнеры.Form?ref={ref_key}"

        try:
            await self.navigate_to(detail_url)
            await self.wait_for_load()

            # 解析表单数据
            data = await self._parse_customer_form()

            return {
                "success": True,
                "data": data
            }
        except Exception as e:
            self.logger.error(f"抓取客户详情失败: {e}")
            return {"success": False, "error": str(e)}

    async def _parse_customer_form(self) -> Dict[str, Any]:
        """解析客户表单"""
        data = {}

        try:
            page = self.driver.page

            # 常见字段
            fields = {
                'description': ['[name="Description"]', '[id*="Description"]', '[data-field="Description"]'],
                'inn': ['[name="ИНН"]', '[id*="ИНН"]', '[data-field="ИНН"]'],
                'kpp': ['[name="КПП"]', '[id*="КПП"]'],
                'phone': ['[name="Телефон"]', '[id*="Телефон"]'],
                'email': ['[name="Email"]', '[id*="Email"]'],
                'address_legal': ['[name="ЮрАдрес"]', '[id*="ЮрАдрес"]'],
            }

            for field, selectors in fields.items():
                for sel in selectors:
                    element = await page.query_selector(sel)
                    if element:
                        value = await element.input_value() or await element.inner_text()
                        if value:
                            data[field] = self.cleaner.clean_text(value)
                            break

        except Exception as e:
            self.logger.debug(f"解析表单失败: {e}")

        return data

    async def export_to_excel(self, output_path: str = "data/customers.xlsx") -> str:
        """导出客户到Excel"""
        import pandas as pd

        customers = self.store.get_customers(include_deleted=False)

        if customers:
            df = pd.DataFrame(customers)
            df.to_excel(output_path, index=False)
            self.logger.info(f"已导出到 {output_path}")

        return output_path
