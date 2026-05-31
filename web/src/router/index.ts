import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/components/layout/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/pages/Dashboard.vue') },
      { path: 'overview', name: 'Overview', component: () => import('@/pages/Overview.vue') },
      { path: 'customers', name: 'Customers', component: () => import('@/pages/customers/List.vue') },
      { path: 'customers/:id', name: 'CustomerDetail', component: () => import('@/pages/customers/Detail.vue') },
      { path: 'products', name: 'Products', component: () => import('@/pages/products/List.vue') },
      { path: 'orders', name: 'Orders', component: () => import('@/pages/orders/List.vue') },
      { path: 'orders/:id', name: 'OrderDetail', component: () => import('@/pages/orders/Detail.vue') },
      { path: 'inventory', name: 'Inventory', component: () => import('@/pages/Inventory.vue') },
      { path: 'reports', name: 'Reports', component: () => import('@/pages/Reports.vue') },
      { path: 'sync', name: 'Sync', component: () => import('@/pages/Sync.vue') },
      { path: 'settings', name: 'Settings', component: () => import('@/pages/Settings.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
