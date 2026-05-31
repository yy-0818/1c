<script setup lang="ts">
const settings = ref({
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL || '',
  supabaseKey: import.meta.env.VITE_SUPABASE_ANON_KEY ? '••••••••' : '',
})

function saveSettings() {
  alert('请在 .env 文件中修改 Supabase 配置')
}
</script>

<template>
  <div class="settings-page">
    <h2>系统设置</h2>

    <div class="settings-card">
      <h3>数据库连接</h3>
      <div class="form-group">
        <label>Supabase URL</label>
        <input type="text" v-model="settings.supabaseUrl" disabled class="input" />
      </div>
      <div class="form-group">
        <label>Supabase Key</label>
        <input type="password" v-model="settings.supabaseKey" disabled class="input" />
      </div>
      <p class="note">数据库配置通过环境变量设置，请修改 <code>.env</code> 文件</p>
    </div>

    <div class="settings-card">
      <h3>关于</h3>
      <p>1C 数据管理系统 v1.0.0</p>
      <p>用于从 1C Clobus 系统抓取和展示业务数据</p>
    </div>
  </div>
</template>

<style scoped>
.settings-page { max-width: 800px; margin: 0 auto; }
.settings-page h2 { font-size: 24px; margin-bottom: 24px; }
.settings-card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.settings-card h3 { margin: 0 0 16px; font-size: 16px; color: #1f2937; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 14px; color: #6b7280; margin-bottom: 6px; }
.input { width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 14px; background: #f9fafb; }
.note { font-size: 13px; color: #6b7280; background: #f9fafb; padding: 12px; border-radius: 6px; }
.note code { background: #e5e7eb; padding: 2px 6px; border-radius: 4px; }
.settings-card p { margin: 8px 0; font-size: 14px; color: #6b7280; }
</style>
