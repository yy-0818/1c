"""Supabase存储模块"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel
from supabase import create_client, Client

from ..core.config_loader import get_config
from ..utils.logger import get_logger

logger = get_logger("storage")


class SyncStatus:
    """同步状态常量"""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class SupabaseStore:
    """Supabase数据存储管理器"""

    def __init__(self, url: str = None, key: str = None):
        config = get_config()
        self.url = url or config.supabase.url
        self.key = key or config.supabase.anon_key
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """获取Supabase客户端"""
        if self._client is None:
            self._client = create_client(self.url, self.key)
        return self._client

    # ==================== 客户数据 ====================

    def upsert_customers(self, data: List[Dict]) -> Dict:
        """Upsert客户主数据"""
        if not data:
            return {"data": [], "count": 0}

        # 确保所有必要字段
        for item in data:
            if 'id' not in item and 'ref_key' not in item:
                item['id'] = str(uuid4())

        logger.info(f"Upserting {len(data)} customers")
        result = self.client.table('customers').upsert(
            data,
            on_conflict='ref_key',
            ignore_duplicates=False
        ).execute()
        return {"data": result.data, "count": len(result.data)}

    def get_customers(self,
                      include_deleted: bool = False,
                      limit: int = 1000) -> List[Dict]:
        """获取客户列表"""
        query = self.client.table('customers').select('*')

        if not include_deleted:
            query = query.eq('deletion_mark', False)

        query = query.limit(limit)
        result = query.execute()
        return result.data or []

    def get_customer_by_inn(self, inn: str) -> Optional[Dict]:
        """根据INN获取客户"""
        result = self.client.table('customers') \
            .select('*') \
            .eq('inn', inn) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    # ==================== 产品数据 ====================

    def upsert_products(self, data: List[Dict]) -> Dict:
        """Upsert产品主数据"""
        if not data:
            return {"data": [], "count": 0}

        for item in data:
            if 'id' not in item and 'ref_key' not in item:
                item['id'] = str(uuid4())

        logger.info(f"Upserting {len(data)} products")
        result = self.client.table('products').upsert(
            data,
            on_conflict='ref_key',
            ignore_duplicates=False
        ).execute()
        return {"data": result.data, "count": len(result.data)}

    def get_products(self,
                    include_deleted: bool = False,
                    limit: int = 1000) -> List[Dict]:
        """获取产品列表"""
        query = self.client.table('products').select('*')

        if not include_deleted:
            query = query.eq('deletion_mark', False)

        query = query.limit(limit)
        result = query.execute()
        return result.data or []

    # ==================== 订单数据 ====================

    def upsert_orders(self, data: List[Dict]) -> Dict:
        """Upsert订单主数据"""
        if not data:
            return {"data": [], "count": 0}

        for item in data:
            if 'id' not in item and 'ref_key' not in item:
                item['id'] = str(uuid4())

        logger.info(f"Upserting {len(data)} orders")
        result = self.client.table('orders').upsert(
            data,
            on_conflict='ref_key',
            ignore_duplicates=False
        ).execute()
        return {"data": result.data, "count": len(result.data)}

    def upsert_order_items(self, order_id: str, data: List[Dict]) -> Dict:
        """Upsert订单明细"""
        if not data:
            return {"data": [], "count": 0}

        for item in data:
            item['order_id'] = order_id
            if 'id' not in item:
                item['id'] = str(uuid4())

        # 先删除旧数据再插入
        self.client.table('order_items').delete() \
            .eq('order_id', order_id).execute()

        result = self.client.table('order_items').insert(data).execute()
        return {"data": result.data, "count": len(result.data)}

    def get_orders(self,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   status: Optional[str] = None,
                   limit: int = 1000) -> List[Dict]:
        """获取订单列表"""
        query = self.client.table('orders').select('*')

        if date_from:
            query = query.gte('order_date', date_from)
        if date_to:
            query = query.lte('order_date', date_to)
        if status:
            query = query.eq('status', status)

        query = query.limit(limit).order('order_date', desc=True)
        result = query.execute()
        return result.data or []

    # ==================== 库存数据 ====================

    def upsert_inventory(self, data: List[Dict]) -> Dict:
        """Upsert库存数据"""
        if not data:
            return {"data": [], "count": 0}

        for item in data:
            if 'id' not in item and 'ref_key' not in item:
                item['id'] = str(uuid4())

        logger.info(f"Upserting {len(data)} inventory records")
        result = self.client.table('inventory').upsert(
            data,
            on_conflict='ref_key',
            ignore_duplicates=False
        ).execute()
        return {"data": result.data, "count": len(result.data)}

    # ==================== 财务数据 ====================

    def upsert_accounting_entries(self, data: List[Dict]) -> Dict:
        """Upsert财务凭证"""
        if not data:
            return {"data": [], "count": 0}

        for item in data:
            if 'id' not in item and 'ref_key' not in item:
                item['id'] = str(uuid4())

        logger.info(f"Upserting {len(data)} accounting entries")
        result = self.client.table('accounting_entries').upsert(
            data,
            on_conflict='ref_key',
            ignore_duplicates=False
        ).execute()
        return {"data": result.data, "count": len(result.data)}

    # ==================== 报表数据 ====================

    def insert_report(self, data: Dict) -> Dict:
        """插入报表数据"""
        data['id'] = str(uuid4())
        result = self.client.table('reports').insert(data).execute()
        return {"data": result.data, "count": 1}

    # ==================== 同步日志 ====================

    def start_sync(self, sync_type: str, mode: str = 'full') -> str:
        """开始同步，返回sync_log_id"""
        data = {
            'sync_type': sync_type,
            'sync_mode': mode,
            'status': SyncStatus.STARTED,
            'started_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('sync_logs').insert(data).execute()
        return result.data[0]['id']

    def complete_sync(self,
                      sync_id: str,
                      processed: int = 0,
                      created: int = 0,
                      updated: int = 0,
                      deleted: int = 0,
                      failed: int = 0) -> Dict:
        """完成同步"""
        duration = 0
        # 计算耗时
        log = self.client.table('sync_logs').select('started_at') \
            .eq('id', sync_id).single().execute()
        if log.data:
            start = datetime.fromisoformat(log.data['started_at'].replace('Z', '+00:00'))
            duration = int((datetime.utcnow() - start.replace(tzinfo=None)).total_seconds())

        return self.client.table('sync_logs').update({
            'status': SyncStatus.COMPLETED,
            'records_processed': processed,
            'records_created': created,
            'records_updated': updated,
            'records_deleted': deleted,
            'records_failed': failed,
            'completed_at': datetime.utcnow().isoformat(),
            'duration_seconds': duration
        }).eq('id', sync_id).execute()

    def fail_sync(self, sync_id: str, error: str) -> Dict:
        """同步失败"""
        return self.client.table('sync_logs').update({
            'status': SyncStatus.FAILED,
            'error_message': error,
            'completed_at': datetime.utcnow().isoformat()
        }).eq('id', sync_id).execute()

    def get_last_sync_time(self, sync_type: str) -> Optional[datetime]:
        """获取上次成功同步的时间"""
        result = self.client.table('sync_logs') \
            .select('completed_at') \
            .eq('sync_type', sync_type) \
            .eq('status', SyncStatus.COMPLETED) \
            .order('completed_at', desc=True) \
            .limit(1) \
            .execute()
        return result.data[0]['completed_at'] if result.data else None

    def get_sync_history(self, sync_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """获取同步历史"""
        query = self.client.table('sync_logs') \
            .select('*') \
            .order('started_at', desc=True) \
            .limit(limit)

        if sync_type:
            query = query.eq('sync_type', sync_type)

        result = query.execute()
        return result.data or []

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, int]:
        """获取数据统计"""
        stats = {}

        tables = ['customers', 'products', 'orders', 'inventory', 'accounting_entries']
        for table in tables:
            try:
                result = self.client.table(table) \
                    .select('*', count='exact', head=True) \
                    .execute()
                stats[table] = result.count or 0
            except Exception as e:
                logger.warning(f"Failed to get count for {table}: {e}")
                stats[table] = 0

        return stats


# 全局实例
_store: Optional[SupabaseStore] = None


def get_store() -> SupabaseStore:
    """获取存储实例"""
    global _store
    if _store is None:
        _store = SupabaseStore()
    return _store
