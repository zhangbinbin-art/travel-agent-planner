<template>
  <div class="plan">
    <el-card>
      <template #header>
        <span class="card-title">智能路线规划</span>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <div class="panel">
            <div class="panel-title">选择景点与起点</div>
            <el-radio-group v-model="candidateTab" size="small" class="candidate-tabs">
              <el-radio-button value="all">全部景点</el-radio-button>
              <el-radio-button value="favorite">我的收藏</el-radio-button>
            </el-radio-group>
            <div v-if="candidateTab === 'favorite' && !auth.token" class="favorite-guest">
              <el-empty description="请先登录后查看收藏" :image-size="80">
                <el-button type="primary" @click="goLogin">去登录</el-button>
              </el-empty>
            </div>
            <div v-else class="spot-loading" v-loading="candidateTab === 'favorite' ? favoritesLoading : spotsLoading">
              <div class="spot-count">已选择 {{ selectedSpotIds.length }} 个景点（至少选择 2 个）</div>
              <el-empty
                v-if="!displaySpots.length"
                :description="candidateTab === 'favorite' ? '还没有收藏的景点' : '暂无可选景点'"
                :image-size="80"
              />
              <el-checkbox-group v-else v-model="selectedSpotIds" class="spot-group">
                <div v-for="spot in displaySpots" :key="spot.id" class="spot-item">
                  <el-checkbox :value="spot.id">
                    <span class="spot-label">{{ spot.name }}（{{ spot.city }}）</span>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>
            <div class="days-section">
              <div class="section-label">游玩天数</div>
              <el-input-number v-model="days" :min="1" :max="30" />
            </div>
            <el-divider />
            <div class="start-section">
              <div class="section-label">起点景点</div>
              <el-select v-model="startSpotId" placeholder="请选择起点景点" clearable class="start-select">
                <el-option
                  v-for="spot in selectedSpotsList"
                  :key="spot.id"
                  :label="spot.name + '（' + spot.city + '）'"
                  :value="spot.id"
                />
              </el-select>
            </div>
            <div class="actions">
              <el-button type="primary" :loading="generating" @click="handleGenerate">生成路线</el-button>
              <el-button @click="handleReset">重置</el-button>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :md="16">
          <div class="panel" v-if="routeData">
            <div class="panel-title">路线结果</div>
            <div class="summary">
              <div>总距离：<span class="highlight">{{ formatDistance(routeData.total_distance) }} km</span></div>
              <div>途经景点数：<span class="highlight">{{ routeData.route.length }}</span></div>
              <div>起点：<span class="highlight">{{ startSpotName }}</span></div>
            </div>
            <el-divider content-position="left">预算预估</el-divider>
            <div v-if="routeData.budget" class="budget-card">
              <div class="budget-head">游玩天数：<span class="highlight">{{ routeData.budget.days }}</span> 天</div>
              <div v-for="item in (routeData.budget.items || [])" :key="item.spot_id" class="budget-row">
                <span class="budget-name">{{ item.name }}</span>
                <span>门票 ¥{{ formatMoney(item.ticket_price) }}</span>
              </div>
              <el-divider class="budget-divider" />
              <div class="budget-row budget-total">
                <span>门票合计</span>
                <span>¥{{ formatMoney(routeData.budget.ticket_total) }}</span>
              </div>
              <div class="budget-row">
                <span>日均预算（按 {{ routeData.budget.days }} 天）</span>
                <span class="highlight">¥{{ formatMoney(routeData.budget.daily_average) }}</span>
              </div>
            </div>
            <div v-else class="budget-empty">暂无预算信息</div>
            <el-divider content-position="left">路线顺序</el-divider>
            <el-steps direction="vertical" :active="routeData.route.length" finish-status="success">
              <el-step
                v-for="(spot, idx) in routeData.route"
                :key="spot.id"
                :title="(idx + 1) + '. ' + spot.name + '（' + spot.city + '）'"
                :description="'评分：' + spot.score"
              />
            </el-steps>
            <el-divider content-position="left">路线图</el-divider>
            <div ref="chartRef" class="chart-container"></div>
            <el-divider content-position="left">保存方案</el-divider>
            <div class="save-row">
              <el-input v-model="planName" placeholder="给这条路线起个名字" class="plan-name-input" />
              <el-button type="primary" :loading="saving" :disabled="!routeData" @click="handleSave">保存方案</el-button>
            </div>
          </div>
          <el-empty v-else description="请在左侧选择景点并生成路线" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getSpotList } from '@/api/spot'
import { getMyFavoriteSpots } from '@/api/favorite'
import { generateTrip, saveTrip } from '@/api/trip'
import { auth } from '@/utils/auth'

const router = useRouter()

// 按需注册 ECharts 模块，避免整包引入导致 Plan 页 chunk 过大
echarts.use([GraphChart, TooltipComponent, CanvasRenderer])

const spots = ref([])
const spotsLoading = ref(false)
const favoriteSpots = ref([])
const favoritesLoading = ref(false)
const candidateTab = ref('all')
const selectedSpotIds = ref([])
const startSpotId = ref(null)
const days = ref(2)

const generating = ref(false)
const routeData = ref(null)
const planName = ref('')
const saving = ref(false)

const chartRef = ref(null)
let chartInstance = null
let resizeHandler = null

const extractError = (e, fallback) => {
  if (e?.response?.status === 403) return '无权限操作'
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

const displaySpots = computed(() => {
  return candidateTab.value === 'favorite' ? favoriteSpots.value : spots.value
})

const spotMap = computed(() => {
  const map = new Map()
  ;[...spots.value, ...favoriteSpots.value].forEach((spot) => {
    if (spot && spot.id !== undefined && !map.has(spot.id)) {
      map.set(spot.id, spot)
    }
  })
  return map
})

const selectedSpotsList = computed(() => {
  return selectedSpotIds.value.map((id) => spotMap.value.get(id)).filter(Boolean)
})

const startSpotName = computed(() => {
  if (!routeData.value || !routeData.value.route.length) return ''
  const start = routeData.value.route.find((s) => s.id === startSpotId.value) || routeData.value.route[0]
  return start ? start.name : ''
})

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

watch(selectedSpotIds, (newVal) => {
  if (!newVal || newVal.length === 0) {
    startSpotId.value = null
    return
  }
  if (startSpotId.value && !newVal.includes(startSpotId.value)) {
    startSpotId.value = null
  }
  if (!startSpotId.value) {
    startSpotId.value = newVal[0]
  }
})

const fetchSpots = async () => {
  spotsLoading.value = true
  try {
    const res = await getSpotList({ page: 1, page_size: 100 })
    spots.value = res.data.items || []
  } catch (e) {
    ElMessage.error(extractError(e, '获取景点列表失败'))
  } finally {
    spotsLoading.value = false
  }
}

const fetchFavoriteSpots = async () => {
  if (!auth.token) return
  favoritesLoading.value = true
  try {
    const res = await getMyFavoriteSpots()
    favoriteSpots.value = (res.data?.items || []).map((item) => item?.spot).filter(Boolean)
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.warning('请先登录')
      return
    }
    ElMessage.error(extractError(e, '获取收藏景点失败'))
  } finally {
    favoritesLoading.value = false
  }
}

const goLogin = () => {
  router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
}

watch(candidateTab, (val) => {
  if (val === 'favorite' && auth.token) {
    fetchFavoriteSpots()
  }
})

const handleGenerate = async () => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (selectedSpotIds.value.length < 2) {
    ElMessage.warning('请至少选择两个景点')
    return
  }
  if (!startSpotId.value) {
    ElMessage.warning('请选择起点景点')
    return
  }
  generating.value = true
  routeData.value = null
  try {
    const res = await generateTrip({
      spot_ids: selectedSpotIds.value,
      start_spot_id: startSpotId.value,
      days: days.value
    })
    routeData.value = res.data
    planName.value = ''
    await nextTick()
    initChart()
  } catch (e) {
    ElMessage.error(extractError(e, '生成路线失败'))
  } finally {
    generating.value = false
  }
}

const handleReset = () => {
  selectedSpotIds.value = []
  startSpotId.value = null
  routeData.value = null
  planName.value = ''
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const initChart = () => {
  if (!chartRef.value || !routeData.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)
  const route = routeData.value.route || []
  const legs = routeData.value.legs || []
  const nodes = route.map((spot) => ({
    name: String(spot.id),
    value: spot.name,
    x: spot.x,
    y: spot.y,
    symbolSize: spot.id === startSpotId.value ? 18 : 14,
    itemStyle: {
      color: spot.id === startSpotId.value ? '#409eff' : '#67c23a'
    },
    label: {
      show: true,
      formatter: spot.name,
      position: 'right'
    }
  }))
  const links = legs.map((leg) => ({
    source: String(leg.from_spot_id),
    target: String(leg.to_spot_id)
  }))
  const option = {
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          const spot = route.find((s) => String(s.id) === params.name)
          if (spot) {
            return spot.name + '（' + spot.city + '）<br/>评分：' + spot.score
          }
          return params.value
        }
        if (params.dataType === 'edge') {
          const from = route.find((s) => String(s.id) === params.data.source)
          const to = route.find((s) => String(s.id) === params.data.target)
          const leg = legs.find((l) => String(l.from_spot_id) === params.data.source && String(l.to_spot_id) === params.data.target)
          if (from && to) {
            return from.name + ' -> ' + to.name + '<br/>距离：' + (leg ? Number(leg.distance).toFixed(2) : '') + ' km'
          }
        }
        return ''
      }
    },
    xAxis: { show: false, type: 'value' },
    yAxis: { show: false, type: 'value' },
    series: [
      {
        type: 'graph',
        layout: 'none',
        data: nodes,
        links: links,
        roam: true,
        label: {
          show: true
        },
        lineStyle: {
          color: '#909399',
          curveness: 0.1,
          width: 2
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 10]
      }
    ]
  }
  chartInstance.setOption(option)
  if (!resizeHandler) {
    resizeHandler = () => {
      if (chartInstance) chartInstance.resize()
    }
    window.addEventListener('resize', resizeHandler)
  }
}

const handleSave = async () => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (!routeData.value) {
    ElMessage.warning('请先生成路线')
    return
  }
  if (!planName.value || !planName.value.trim()) {
    ElMessage.warning('请输入路线名称')
    return
  }
  saving.value = true
  try {
    const orderedRouteIds = routeData.value.route.map((s) => s.id)
    await saveTrip({
      name: planName.value.trim(),
      spot_ids: orderedRouteIds,
      start_spot_id: startSpotId.value,
      days: days.value
    })
    ElMessage.success('保存成功')
    try {
      await ElMessageBox.confirm('是否前往“我的路线”查看？', '提示', {
        confirmButtonText: '去查看',
        cancelButtonText: '留在此页',
        type: 'success'
      })
      router.push('/user/my-plan')
    } catch (e) {
      // user chose to stay
    }
  } catch (e) {
    ElMessage.error(extractError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSpots()
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    resizeHandler = null
  }
})
</script>

<style scoped>
.card-title {
  font-weight: 600;
}
.panel {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px;
  min-height: 400px;
}
.panel-title {
  font-weight: 600;
  margin-bottom: 12px;
}
.candidate-tabs {
  margin-bottom: 12px;
}
.favorite-guest {
  padding: 8px 0;
}
.spot-count {
  color: #606266;
  margin-bottom: 10px;
}
.days-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.spot-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
}
.spot-item {
  display: flex;
}
.spot-label {
  color: #303133;
}
.start-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-label {
  color: #606266;
}
.start-select {
  width: 100%;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #606266;
}
.highlight {
  color: #409eff;
  font-weight: 600;
}
.budget-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px 14px;
  background: #fafcff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.budget-head {
  color: #303133;
}
.budget-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: #606266;
}
.budget-name {
  color: #303133;
}
.budget-divider {
  margin: 4px 0;
}
.budget-total {
  color: #303133;
  font-weight: 600;
}
.budget-empty {
  color: #909399;
  font-size: 13px;
}
.chart-container {
  width: 100%;
  height: 380px;
}
.save-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.plan-name-input {
  flex: 1;
  max-width: 320px;
}
</style>
