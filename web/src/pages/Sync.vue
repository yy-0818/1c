<script setup lang="ts">
import { ref, onMounted } from 'vue'
import supabase from '@/api/supabase'

const syncLogs = ref<any[]>([])
const loading = ref(true)
const syncing = ref(false)

onMounted(() => {
  loadSyncLogs()
})

async function loadSyncLogs() {
  loading.value = true
  try {
    const { data, error } = await supabase
      .from('sync_logs')
      .select('*')
      .order('started_at', { ascending: false })
      .limit(20)

    if (!error && data) {
      syncLogs.value = data
    }
  } catch (e) {
    console.error('Failed to load sync logs:', e)
  } finally {
    loading.value = false
  }
}

async function triggerSync() {
  syncing.value = true
  // 触发爬虫同步（需要后端API）
  alert('同步功能需要后端API支持，请先运行 Python 爬虫')
  syncing.value = false
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString('zh-CN')
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'error'
    default: return 'pending'
  }
}
</script>

<template>
  <div class="sync-page">
    <div class="page-header">
      <h2>数据同步</h2>
      <button class="btn-primary" :disabled="syncing" @click="triggerSync">
        {{ syncing ? '同步中...' : '🔄 手动同步' }}
      </button>
    </div>

    <div class="info-card">
      <h3>同步说明</h3>
      <p>数据同步将从 1C Clobus 系统抓取最新数据并存储到数据库。</p>
      <p>建议每天定时执行同步任务以保持数据最新。</p>
      <p class="note">注意：同步功能需要运行 Python 爬虫脚本 <code>python main.py --mode sync --task all</code></p>
    </div>

    <div class="data-card">
      <h3>同步历史</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>类型</th>
            <th>状态</th>
            <th>记录数</th>
            <th>开始时间</th>
            <th>耗时</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="syncLogs.length === 0">
            <td colspan="5" class="empty">暂无同步记录</td>
          </tr>
          <tr v-else v-for="log in syncLogs" :key="log.id">
            <td>{{ log.sync_type }}</td>
            <td>
              <span class="status-badge" :class="getStatusClass(log.status)">
                {{ log.status }}
              </span>
            </td>
            <td>{{ log.records_processed || 0 }}</td>
            <td>{{ formatDate(log.started_at) }}</td>
            <td>{{ log.duration_seconds ? `${log.duration_seconds}秒` : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.sync-page { max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 24px; font-weight: 600; }
.btn-primary { padding: 10px 20px; background: #0052D9; color: white; border: none; border-radius: 6px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.info-card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.info-card h3 { margin: 0 0 12px; font-size: 16px; color: #1f2937; }
.info-card p { margin: 8px 0; font-size: 14px; color: #6b7280; }
.info-card .note { background: #fef3c7; padding: 12px; border-radius: 6px; font-size: 13px; }
.info-card code { background: #e5e7eb; padding: 2px 6px; border-radius: 4px; }
.data-card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
.data-card h3 { margin: 0; padding: 16px 20px; font-size: 16px; border-bottom: 1px solid #e5e7eb; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.data-table th { background: #f9fafb; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; }
.status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.status-badge.success { background: #d1fae5; color: #065f46; }
.status-badge.error { background: #fee2e2; color: #991b1b; }
.status-badge.pending { background: #fef3c7; color: #92400e; }
.loading, .empty { text-align: center; color: #9ca3af; padding: 40px !important; }
</style>
