<template>
  <div class="my-plan">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="card-title">我的路线</span>
        </div>
      </template>

      <div v-loading="loading">
        <el-row :gutter="16" v-if="trips.length">
          <el-col v-for="trip in trips" :key="trip.id" :xs="24" :sm="12" :md="8" class="trip-col">
            <TripRouteCard :trip="trip" @view="openDetail" @delete="handleDelete" />
          </el-col>
        </el-row>
        <el-empty v-else description="还没有保存的路线">
          <el-button type="primary" @click="goPlan">去规划路线</el-button>
        </el-empty>

        <el-pagination
          v-if="total > pageSize"
          class="pager"
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="路线详情" width="640px">
      <div v-loading="detailLoading">
        <div v-if="detail" class="detail-info">
          <div class="detail-row"><span class="label">路线名称：</span>{{ detail.name }}</div>
          <div class="detail-row"><span class="label">总距离：</span>{{ formatDistance(detail.total_distance) }} km</div>
          <div class="detail-row"><span class="label">途经景点数：</span>{{ detail.spot_count }}</div>
          <el-divider content-position="left">路线顺序</el-divider>
          <div class="route-list">
            <div v-for="(spot, idx) in detail.route" :key="spot.id" class="route-item">
              <div class="route-main">
                <span class="order">{{ idx + 1 }}</span>
                <span class="spot-name">{{ spot.name }}</span>
                <span class="spot-city">{{ spot.city }}</span>
                <span class="spot-score">评分 {{ spot.score }}</span>
              </div>
            </div>
          </div>
          <el-divider content-position="left">路段距离</el-divider>
          <div class="legs-list">
            <div v-for="(leg, idx) in detail.legs" :key="idx" class="leg-item">
              <span>{{ getSpotName(detail.route, leg.from_spot_id) }} -> {{ getSpotName(detail.route, leg.to_spot_id) }}</span>
              <span class="leg-dist">{{ Number(leg.distance).toFixed(2) }} km</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyTrips, getTripDetail, deleteTrip } from '@/api/trip'
import TripRouteCard from '@/components/TripRouteCard.vue'

const router = useRouter()

const trips = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(6)
const loading = ref(false)

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const extractError = (e, fallback) => {
  if (e?.response?.status === 403) return '无权限操作'
  const detailMsg = e?.response?.data?.detail
  if (typeof detailMsg === 'string' && detailMsg) return detailMsg
  if (Array.isArray(detailMsg)) {
    const messages = detailMsg.map((item) => item?.msg || item?.message).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

const formatDistance = (val) => {
  const num = Number(val)
  if (Number.isNaN(num)) return '0.00'
  return num.toFixed(2)
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getMyTrips({ page: page.value, page_size: pageSize.value })
    trips.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    ElMessage.error(extractError(e, '获取路线列表失败'))
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p) => {
  page.value = p
  fetchList()
}

const goPlan = () => {
  router.push('/plan')
}

const openDetail = async (trip) => {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await getTripDetail(trip.id)
    detail.value = res.data
  } catch (e) {
    ElMessage.error(extractError(e, '获取路线详情失败'))
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const getSpotName = (routeArr, spotId) => {
  if (!Array.isArray(routeArr)) return spotId
  const found = routeArr.find((s) => s.id === spotId)
  return found ? found.name : spotId
}

const handleDelete = async (trip) => {
  try {
    await ElMessageBox.confirm('确定删除这条路线吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteTrip(trip.id)
    ElMessage.success('删除成功')
    if (trips.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await fetchList()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.trip-col {
  margin-bottom: 16px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.detail-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-row {
  color: #303133;
}
.label {
  color: #606266;
}
.route-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.route-item {
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}
.route-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.order {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
}
.spot-name {
  font-weight: 600;
}
.spot-city {
  color: #606266;
}
.spot-score {
  color: #f59e0b;
}
.legs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.leg-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #f8f9fa;
  border-radius: 4px;
}
.leg-dist {
  color: #409eff;
}
</style>
