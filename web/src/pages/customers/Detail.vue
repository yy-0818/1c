<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCustomerStore } from '@/stores/customers'

const route = useRoute()
const customerStore = useCustomerStore()

const customer = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  const id = route.params.id as string
  customer.value = await customerStore.getCustomerById(id)
  loading.value = false
})

function formatDate(date: string | null): string {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="customer-detail">
    <div class="page-header">
      <h2>客户详情</h2>
      <button class="btn-back" @click="$router.back()">← 返回</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    
    <div v-else-if="!customer" class="empty">客户不存在</div>

    <div v-else class="detail-card">
      <div class="detail-section">
        <h3>基本信息</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <label>代码</label>
            <span>{{ customer.code || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>名称</label>
            <span>{{ customer.description }}</span>
          </div>
          <div class="detail-item">
            <label>INN</label>
            <span>{{ customer.inn || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>КПП</label>
            <span>{{ customer.kpp || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>联系信息</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <label>电话(工作)</label>
            <span>{{ customer.phone_work || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>电话(手机)</label>
            <span>{{ customer.phone_mobile || '-' }}</span>
          </div>
          <div class="detail-item">
            <label>邮箱</label>
            <span>{{ customer.email || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>地址</h3>
        <div class="detail-grid">
          <div class="detail-item full-width">
            <label>法律地址</label>
            <span>{{ customer.address_legal || '-' }}</span>
          </div>
          <div class="detail-item full-width">
            <label>实际地址</label>
            <span>{{ customer.address_actual || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>系统信息</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <label>创建时间</label>
            <span>{{ formatDate(customer.created_at) }}</span>
          </div>
          <div class="detail-item">
            <label>更新时间</label>
            <span>{{ formatDate(customer.updated_at) }}</span>
          </div>
          <div class="detail-item">
            <label>已删除</label>
            <span>{{ customer.deletion_mark ? '是' : '否' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.customer-detail {
  max-width: 1000px;
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
}

.btn-back {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

.detail-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.detail-section {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h3 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item.full-width {
  grid-column: span 2;
}

.detail-item label {
  font-size: 12px;
  color: #6b7280;
}

.detail-item span {
  font-size: 14px;
  color: #374151;
}
</style>
