<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const menuItems = [
  { path: '/', icon: 'dashboard', label: '仪表盘' },
  { path: '/overview', icon: 'overview', label: '数据总览' },
  { path: '/customers', icon: 'users', label: '客户管理' },
  { path: '/products', icon: 'package', label: '产品管理' },
  { path: '/orders', icon: 'file-text', label: '订单管理' },
  { path: '/inventory', icon: 'box', label: '库存管理' },
  { path: '/reports', icon: 'bar-chart', label: '报表' },
  { path: '/sync', icon: 'refresh-cw', label: '数据同步' },
  { path: '/settings', icon: 'settings', label: '设置' },
]

const icons: Record<string, string> = {
  dashboard: '📊', overview: '📋', users: '👥', package: '📦',
  'file-text': '📝', box: '🏭', 'bar-chart': '📈', 'refresh-cw': '🔄', settings: '⚙️',
}

const titles: Record<string, string> = {
  '/': '仪表盘', '/overview': '数据总览', '/customers': '客户管理',
  '/products': '产品管理', '/orders': '订单管理', '/inventory': '库存管理',
  '/reports': '报表', '/sync': '数据同步', '/settings': '设置',
}

function getPageTitle(path: string) {
  return titles[path] || '1C数据管理'
}

function formatTime(time: string) {
  return new Date(time).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">📊</span>
          <span v-if="!appStore.sidebarCollapsed" class="logo-text">1C数据管理</span>
        </div>
        <button class="collapse-btn" @click="appStore.toggleSidebar">
          {{ appStore.sidebarCollapsed ? '→' : '←' }}
        </button>
      </div>

      <nav class="sidebar-nav">
        <div
          v-for="item in menuItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          @click="router.push(item.path)"
        >
          <span class="nav-icon">{{ icons[item.icon] }}</span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div v-if="appStore.lastSyncTime" class="last-sync">
          <span class="sync-label">最后同步</span>
          <span class="sync-time">{{ formatTime(appStore.lastSyncTime) }}</span>
        </div>
      </div>
    </aside>

    <div class="main-content">
      <header class="top-bar">
        <div class="page-title">{{ getPageTitle(route.path) }}</div>
        <button class="btn-sync" @click="router.push('/sync')">🔄 同步数据</button>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; background-color: #f5f7fa; }
.sidebar { width: 240px; background: white; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; transition: width 0.3s; }
.sidebar.collapsed { width: 64px; }
.sidebar-header { padding: 16px; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; justify-content: space-between; }
.logo { display: flex; align-items: center; gap: 8px; }
.logo-icon { font-size: 24px; }
.logo-text { font-size: 16px; font-weight: 600; color: #1f2937; }
.collapse-btn { width: 28px; height: 28px; border: 1px solid #e5e7eb; border-radius: 4px; background: white; cursor: pointer; font-size: 12px; }
.sidebar-nav { flex: 1; padding: 8px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 8px; cursor: pointer; color: #6b7280; transition: all 0.2s; }
.nav-item:hover { background: #f3f4f6; color: #1f2937; }
.nav-item.active { background: #eff6ff; color: #0052D9; }
.nav-icon { font-size: 18px; }
.nav-label { font-size: 14px; }
.sidebar-footer { padding: 16px; border-top: 1px solid #e5e7eb; }
.last-sync { display: flex; flex-direction: column; gap: 4px; }
.sync-label { font-size: 12px; color: #9ca3af; }
.sync-time { font-size: 12px; color: #6b7280; }
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-bar { height: 64px; padding: 0 24px; background: white; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 18px; font-weight: 600; color: #1f2937; }
.btn-sync { padding: 8px 16px; background: #0052D9; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
.btn-sync:hover { background: #0043c4; }
.content { flex: 1; padding: 24px; overflow-y: auto; }
</style>
