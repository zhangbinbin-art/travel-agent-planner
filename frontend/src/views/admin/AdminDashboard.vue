<template>
  <div class="admin-dashboard">
    <el-card shadow="never" class="head-card">
      <div class="head-title">平台总览</div>
      <div class="head-sub">数据大盘 · 点击卡片可进入对应管理页</div>
    </el-card>

    <div class="stat-grid">
      <el-card
        v-for="card in cards"
        :key="card.key"
        shadow="hover"
        class="stat-card"
        @click="router.push(card.to)"
      >
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value" :style="{ color: card.color }">{{ stats[card.key] ?? 0 }}</div>
        <div v-if="card.tip" class="stat-tip">{{ card.tip }}</div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const stats = ref({})

const cards = [
  { key: 'user_count', label: '用户总数', color: '#409eff', to: '/admin' },
  { key: 'merchant_count', label: '商户数量', color: '#ff7a2f', to: '/admin/merchant-audit', tip: '含待审核商户' },
  { key: 'spot_count', label: '景点总数', color: '#67c23a', to: '/admin/spot' },
  { key: 'post_count', label: '游记总数', color: '#e6a23c', to: '/admin/post-audit', tip: '含待审核游记' },
  { key: 'order_count', label: '订单总量', color: '#909399', to: '/admin/data' }
]

const fetchStats = async () => {
  try {
    const res = await api.get('/api/v1/admin/stats')
    stats.value = res.data || {}
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取统计数据失败')
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.admin-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.head-title {
  font-size: 18px;
  font-weight: 800;
  color: #222;
}
.head-sub {
  margin-top: 4px;
  font-size: 12.5px;
  color: #7b8794;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.stat-card {
  text-align: center;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
  border-color: #ff7a2f !important;
  box-shadow: 0 8px 18px rgba(34, 34, 34, 0.12) !important;
}
.stat-label {
  font-size: 14px;
  color: #909399;
}
.stat-value {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 800;
}
.stat-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #a8b3c0;
}
</style>
