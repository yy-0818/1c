<script setup lang="ts">
import { ref, onMounted } from 'vue'
import supabase from '@/api/supabase'

const orders = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  loadOrders()
})

async function loadOrders() {
  loading.value = true
  try {
    let query = supabase
      .from('orders')
      .select('*, customers(description)', { count: 'exact' })
      .eq('deletion_mark', false)

    if (search.value) {
      query = query.or(`order_number.ilike.%${search.value}%,customer_name.ilike.%${search.value}%`)
    }

    const from = (currentPage.value - 1) * pageSize.value
    query = query.range(from, from + pageSize.value - 1).order('order_date', { ascending: false })

    const { data, error, count } = await query

    if (!error && data) {
      orders.value = data
      total.value = count || 0
    }
  } catch (e) {
    console.error('Failed to load orders:', e)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  loadOrders()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadOrders()
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
  <div class="orders-page">
    <div class="page-header">
      <h2>订单管理</h2>
      <button class="btn-primary" @click="loadOrders">🔄 刷新</button>
    </div>

    <div class="search-bar">
      <input
        v-model="search"
        type="text"
        placeholder="搜索订单号或客户..."
        class="search-input"
        @keyup.enter="handleSearch"
      />
      <button class="btn-search" @click="handleSearch">搜索</button>
    </div>

    <div class="data-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>订单号</th>
            <th>日期</th>
            <th>客户</th>
            <th>金额</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="orders.length === 0">
            <td colspan="6" class="empty">暂无数据</td>
          </tr>
          <tr v-else v-for="order in orders" :key="order.id">
            <td>{{ order.order_number || '-' }}</td>
            <td>{{ formatDate(order.order_date) }}</td>
            <td>{{ order.customers?.description || order.customer_name || '-' }}</td>
            <td>{{ formatCurrency(order.total_amount) }}</td>
            <td>
              <span class="status-badge" :class="order.status">
                {{ order.status || '未知' }}
              </span>
            </td>
            <td>
              <button class="btn-view" @click="$router.push(`/orders/${order.id}`)">查看</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > 0">
        <span class="pagination-info">共 {{ total }} 条记录</span>
        <div class="pagination-controls">
          <button :disabled="currentPage === 1" @click="handlePageChange(currentPage - 1)">上一页</button>
          <span class="current-page">{{ currentPage }}</span>
          <button :disabled="currentPage * pageSize >= total" @click="handlePageChange(currentPage + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.orders-page { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 24px; font-weight: 600; }
.btn-primary { padding: 10px 20px; background: #0052D9; color: white; border: none; border-radius: 6px; cursor: pointer; }
.search-bar { display: flex; gap: 12px; margin-bottom: 20px; }
.search-input { flex: 1; padding: 10px 16px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 14px; }
.btn-search { padding: 10px 24px; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; }
.data-card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 14px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.data-table th { background: #f9fafb; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; }
.data-table td { font-size: 14px; color: #374151; }
.status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; background: #e5e7eb; }
.status-badge.Completed { background: #d1fae5; color: #065f46; }
.status-badge.Cancelled { background: #fee2e2; color: #991b1b; }
.btn-view { padding: 4px 12px; border: 1px solid #e5e7eb; background: white; border-radius: 4px; cursor: pointer; font-size: 12px; }
.loading, .empty { text-align: center; color: #9ca3af; padding: 40px !important; }
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-top: 1px solid #e5e7eb; }
.pagination-info { font-size: 14px; color: #6b7280; }
.pagination-controls { display: flex; align-items: center; gap: 12px; }
.pagination-controls button { padding: 8px 16px; border: 1px solid #e5e7eb; background: white; border-radius: 6px; cursor: pointer; }
.pagination-controls button:disabled { opacity: 0.5; cursor: not-allowed; }
.current-page { font-size: 14px; color: #374151; font-weight: 500; }
</style>
