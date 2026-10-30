<template>
  <div class="plan">
    <el-card>
      <template #header>
        <span class="card-title">智能路线规划</span>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <div class="panel">
            <div class="panel-title">智能偏好设置</div>

            <div class="form-block">
              <div class="section-label">出发位置</div>
              <div class="start-location-row">
                <el-input
                  v-model="startLocation"
                  placeholder="请输入出发城市，如：杭州"
                  clearable
                  class="start-city-input"
                />
                <el-button @click="mapDialogVisible = true">地图选点</el-button>
              </div>
              <div v-if="startLat && startLng" class="coord-tip">
                已选取坐标：{{ startLat }}, {{ startLng }}
              </div>
            </div>

            <div class="form-block">
              <div class="section-label">目标地区（单城市）</div>
              <el-input v-model="targetCity" placeholder="例如：杭州" clearable />
            </div>

            <div class="form-block">
              <div class="section-label">出行类型</div>
              <el-radio-group v-model="travelType" class="type-group">
                <el-radio-button v-for="t in travelTypes" :key="t" :value="t">{{ t }}</el-radio-button>
              </el-radio-group>
            </div>

            <div class="form-block">
              <div class="section-label">游玩偏好（可多选）</div>
              <el-checkbox-group v-model="preferences" class="pref-group">
                <el-checkbox-button v-for="p in prefOptions" :key="p" :value="p">{{ p }}</el-checkbox-button>
              </el-checkbox-group>
            </div>

            <div class="form-block days-section">
              <div class="section-label">游玩天数</div>
              <el-input-number v-model="days" :min="1" :max="10" />
            </div>

            <div class="form-block">
              <div class="section-label">酒店筛选与选择</div>
              <HotelPicker
                v-model="selectedHotelId"
                :city-list="cityWhitelist"
                :allow-custom="true"
                @change="onHotelChange"
              />
            </div>

            <div class="hotel-section">
              <div class="section-label">单日食宿费用（元/天）</div>
              <el-input-number
                v-model="hotelPerDay"
                :min="0"
                :max="100000"
                :step="50"
                :disabled="!!selectedHotelId"
              />
            </div>
            <div class="hotel-hint">
              {{ selectedHotelId ? '已按所选酒店单价自动带入预算' : '自定义价格仅用于预算估算，无法提交预约' }}
            </div>

            <div class="actions">
              <el-button type="primary" :loading="generating" @click="handleGenerate">
                生成智能行程
              </el-button>
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
              <div>目标城市：<span class="highlight">{{ routeData.target_city || targetCity }}</span></div>
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
              <div class="budget-row">
                <span>门票合计</span>
                <span>¥{{ formatMoney(routeData.budget.ticket_total ?? 0) }}</span>
              </div>
              <div class="budget-row">
                <span>食宿费用（{{ routeData.budget.days }} 天 × ¥{{ formatMoney(generatedHotelPerDay ?? hotelPerDay) }}/天）</span>
                <span>¥{{ formatMoney(routeData.budget.hotel_total ?? 0) }}</span>
              </div>
              <div class="budget-row">
                <span>交通费用（{{ formatDistance(routeData.total_distance) }} km）</span>
                <span>¥{{ formatMoney(routeData.budget.traffic_total ?? 0) }}</span>
              </div>
              <div class="budget-row budget-total">
                <span>总预算</span>
                <span class="highlight">¥{{ formatMoney(routeData.budget.grand_total ?? 0) }}</span>
              </div>
              <div class="budget-row">
                <span>日均预算（按 {{ routeData.budget.days }} 天）</span>
                <span class="highlight">¥{{ formatMoney(routeData.budget.daily_avg ?? 0) }}</span>
              </div>
            </div>
            <div v-else class="budget-empty">暂无预算信息</div>

            <el-divider content-position="left">路线顺序</el-divider>
            <el-steps direction="vertical" :active="routeData.route.length" finish-status="success">
              <el-step
                v-for="(spot, idx) in routeData.route"
                :key="spot.id"
                :title="(idx + 1) + '. ' + spot.name + '（' + spot.city + '）'"
                :description="'评分：' + spot.score + dayLabel(idx)"
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
          <el-empty v-else description="请填写偏好并生成智能行程" />

          <div class="panel booking-panel">
            <div class="panel-title">酒店预约（可选）</div>
            <el-form label-width="90px">
              <el-form-item label="入住日期">
                <el-date-picker
                  v-model="bookingStart"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择入住日期"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="离店日期">
                <el-date-picker
                  v-model="bookingEnd"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择离店日期"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="入住人数">
                <el-input-number v-model="guestCount" :min="1" :max="10" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="remark" maxlength="200" placeholder="选填，如房型偏好、到店时间" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="success"
                  :disabled="!selectedHotelId"
                  :loading="bookingSubmitting"
                  @click="submitBooking"
                >
                  提交酒店预约
                </el-button>
                <span v-if="!selectedHotelId" class="booking-tip">
                  自定义价格仅用于预算估算，无法提交预约
                </span>
              </el-form-item>
            </el-form>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="mapDialogVisible" title="地图选点（获取经纬度）" width="460px">
      <el-form label-width="80px">
        <el-form-item label="纬度">
          <el-input v-model="tempLat" placeholder="例如 30.2741" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model="tempLng" placeholder="例如 120.1551" />
        </el-form-item>
        <el-form-item>
          <el-button @click="useCurrentLocation">使用当前位置</el-button>
          <span class="coord-hint">也可手动填写经纬度，用于行程排序</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mapDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmLocation">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '@/api'
import { saveTrip } from '@/api/trip'
import { createHotelBooking } from '@/api/hotel'
import { auth } from '@/utils/auth'
import HotelPicker from '@/components/hotel/HotelPicker.vue'

const router = useRouter()

// 按需注册 ECharts 模块，避免整包引入导致 Plan 页 chunk 过大
echarts.use([GraphChart, GridComponent, TooltipComponent, CanvasRenderer])

const travelTypes = ['单人出行', '情侣出行', '家庭亲子', '老年休闲']
const prefOptions = ['自然风光', '人文古迹', '美食探店', '游乐乐园', '城市逛街', '徒步登山']

const startLocation = ref('')
const startLat = ref('')
const startLng = ref('')
const mapDialogVisible = ref(false)
const tempLat = ref('')
const tempLng = ref('')
const targetCity = ref('')
const travelType = ref('单人出行')
const preferences = ref([])
const days = ref(2)

const hotelPerDay = ref(300)
const selectedHotelId = ref('')
const selectedHotel = ref(null)
const bookingStart = ref('')
const bookingEnd = ref('')
const guestCount = ref(1)
const remark = ref('')
const bookingSubmitting = ref(false)
const savedTripId = ref(null)

const generating = ref(false)
const routeData = ref(null)
const planName = ref('')
const saving = ref(false)

const chartRef = ref(null)
let chartInstance = null
let resizeHandler = null

// 生成路线时实际使用的食宿单价快照
const generatedHotelPerDay = ref(null)

const cityWhitelist = computed(() => {
  const city = (targetCity.value || '').trim()
  return city ? [city] : []
})

const startSpotName = computed(() => {
  if (startLocation.value) return startLocation.value
  return targetCity.value || '出发位置'
})

const dayLabel = (idx) => {
  const plans = routeData.value?.day_plans || []
  for (const p of plans) {
    if (p.spot_ids?.includes(routeData.value.route[idx]?.id)) return ' ｜ 第' + p.day + '天'
  }
  return ''
}

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

const refreshBudgetHotel = (pricePerDay) => {
  if (!routeData.value?.budget) return
  const b = routeData.value.budget
  const safeDays = Number(b.days) || days.value || 1
  const hotelTotal = Number((safeDays * Number(pricePerDay || 0)).toFixed(2))
  const ticket = Number(b.ticket_total || 0)
  const traffic = Number(b.traffic_total || 0)
  const grand = Number((ticket + hotelTotal + traffic).toFixed(2))
  routeData.value.budget = {
    ...b,
    hotel_total: hotelTotal,
    grand_total: grand,
    daily_avg: Number((grand / safeDays).toFixed(2))
  }
  generatedHotelPerDay.value = Number(pricePerDay || 0)
}

const onHotelChange = (hotel) => {
  selectedHotel.value = hotel || null
  if (!hotel) return
  hotelPerDay.value = Number(hotel.price_per_day) || 0
  refreshBudgetHotel(hotelPerDay.value)
}

watch(hotelPerDay, (val) => {
  if (!selectedHotelId.value) {
    refreshBudgetHotel(val)
  }
})

const handleGenerate = async () => {
  if (!targetCity.value || !targetCity.value.trim()) {
    ElMessage.warning('请输入目标地区（单城市）')
    return
  }
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  generating.value = true
  routeData.value = null
  try {
    const sentHotelPerDay = selectedHotel.value
      ? Number(selectedHotel.value.price_per_day) || 0
      : hotelPerDay.value
    const res = await api.post('/api/v1/trip/smart-recommend', {
      start_lat: startLat.value === '' ? null : Number(startLat.value),
      start_lng: startLng.value === '' ? null : Number(startLng.value),
      start_location: startLocation.value || undefined,
      target_city: targetCity.value.trim(),
      travel_type: travelType.value,
      preferences: preferences.value,
      days: days.value,
      hotel_per_day: sentHotelPerDay
    })
    routeData.value = res.data
    generatedHotelPerDay.value = sentHotelPerDay
    planName.value = ''
    savedTripId.value = null
    fillBookingDates(res.data?.budget?.days ?? days.value)
    await nextTick()
    initChart()
  } catch (e) {
    ElMessage.error(extractError(e, '生成智能行程失败'))
  } finally {
    generating.value = false
  }
}

const handleReset = () => {
  targetCity.value = ''
  startLocation.value = ''
  startLat.value = ''
  startLng.value = ''
  travelType.value = '单人出行'
  preferences.value = []
  days.value = 2
  selectedHotelId.value = ''
  selectedHotel.value = null
  routeData.value = null
  planName.value = ''
  generatedHotelPerDay.value = null
  savedTripId.value = null
  // 预约表单（日期/人数/备注）保留，便于单独订酒店
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const useCurrentLocation = () => {
  if (!navigator.geolocation) {
    ElMessage.warning('当前浏览器不支持定位，请手动填写经纬度')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      tempLat.value = pos.coords.latitude.toFixed(6)
      tempLng.value = pos.coords.longitude.toFixed(6)
      ElMessage.success('已获取当前位置坐标')
    },
    () => ElMessage.warning('定位失败，请手动填写经纬度')
  )
}

const confirmLocation = () => {
  startLat.value = String(tempLat.value || '').trim()
  startLng.value = String(tempLng.value || '').trim()
  mapDialogVisible.value = false
}

const formatDate = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const fillBookingDates = (totalDays) => {
  if (bookingStart.value && bookingEnd.value) return
  const start = new Date()
  const end = new Date()
  end.setDate(end.getDate() + (Number(totalDays) || 1))
  bookingStart.value = formatDate(start)
  bookingEnd.value = formatDate(end)
}

const submitBooking = async () => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (!selectedHotelId.value) {
    ElMessage.warning('自定义价格仅用于预算估算，无法提交预约')
    return
  }
  if (!bookingStart.value || !bookingEnd.value) {
    ElMessage.warning('请选择入住和离店日期')
    return
  }
  if (bookingEnd.value <= bookingStart.value) {
    ElMessage.warning('离店日期必须晚于入住日期')
    return
  }
  bookingSubmitting.value = true
  try {
    let routeId = savedTripId.value
    if (!routeId && routeData.value) {
      const orderedRouteIds = routeData.value.route.map((s) => s.id)
      const autoName =
        (planName.value && planName.value.trim()) ||
        '智能行程 ' + new Date().toLocaleString('zh-CN')
      const saved = await saveTrip({
        name: autoName,
        spot_ids: orderedRouteIds,
        start_spot_id: orderedRouteIds[0],
        days: routeData.value.budget?.days ?? days.value,
        hotel_per_day: generatedHotelPerDay.value ?? hotelPerDay.value
      })
      routeId = saved.data?.id || null
      savedTripId.value = routeId
      planName.value = autoName
      ElMessage.success('已自动保存行程，便于关联预约')
    }

    const res = await createHotelBooking({
      hotel_id: selectedHotelId.value,
      start_date: bookingStart.value,
      end_date: bookingEnd.value,
      guest_count: guestCount.value,
      remark: remark.value || undefined,
      route_id: routeId || null
    })
    ElMessage.success(
      '预约提交成功，请等待商家确认（' +
        res.data?.days +
        ' 天，¥' +
        formatMoney(res.data?.total_price) +
        '）'
    )
  } catch (e) {
    ElMessage.error(extractError(e, '提交预约失败'))
  } finally {
    bookingSubmitting.value = false
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
    symbolSize: 16,
    itemStyle: { color: '#409eff' },
    label: { show: true, formatter: spot.name, position: 'right' }
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
          const leg = legs.find(
            (l) => String(l.from_spot_id) === params.data.source && String(l.to_spot_id) === params.data.target
          )
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
        links,
        roam: true,
        label: { show: true },
        lineStyle: { color: '#909399', curveness: 0.1, width: 2 },
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
    ElMessage.warning('请先生成智能行程')
    return
  }
  if (!planName.value || !planName.value.trim()) {
    ElMessage.warning('请输入行程名称')
    return
  }
  saving.value = true
  try {
    const orderedRouteIds = routeData.value.route.map((s) => s.id)
    const saved = await saveTrip({
      name: planName.value.trim(),
      spot_ids: orderedRouteIds,
      start_spot_id: orderedRouteIds[0],
      days: routeData.value.budget?.days ?? days.value,
      hotel_per_day: generatedHotelPerDay.value ?? hotelPerDay.value
    })
    savedTripId.value = saved.data?.id || null
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

onMounted(() => {})

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
.form-block {
  margin-bottom: 16px;
}
.section-label {
  color: #606266;
  margin-bottom: 8px;
}
.start-location-row {
  display: flex;
  gap: 8px;
}
.start-city-input {
  flex: 1;
}
.coord-tip {
  color: #67c23a;
  font-size: 12px;
  margin-top: 6px;
}
.coord-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
.type-group,
.pref-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.days-section {
  display: flex;
  align-items: center;
  gap: 12px;
}
.days-section .section-label {
  margin-bottom: 0;
}
.hotel-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.hotel-hint {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
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
.booking-panel {
  margin-top: 16px;
  min-height: auto;
}
.booking-tip {
  margin-left: 12px;
  color: #e6a23c;
  font-size: 12px;
}
</style>
