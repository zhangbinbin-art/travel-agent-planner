<template>
  <div class="dashboard">
    <el-card shadow="never" class="hotel-card">
      <div class="hotel-name">{{ hotel?.name || '未绑定酒店' }}</div>
      <div class="hotel-addr">{{ hotel?.address || '请联系管理员绑定酒店' }}</div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="12" :md="6" v-for="card in cards" :key="card.key">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ stats[card.key] ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDashboard, getMyMerchantHotel } from '@/api/hotel'

const stats = ref({})
const hotel = ref(null)

const cards = [
  { key: 'hotel_count', label: '绑定酒店数', color: '#409eff' },
  { key: 'pending_count', label: '待支付订单', color: '#e6a23c' },
  { key: 'confirm_count', label: '已支付订单', color: '#67c23a' },
  { key: 'booking_total', label: '总预定单', color: '#909399' }
]

const fetchData = async () => {
  try {
    const [dash, h] = await Promise.all([getDashboard(), getMyMerchantHotel()])
    stats.value = dash.data || {}
    hotel.value = h.data || null
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取看板数据失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.hotel-card { margin-bottom: 16px; }
.hotel-name { font-size: 18px; font-weight: 600; }
.hotel-addr { color: #909399; font-size: 13px; margin-top: 6px; }
.stat-card { text-align: center; margin-bottom: 16px; }
.stat-label { color: #909399; font-size: 14px; }
.stat-value { font-size: 32px; font-weight: 700; margin-top: 8px; }
</style>
