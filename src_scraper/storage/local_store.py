"""本地存储模块 - 作为Supabase的备选"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..utils.logger import get_logger

logger = get_logger("local_storage")

DATA_DIR = Path("data/exports")


class LocalStore:
    """本地数据存储管理器"""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._sync_id = None
        self._sync_start = None

    # ==================== 同步管理 ====================

    def start_sync(self, task: str, mode: str = "full") -> str:
        """开始同步"""
        self._sync_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._sync_start = datetime.now()
        logger.info(f"开始同步: {task}, 模式: {mode}, ID: {self._sync_id}")
        return self._sync_id

    def end_sync(self, sync_id: str, success: bool = True, records_synced: int = 0):
        """结束同步"""
        duration = (datetime.now() - self._sync_start).total_seconds() if self._sync_start else 0
        status = "成功" if success else "失败"
        logger.info(f"同步完成: {status}, 记录数: {records_synced}, 耗时: {duration:.1f}秒")

    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """获取同步历史"""
        return []

    def get_stats(self) -> Dict:
        """获取统计数据"""
        stats = {}
        for table in ["customers", "products", "orders"]:
            json_file = DATA_DIR / f"{table}.json"
            csv_file = DATA_DIR / f"{table}.csv"
            count = 0
            if json_file.exists():
                try:
                    data = json.loads(json_file.read_text())
                    count = len(data) if isinstance(data, list) else 0
                except:
                    pass
            stats[table] = {"count": count}
        return stats

    # ==================== 客户数据 ====================

    def upsert_customers(self, data: List[Dict]) -> Dict:
        """保存客户数据"""
        return self._save_data("customers", data)

    # ==================== 产品数据 ====================

    def upsert_products(self, data: List[Dict]) -> Dict:
        """保存产品数据"""
        return self._save_data("products", data)

    # ==================== 订单数据 ====================

    def upsert_orders(self, data: List[Dict]) -> Dict:
        """保存订单数据"""
        return self._save_data("orders", data)

    # ==================== 私有方法 ====================

    def _save_data(self, table: str, data: List[Dict]) -> Dict:
        """保存数据到本地文件"""
        if not data:
            return {"data": [], "count": 0}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存为JSON（追加模式）
        json_file = DATA_DIR / f"{table}.json"
        existing_data = []
        if json_file.exists():
            try:
                existing_data = json.loads(json_file.read_text())
                if not isinstance(existing_data, list):
                    existing_data = []
            except:
                existing_data = []

        # 合并数据（去重）
        existing_ids = {item.get("ref_key") or item.get("id") for item in existing_data if item.get("ref_key") or item.get("id")}
        new_items = [item for item in data if (item.get("ref_key") or item.get("id")) not in existing_ids]
        
        all_data = existing_data + new_items
        
        # 添加元数据
        for item in all_data:
            if "_synced_at" not in item:
                item["_synced_at"] = datetime.now().isoformat()

        json_file.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))
        logger.info(f"已保存 {len(all_data)} 条 {table} 数据到 {json_file}")

        # 保存为CSV
        csv_file = DATA_DIR / f"{table}.csv"
        if all_data:
            keys = all_data[0].keys()
            csv_file.write_text("")
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(all_data)
            logger.info(f"已保存 {len(all_data)} 条 {table} 数据到 {csv_file}")

        # 备份本次数据
        backup_file = DATA_DIR / f"{table}_{timestamp}.json"
        backup_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        return {
            "data": all_data,
            "count": len(all_data),
            "new_count": len(new_items),
            "json_file": str(json_file),
            "csv_file": str(csv_file)
        }


def get_local_store() -> LocalStore:
    """获取本地存储实例"""
    return LocalStore()
