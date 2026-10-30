<template>
  <div class="hotel-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ hotel?.name || '酒店详情' }}</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>

      <el-empty v-if="!loading && !hotel" description="酒店不存在或已下架" />

      <div v-else-if="hotel" class="detail-body">
        <img
          v-if="hotel.cover_img"
          :src="hotel.cover_img"
          class="cover"
          alt="酒店封面"
        />
        <div class="info-row">
          <span class="label">地址</span>
          <span>{{ hotel.address || '暂无' }}</span>
        </div>
        <div class="info-row">
          <span class="label">单价</span>
          <span class="price">¥{{ formatMoney(hotel.price_per_day) }}/天</span>
        </div>
        <div class="info-row">
          <span class="label">评分</span>
          <span>环境 {{ hotel.env_score || '-' }} ｜ 服务 {{ hotel.service_score || '-' }}</span>
        </div>
        <div class="info-row">
          <span class="label">简介</span>
          <span>{{ hotel.description || '暂无简介' }}</span>
        </div>
        <div class="info-row">
          <span class="label">配套设施</span>
          <span>
            <el-tag v-for="f in facilities" :key="f" size="small" class="facility-tag">{{ f }}</el-tag>
            <span v-if="!facilities.length">暂无</span>
          </span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getOnShelfHotels } from '@/api/hotel'
import { parseFacilities } from '@/utils/hotel'

const route = useRoute()
const hotel = ref(null)
const loading = ref(false)

const facilities = computed(() => parseFacilities(hotel.value))

const formatMoney = (val) => {
  const num = Number(val)
  return Number.isNaN(num) ? '0.00' : num.toFixed(2)
}

const fetchHotel = async () => {
  const id = Number(route.params.id)
  if (!Number.isFinite(id) || id <= 0) {
    console.warn('[HotelDetail] 无效的酒店 id，跳过加载:', route.params.id)
    return
  }
  loading.value = true
  try {
    const res = await getOnShelfHotels()
    const list = res.data?.items || []
    hotel.value = list.find((h) => Number(h.id) === id) || null
    if (!hotel.value) {
      console.warn('[HotelDetail] 未找到酒店 id:', id)
    }
  } catch (e) {
    console.warn('[HotelDetail] 获取酒店信息失败:', e?.message)
  } finally {
    loading.value = false
  }
}

onMounted(fetchHotel)
</script>

<style scoped>
.hotel-detail-page {
  max-width: 900px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.cover {
  width: 100%;
  max-height: 320px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 16px;
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.info-row {
  display: flex;
  gap: 12px;
  color: #606266;
  line-height: 1.7;
}
.label {
  width: 80px;
  flex-shrink: 0;
  color: #909399;
}
.price {
  color: #f56c6c;
  font-weight: 600;
}
.facility-tag {
  margin: 0 6px 6px 0;
}
</style>
