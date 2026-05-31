<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import supabase from '@/api/supabase'

const appStore = useAppStore()

interface Stats {
  customers: number
  products: number
  orders: number
  inventory: number
}

const stats = ref<Stats>({
  customers: 0,
  products: 0,
  orders: 0,
  inventory: 0,
})

const recentOrders = ref<any[]>([])

onMounted(async () => {
  await Promise.all([
    fetchStats(),
    fetchRecentOrders(),
  ])
})

async function fetchStats() {
  try {
    const tables = ['customers', 'products', 'orders', 'inventory']
    
    for (const table of tables) {
      const { count, error } = await supabase
        .from(table)
        .select('*', { count: 'exact', head: true })
      
      if (!error && count !== null) {
        stats.value[table as keyof Stats] = count
      }
    }
    
    appStore.stats = stats.value
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  }
}

async function fetchRecentOrders() {
  try {
    const { data, error } = await supabase
      .from('orders')
      .select('*, customers(description)')
      .order('order_date', { ascending: false })
      .limit(5)

    if (!error && data) {
      recentOrders.value = data
    }
  } catch (e) {
    console.error('Failed to fetch recent orders:', e)
  }
}

function formatCurrency(amount: number | null): string {
  if (amount === null) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'UZS',
    minimumFractionDigits: 0,
  }).format(amount)
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="dashboard">
    <!-- KPI 卡片 -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">👥</div>
        <div class="kpi-content">
          <div class="kpi-value">{{ stats.customers }}</div>
          <div class="kpi-label">客户总数</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon">📦</div>
        <div class="kpi-content">
          <div class="kpi-value">{{ stats.products }}</div>
          <div class="kpi-label">产品总数</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon">📝</div>
        <div class="kpi-content">
          <div class="kpi-value">{{ stats.orders }}</div>
          <div class="kpi-label">订单总数</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon">🏭</div>
        <div class="kpi-content">
          <div class="kpi-value">{{ stats.inventory }}</div>
          <div class="kpi-label">库存记录</div>
        </div>
      </div>
    </div>

    <!-- 图表和最近订单 -->
    <div class="content-grid">
      <div class="card">
        <div class="card-header">
          <h3>最近订单</h3>
          <router-link to="/orders" class="view-all">查看全部 →</router-link>
        </div>
        <div class="card-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>订单号</th>
                <th>日期</th>
                <th>客户</th>
                <th>金额</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in recentOrders" :key="order.id">
                <td>{{ order.order_number || '-' }}</td>
                <td>{{ formatDate(order.order_date) }}</td>
                <td>{{ order.customers?.description || order.customer_name || '-' }}</td>
                <td>{{ formatCurrency(order.total_amount) }}</td>
                <td>
                  <span class="status-badge" :class="order.status">
                    {{ order.status || '未知' }}
                  </span>
                </td>
              </tr>
              <tr v-if="recentOrders.length === 0">
                <td colspan="5" class="empty-text">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>快速操作</h3>
        </div>
        <div class="card-body">
          <div class="quick-actions">
            <router-link to="/sync" class="action-btn">
              🔄 同步数据
            </router-link>
            <router-link to="/customers" class="action-btn">
              👥 客户管理
            </router-link>
            <router-link to="/orders" class="action-btn">
              📝 订单管理
            </router-link>
            <router-link to="/reports" class="action-btn">
              📈 财务报表
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- 系统信息 -->
    <div class="system-info">
      <div class="info-item">
        <span class="info-label">数据库</span>
        <span class="info-value">Supabase</span>
      </div>
      <div class="info-item">
        <span class="info-label">最后同步</span>
        <span class="info-value">{{ appStore.lastSyncTime ? formatDate(appStore.lastSyncTime) : '从未同步' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.kpi-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.kpi-icon {
  font-size: 36px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}

.kpi-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.view-all {
  font-size: 14px;
  color: #0052D9;
  text-decoration: none;
}

.view-all:hover {
  text-decoration: underline;
}

.card-body {
  padding: 16px 20px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 8px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table th {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
}

.data-table td {
  font-size: 14px;
  color: #374151;
}

.empty-text {
  text-align: center;
  color: #9ca3af;
  padding: 24px !important;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #e5e7eb;
  color: #374151;
}

.status-badge.Completed {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.Cancelled {
  background: #fee2e2;
  color: #991b1b;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.action-btn {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  text-align: center;
  text-decoration: none;
  color: #374151;
  font-size: 14px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #eff6ff;
  color: #0052D9;
}

.system-info {
  background: white;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  gap: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-item {
  display: flex;
  gap: 8px;
}

.info-label {
  color: #6b7280;
  font-size: 14px;
}

.info-value {
  color: #374151;
  font-size: 14px;
  font-weight: 500;
}
</style>
