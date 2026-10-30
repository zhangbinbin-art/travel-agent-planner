<template>
  <el-dialog v-model="visible" :title="hotel?.name || '酒店详情'" width="520px">
    <div v-if="hotel" class="hotel-detail">
      <div class="detail-row">
        <span class="detail-label">地址</span>
        <span>{{ hotel.address || '暂无' }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">单价</span>
        <span class="detail-price">¥{{ formatMoney(hotel.price_per_day) }}/天</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">评分</span>
        <span>环境 {{ hotel.env_score || '-' }} ｜ 服务 {{ hotel.service_score || '-' }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">简介</span>
        <span>{{ hotel.description || '暂无简介' }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">配套设施</span>
        <span>
          <el-tag v-for="f in facilities" :key="f" size="small" class="facility-tag">{{ f }}</el-tag>
          <span v-if="!facilities.length">暂无</span>
        </span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { parseFacilities } from '@/utils/hotel'

const props = defineProps({
  hotel: { type: Object, default: null }
})
const visible = defineModel({ type: Boolean, default: false })

const facilities = computed(() => parseFacilities(props.hotel))

const formatMoney = (val) => {
  const num = Number(val)
  return Number.isNaN(num) ? '0.00' : num.toFixed(2)
}
</script>

<style scoped>
.hotel-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-row {
  display: flex;
  gap: 12px;
  color: #606266;
  line-height: 1.6;
}
.detail-label {
  width: 70px;
  flex-shrink: 0;
  color: #909399;
}
.detail-price {
  color: #f56c6c;
  font-weight: 600;
}
.facility-tag {
  margin: 0 6px 6px 0;
}
</style>
