<script setup lang="ts">
import { ref, onMounted } from 'vue'
import supabase from '@/api/supabase'

const stats = ref<any>({
  customers: 0,
  products: 0,
  orders: 0,
  inventory: 0,
  accounting: 0,
})
const loading = ref(true)

onMounted(() => {
  loadStats()
})

async function loadStats() {
  loading.value = true
  try {
    const tables = ['customers', 'products', 'orders', 'inventory', 'accounting_entries']
    
    for (const table of tables) {
      const { count, error } = await supabase
        .from(table)
        .select('*', { count: 'exact', head: true })
      if (!error && count !== null) {
        stats.value[table] = count
      }
    }
  } catch (e) {
    console.error('Failed to load stats:', e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="overview-page">
    <h2>数据总览</h2>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.customers }}</div>
          <div class="stat-label">客户</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📦</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.products }}</div>
          <div class="stat-label">产品</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📝</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.orders }}</div>
          <div class="stat-label">订单</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🏭</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.inventory }}</div>
          <div class="stat-label">库存记录</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.accounting }}</div>
          <div class="stat-label">财务凭证</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview-page { max-width: 1200px; margin: 0 auto; }
.overview-page h2 { font-size: 24px; margin-bottom: 24px; }
.loading { text-align: center; padding: 40px; color: #9ca3af; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
.stat-card { background: white; border-radius: 12px; padding: 24px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.stat-icon { font-size: 36px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1f2937; }
.stat-label { font-size: 14px; color: #6b7280; margin-top: 4px; }
</style>
