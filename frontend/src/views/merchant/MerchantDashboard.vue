<template>
  <div class="dashboard">
    <el-card shadow="never" class="hotel-card">
      <div class="hotel-name">{{ hotel?.name || '未绑定酒店' }}</div>
      <div class="hotel-addr">{{ hotel?.address || '请联系管理员绑定酒店' }}</div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="12" :md="6" v-for="card in cards" :key="card.key">
        <el-card
          shadow="hover"
          class="stat-card is-clickable"
          role="button"
          tabindex="0"
          @click="goCard(card)"
          @keyup.enter="goCard(card)"
        >
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ stats[card.key] ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDashboard, getMyMerchantHotel } from '@/api/hotel'

const router = useRouter()
const stats = ref({})
const hotel = ref(null)

// 卡片点击跳转：绑定酒店 -> 酒店详情；订单类 -> 预定订单并携带状态筛选
const cards = [
  { key: 'hotel_count', label: '绑定酒店数', color: '#409eff', to: '/merchant/hotel-info' },
  { key: 'pending_count', label: '待支付订单', color: '#e6a23c', to: '/merchant/orders', status: 'pending_pay' },
  { key: 'confirm_count', label: '已支付订单', color: '#67c23a', to: '/merchant/orders', status: 'paid' },
  { key: 'booking_total', label: '总预定单', color: '#909399', to: '/merchant/orders' }
]

const goCard = (card) => {
  if (!card?.to) return
  if (card.status) router.push({ path: card.to, query: { status: card.status } })
  else router.push({ path: card.to })
}

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
/* 可点击卡片：指针 + 轻微上浮 + 边框高亮 */
.stat-card.is-clickable {
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}
.stat-card.is-clickable:hover {
  transform: translateY(-3px);
  border-color: #ff7a2f !important;
  box-shadow: 0 8px 18px rgba(34, 34, 34, 0.12) !important;
}
.stat-card.is-clickable:focus-visible {
  outline: 2px solid #ff7a2f;
  outline-offset: 2px;
}
.stat-label { color: #909399; font-size: 14px; }
.stat-value { font-size: 32px; font-weight: 700; margin-top: 8px; }
</style>
