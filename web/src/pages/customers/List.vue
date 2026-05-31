<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCustomerStore } from '@/stores/customers'
import supabase from '@/api/supabase'

const customerStore = useCustomerStore()

const search = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

onMounted(() => {
  loadCustomers()
})

async function loadCustomers() {
  await customerStore.fetchCustomers({
    page: currentPage.value,
    pageSize: pageSize.value,
    search: search.value || undefined,
  })
}

async function handleSearch() {
  currentPage.value = 1
  await loadCustomers()
}

async function handlePageChange(page: number) {
  currentPage.value = page
  await loadCustomers()
}

function formatDate(date: string | null): string {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="customers-page">
    <div class="page-header">
      <h2>客户管理</h2>
      <div class="header-actions">
        <button class="btn-primary" @click="loadCustomers">
          🔄 刷新
        </button>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="search"
        type="text"
        placeholder="搜索客户名称或INN..."
        class="search-input"
        @keyup.enter="handleSearch"
      />
      <button class="btn-search" @click="handleSearch">搜索</button>
    </div>

    <!-- 数据表格 -->
    <div class="data-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>INN</th>
            <th>电话</th>
            <th>邮箱</th>
            <th>更新日期</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="customerStore.loading">
            <td colspan="6" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="customerStore.customers.length === 0">
            <td colspan="6" class="empty">暂无数据</td>
          </tr>
          <tr 
            v-else 
            v-for="customer in customerStore.customers" 
            :key="customer.id"
          >
            <td>{{ customer.code || '-' }}</td>
            <td>{{ customer.description }}</td>
            <td>{{ customer.inn || '-' }}</td>
            <td>{{ customer.phone_work || customer.phone_mobile || '-' }}</td>
            <td>{{ customer.email || '-' }}</td>
            <td>{{ formatDate(customer.updated_at) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 分页 -->
      <div class="pagination" v-if="customerStore.total > 0">
        <span class="pagination-info">
          共 {{ customerStore.total }} 条记录
        </span>
        <div class="pagination-controls">
          <button 
            :disabled="currentPage === 1"
            @click="handlePageChange(currentPage - 1)"
          >
            上一页
          </button>
          <span class="current-page">{{ currentPage }}</span>
          <button 
            :disabled="currentPage * pageSize >= customerStore.total"
            @click="handlePageChange(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.customers-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.btn-primary {
  padding: 10px 20px;
  background: #0052D9;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.btn-search {
  padding: 10px 24px;
  background: #6b7280;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.data-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table th {
  background: #f9fafb;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
}

.data-table td {
  font-size: 14px;
  color: #374151;
}

.data-table tr:hover {
  background: #f9fafb;
}

.loading,
.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40px !important;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
}

.pagination-info {
  font-size: 14px;
  color: #6b7280;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-controls button {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.current-page {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}
</style>
