import { ref } from 'vue'
import { defineStore } from 'pinia'
import supabase from '@/api/supabase'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const syncStatus = ref<'idle' | 'syncing' | 'success' | 'error'>('idle')
  const lastSyncTime = ref<string | null>(null)
  const stats = ref({
    customers: 0,
    products: 0,
    orders: 0,
    inventory: 0,
  })

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  async function fetchStats() {
    try {
      const tables = ['customers', 'products', 'orders', 'inventory']
      const results: Record<string, number> = {}

      for (const table of tables) {
        const { count, error } = await supabase
          .from(table)
          .select('*', { count: 'exact', head: true })
        
        if (!error && count !== null) {
          results[table] = count
        }
      }

      stats.value = {
        customers: results.customers || 0,
        products: results.products || 0,
        orders: results.orders || 0,
        inventory: results.inventory || 0,
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  async function fetchLastSyncTime() {
    try {
      const { data, error } = await supabase
        .from('sync_logs')
        .select('completed_at')
        .eq('status', 'completed')
        .order('completed_at', { ascending: false })
        .limit(1)
        .single()

      if (!error && data) {
        lastSyncTime.value = data.completed_at
      }
    } catch (e) {
      console.error('Failed to fetch last sync time:', e)
    }
  }

  return {
    sidebarCollapsed,
    syncStatus,
    lastSyncTime,
    stats,
    toggleSidebar,
    fetchStats,
    fetchLastSyncTime,
  }
})
