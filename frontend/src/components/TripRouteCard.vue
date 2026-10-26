<template>
  <el-card class="trip-route-card" shadow="hover">
    <div class="card-header">
      <div class="title-wrap">
        <div class="title" :title="trip.name">{{ trip.name }}</div>
        <div class="meta">
          途经 {{ trip.spot_count }} 个景点 · 总距离 {{ formatDistance(trip.total_distance) }} km · 创建时间 {{ formatTime(trip.created_at) }}
        </div>
        <div v-if="trip.budget" class="budget-meta">
          <div>门票 ¥{{ formatMoney(trip.budget.ticket_total ?? 0) }} · 食宿 ¥{{ formatMoney(trip.budget.hotel_total ?? 0) }} · 交通 ¥{{ formatMoney(trip.budget.traffic_total ?? 0) }}</div>
          <div class="budget-daily">
            <span class="budget-total">总计 ¥{{ formatMoney(trip.budget.grand_total ?? 0) }}</span> · 日均 ¥{{ formatMoney(trip.budget.daily_avg ?? 0) }}
          </div>
        </div>
      </div>
      <div class="actions">
        <el-button size="small" @click.stop="onView">查看详情</el-button>
        <el-button size="small" type="danger" plain @click.stop="onDelete">删除</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
const props = defineProps({
  trip: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['view', 'delete'])

const formatDistance = (val) => {
  const num = Number(val)
  if (Number.isNaN(num)) return '0.00'
  return num.toFixed(2)
}

const formatMoney = (val) => {
  const num = Number(val)
  if (Number.isNaN(num)) return '0.00'
  return num.toFixed(2)
}

const formatTime = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const onView = () => {
  emit('view', props.trip)
}

const onDelete = () => {
  emit('delete', props.trip)
}
</script>

<style scoped>
.trip-route-card {
  height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.title-wrap {
  min-width: 0;
  flex: 1;
}
.title {
  font-weight: 600;
  font-size: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.budget-meta {
  margin-top: 6px;
  color: #e6a23c;
  font-size: 13px;
}
.budget-total {
  color: #303133;
  font-weight: 600;
}
.budget-daily {
  color: #909399;
  font-size: 12px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
</style>
