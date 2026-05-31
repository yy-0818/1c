<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="detail-page">
    <h2>订单详情</h2>
    <p>订单ID: {{ route.params.id }}</p>
  </div>
</template>

<style scoped>
.detail-page { max-width: 1000px; margin: 0 auto; }
.detail-page h2 { font-size: 24px; margin-bottom: 20px; }
</style>
