"""HTML解析工具模块"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from ..utils.logger import get_logger

_logger = get_logger("parser")


class TableParser:
    """HTML表格解析器"""

    @staticmethod
    def parse_table(html_or_element) -> List[Dict[str, Any]]:
        """
        解析HTML表格为字典列表

        Args:
            html_or_element: HTML字符串或BeautifulSoup元素

        Returns:
            字典列表，每行一个字典
        """
        if isinstance(html_or_element, str):
            soup = BeautifulSoup(html_or_element, 'lxml')
        else:
            soup = html_or_element

        rows = []
        table = soup.find('table') or soup

        # 获取表头
        headers = []
        header_row = table.find('thead')
        if header_row:
            header_row = header_row.find('tr')
        else:
            header_row = table.find('tr')

        if header_row:
            for th in header_row.find_all(['th', 'td']):
                header = th.get_text(strip=True)
                headers.append(header)

        # 解析数据行
        tbody = table.find('tbody')
        data_rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]

        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = {}
                for i, cell in enumerate(cells):
                    header = headers[i] if i < len(headers) else f"col_{i}"
                    row_data[header] = cell.get_text(strip=True)
                    row_data[f"{header}_raw"] = str(cell)
                rows.append(row_data)

        return rows

    @staticmethod
    def extract_row_data(row, columns: List[str]) -> Dict[str, Any]:
        """从行中提取指定列数据"""
        cells = row.find_all(['td', 'th'])
        data = {}

        for i, col in enumerate(columns):
            if i < len(cells):
                data[col] = cells[i].get_text(strip=True)
            else:
                data[col] = None

        return data


class DataCleaner:
    """数据清洗工具"""

    @staticmethod
    def clean_text(text: str) -> str:
        """清洗文本"""
        if not text:
            return ""

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def parse_number(text: str) -> Optional[float]:
        """解析数字"""
        if not text:
            return None

        # 移除非数字字符（保留小数点和负号）
        cleaned = re.sub(r'[^\d.\-,]', '', text)
        if not cleaned:
            return None

        # 处理千分位逗号
        cleaned = cleaned.replace(',', '').replace(' ', '')

        # 处理俄语小数点
        if ',' in cleaned and '.' not in cleaned:
            cleaned = cleaned.replace(',', '.')
        else:
            # 同时有逗号和句号，取最后一个作为小数点
            if ',' in cleaned and '.' in cleaned:
                last_comma = cleaned.rfind(',')
                last_dot = cleaned.rfind('.')
                if last_comma > last_dot:
                    cleaned = cleaned.replace(',', '')
                else:
                    cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def parse_date(text: str) -> Optional[str]:
        """解析日期"""
        if not text:
            return None

        # 俄语月份映射
        months_ru = {
            'января': '01', 'февраля': '02', 'марта': '03',
            'апреля': '04', 'мая': '05', 'июня': '06',
            'июля': '07', 'августа': '08', 'сентября': '09',
            'октября': '10', 'ноября': '11', 'декабря': '12'
        }

        text_lower = text.lower().strip()

        # DD.MM.YYYY 或 DD-MM-YYYY
        match = re.search(r'(\d{1,2})[.\-](\d{1,2})[.\-](\d{2,4})', text)
        if match:
            day, month, year = match.groups()
            if len(year) == 2:
                year = '20' + year if int(year) < 100 else year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # DD месяц YYYY (俄语)
        for month_ru, month_num in months_ru.items():
            if month_ru in text_lower:
                match = re.search(r'(\d{1,2})\s+' + month_ru + r'\s+(\d{2,4})', text_lower)
                if match:
                    day, year = match.groups()
                    if len(year) == 2:
                        year = '20' + year
                    return f"{year}-{month_num}-{day.zfill(2)}"

        # YYYY-MM-DD (ISO)
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
        if match:
            return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

        return None

    @staticmethod
    def parse_phone(text: str) -> Optional[str]:
        """解析电话号码"""
        if not text:
            return None

        # 移除所有非数字字符
        digits = re.sub(r'\D', '', text)
        if len(digits) < 7:
            return None

        return digits

    @staticmethod
    def parse_inn(text: str) -> Optional[str]:
        """解析INN（税号）"""
        if not text:
            return None

        # INN通常是10或12位数字
        digits = re.sub(r'\D', '', text)
        if len(digits) in [10, 12, 14]:
            return digits

        return None

    @staticmethod
    def clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗字典数据"""
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = DataCleaner.clean_text(value)
            else:
                cleaned[key] = value
        return cleaned


class JSONParser:
    """JSON数据解析器"""

    @staticmethod
    def extract_from_script(html: str, key_pattern: str) -> Optional[str]:
        """从script标签中提取JSON数据"""
        match = re.search(rf'{key_pattern}\s*[=:]\s*({{.*?}})\s*;', html, re.DOTALL)
        if match:
            import json
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def parse_grid_data(html: str) -> List[Dict[str, Any]]:
        """解析1C数据网格的JSON数据"""
        # 1C通常将数据存储在特定格式中
        data = []

        # 尝试查找 __data 变量
        match = re.search(r'var\s+__data\s*=\s*(\[[\s\S]*?\])\s*;', html)
        if match:
            import json
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return data


def parse_html_table(html: str) -> List[Dict[str, Any]]:
    """解析HTML表格的便捷函数"""
    return TableParser.parse_table(html)


def clean_and_validate(data: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
    """
    根据schema清洗和验证数据

    Args:
        data: 原始数据字典
        schema: 字段类型映射 {"field_name": "type"}
                 type: text, number, date, phone, inn, bool

    Returns:
        清洗后的数据字典
    """
    result = {}
    cleaner = DataCleaner()

    for field, field_type in schema.items():
        value = data.get(field)

        if value is None:
            result[field] = None
            continue

        if field_type == 'text':
            result[field] = cleaner.clean_text(value)
        elif field_type == 'number':
            result[field] = cleaner.parse_number(value)
        elif field_type == 'date':
            result[field] = cleaner.parse_date(value)
        elif field_type == 'phone':
            result[field] = cleaner.parse_phone(value)
        elif field_type == 'inn':
            result[field] = cleaner.parse_inn(value)
        elif field_type == 'bool':
            result[field] = str(value).lower() in ('true', '1', 'да', 'yes')
        else:
            result[field] = value

    return result
