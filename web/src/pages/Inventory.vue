<script setup lang="ts">
import { ref, onMounted } from 'vue'
import supabase from '@/api/supabase'

const inventory = ref<any[]>([])
const loading = ref(true)

onMounted(() => {
  loadInventory()
})

async function loadInventory() {
  loading.value = true
  try {
    const { data, error } = await supabase
      .from('inventory')
      .select('*, products(description)')
      .limit(100)
      .order('warehouse_name', { ascending: true })

    if (!error && data) {
      inventory.value = data
    }
  } catch (e) {
    console.error('Failed to load inventory:', e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="inventory-page">
    <div class="page-header">
      <h2>库存管理</h2>
      <button class="btn-primary" @click="loadInventory">🔄 刷新</button>
    </div>

    <div class="data-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>产品</th>
            <th>仓库</th>
            <th>数量</th>
            <th>预留</th>
            <th>可用</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="inventory.length === 0">
            <td colspan="5" class="empty">暂无数据</td>
          </tr>
          <tr v-else v-for="item in inventory" :key="item.id">
            <td>{{ item.products?.description || '-' }}</td>
            <td>{{ item.warehouse_name }}</td>
            <td>{{ item.quantity || 0 }}</td>
            <td>{{ item.reserved_quantity || 0 }}</td>
            <td>{{ (item.quantity || 0) - (item.reserved_quantity || 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.inventory-page { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 24px; font-weight: 600; }
.btn-primary { padding: 10px 20px; background: #0052D9; color: white; border: none; border-radius: 6px; cursor: pointer; }
.data-card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 14px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.data-table th { background: #f9fafb; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; }
.data-table td { font-size: 14px; color: #374151; }
.loading, .empty { text-align: center; color: #9ca3af; padding: 40px !important; }
</style>
