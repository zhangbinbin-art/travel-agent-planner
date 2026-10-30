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
                <el-button @click="openMapPicker">地图选点</el-button>
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
                :city="targetCity.trim()"
                :require-city="true"
                :allow-custom="true"
                :reset-signal="hotelResetSignal"
                @change="onHotelChange"
                @filters-change="hotelFilters = $event"
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

            <el-divider />
            <div class="booking-block">
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
            <div class="route-timeline">
              <div
                v-for="(item, idx) in timelineItems"
                :key="item.key"
                class="timeline-row"
                :class="item.kind"
              >
                <div class="timeline-marker">
                  <span class="timeline-dot" :class="item.kind"></span>
                  <span
                    v-if="idx < timelineItems.length - 1"
                    class="timeline-connector"
                  ></span>
                </div>
                <div class="timeline-content" @click="onTimelineClick(item)">
                  <div class="timeline-title">
                    <template v-if="item.kind === 'spot'">
                      {{ item.no }}. {{ item.name }}（{{ item.city }}）
                    </template>
                    <template v-else>
                      {{ item.name }}<span v-if="item.city">（{{ item.city }}）</span>
                    </template>
                  </div>
                  <div class="timeline-meta">
                    <template v-if="item.kind === 'spot'">评分：{{ item.score }} ｜ </template>
                    第{{ item.day }}天
                  </div>
                </div>
              </div>
            </div>

            <el-divider content-position="left">路线图</el-divider>
            <div ref="chartRef" class="chart-container"></div>

            <el-divider content-position="left">保存方案</el-divider>
            <div class="save-row">
              <el-input v-model="planName" placeholder="给这条路线起个名字" class="plan-name-input" />
              <el-button type="primary" :loading="saving" :disabled="!routeData" @click="handleSave">保存方案</el-button>
            </div>
          </div>
          <el-empty v-else description="请填写偏好并生成智能行程" />
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="mapDialogVisible" title="地图选点（回填位置与经纬度）" width="520px">
      <el-form label-width="80px">
        <el-form-item label="位置名称">
          <el-input v-model="tempName" placeholder="例如：杭州" />
        </el-form-item>
        <el-form-item label="快速选择">
          <div class="city-grid">
            <el-button
              v-for="(coord, city) in CITY_COORDS"
              :key="city"
              size="small"
              :type="tempName === city ? 'primary' : 'default'"
              @click="pickCity(city)"
            >
              {{ city }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model="tempLat" placeholder="例如 30.2741" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model="tempLng" placeholder="例如 120.1551" />
        </el-form-item>
        <el-form-item>
          <el-button @click="useCurrentLocation">使用当前位置</el-button>
          <span class="coord-hint">选择城市或定位后自动回填名称与经纬度</span>
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
import { ref, computed, watch, onMounted, onActivated, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
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

defineOptions({ name: 'Plan' })

const router = useRouter()

const PLAN_CACHE_KEY = 'last_trip_plan'
// 离开本页时是否前往详情页（用于 KeepAlive 返回恢复判断）
let leftToDetail = false

// 按需注册 ECharts 模块，避免整包引入导致 Plan 页 chunk 过大
echarts.use([GraphChart, GridComponent, TooltipComponent, CanvasRenderer])

const travelTypes = ['单人出行', '情侣出行', '家庭亲子', '老年休闲']
const prefOptions = ['自然风光', '人文古迹', '美食探店', '游乐乐园', '城市逛街', '徒步登山']

const startLocation = ref('')
const startLat = ref('')
const startLng = ref('')
const mapDialogVisible = ref(false)
const tempName = ref('')
const tempLat = ref('')
const tempLng = ref('')
const targetCity = ref('')
const travelType = ref('单人出行')
const preferences = ref([])
const days = ref(2)

const defaultHotelFilters = () => ({
  types: [],
  price: [0, 2000],
  minEnv: 0,
  minService: 0,
  features: []
})
const hotelFilters = ref(defaultHotelFilters())
const hotelResetSignal = ref(0)
const hotelPerDay = ref(300)
const selectedHotelId = ref('')
const selectedHotel = ref(null)
// 是否由后端自动推荐回填（用于区分用户手动切换）
const autoHotelApplied = ref(false)
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

// 常用城市坐标表：用于输入框手动填写地点时解析经纬度，以及定位后回填城市名
const CITY_COORDS = {
  北京: [39.9042, 116.4074],
  上海: [31.2304, 121.4737],
  杭州: [30.2741, 120.1551],
  广州: [23.1291, 113.2644],
  深圳: [22.5431, 114.0579],
  南京: [32.0603, 118.7969],
  苏州: [31.2989, 120.5853],
  厦门: [24.4798, 118.0894],
  桂林: [25.2736, 110.29],
  珠海: [22.2707, 113.5767],
  嘉兴: [30.7461, 120.7555],
  成都: [30.5728, 104.0668],
  西安: [34.3416, 108.9398],
  重庆: [29.563, 106.5516],
  武汉: [30.5928, 114.3055],
  长沙: [28.2282, 112.9388],
  青岛: [36.0671, 120.3826],
  天津: [39.3434, 117.3616],
  昆明: [24.8801, 102.8329],
  三亚: [18.2528, 109.5119]
}

const resolveCityCoords = (text) => {
  const value = String(text || '').trim()
  if (!value) return null
  for (const [city, coord] of Object.entries(CITY_COORDS)) {
    if (value.includes(city) || city.includes(value)) return { city, coord }
  }
  return null
}

const nearestCity = (lat, lng) => {
  let best = null
  let bestDist = Infinity
  for (const [city, coord] of Object.entries(CITY_COORDS)) {
    const dLat = Number(coord[0]) - lat
    const dLng = Number(coord[1]) - lng
    const dist = dLat * dLat + dLng * dLng
    if (dist < bestDist) {
      best = city
      bestDist = dist
    }
  }
  return best
}

// 手动填写出发位置时自动解析经纬度（与地图选点保持双向一致）
watch(startLocation, (val) => {
  const resolved = resolveCityCoords(val)
  if (resolved) {
    startLat.value = resolved.coord[0].toFixed(4)
    startLng.value = resolved.coord[1].toFixed(4)
  } else if (!String(val || '').trim()) {
    startLat.value = ''
    startLng.value = ''
  }
})

const startSpotName = computed(() => {
  if (startLocation.value) return startLocation.value
  return targetCity.value || '出发位置'
})

const hotelCity = (hotel) => {
  if (!hotel) return ''
  const match = String(hotel.address || '').match(/^(.+?市)/)
  if (match) return match[1].replace(/市$/, '')
  return targetCity.value || ''
}

// 路线顺序时间轴：优先使用后端 nodes 顺序（景点/酒店穿插），酒店节点使用当前选中酒店
const timelineItems = computed(() => {
  if (!routeData.value) return []
  const route = routeData.value.route || []
  const nodes = routeData.value.nodes || []
  const hotel = selectedHotel.value
  const items = []
  let spotNo = 0

  const pushSpot = (node) => {
    const spot = route.find((s) => s.id === node.id)
    spotNo += 1
    items.push({
      key: 'spot-' + node.id + '-d' + (node.day || 1) + '-' + spotNo,
      kind: 'spot',
      id: node.id,
      name: node.name || spot?.name,
      city: spot?.city || '',
      score: node.score ?? spot?.score,
      day: node.day || 1,
      no: spotNo
    })
  }
  const pushHotel = (day) => {
    if (!hotel) return
    items.push({
      key: 'hotel-' + hotel.id + '-d' + day,
      kind: 'hotel',
      id: hotel.id,
      name: hotel.name,
      city: hotelCity(hotel),
      day
    })
  }

  if (nodes.length) {
    nodes.forEach((node) => {
      if (node.node_type === 'hotel') {
        pushHotel(node.day || 1)
      } else {
        pushSpot(node)
      }
    })
  } else {
    // 兼容旧数据：无 nodes 时按景点顺序渲染
    route.forEach((spot) => pushSpot({ id: spot.id, name: spot.name, score: spot.score, day: 1 }))
  }
  return items
})

const isValidId = (id) => Number.isFinite(Number(id)) && Number(id) > 0

const onTimelineClick = (item) => {
  if (!isValidId(item.id)) {
    console.warn('[Plan] 节点 id 不存在，跳过跳转:', item)
    return
  }
  if (item.kind === 'spot') {
    router.push(`/spot-detail/${item.id}`)
  } else {
    router.push(`/hotel-detail/${item.id}`)
  }
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
  if (!hotel) {
    autoHotelApplied.value = false
    return
  }
  // 用户手动切换酒店：更新节点与食宿预算
  autoHotelApplied.value = false
  hotelPerDay.value = Number(hotel.price_per_day) || 0
  refreshBudgetHotel(hotelPerDay.value)
}

watch(hotelPerDay, (val) => {
  if (!selectedHotelId.value) {
    refreshBudgetHotel(val)
  }
})

const buildHotelFilterPayload = () => {
  const f = hotelFilters.value || defaultHotelFilters()
  const [minP, maxP] = f.price || [0, 2000]
  return {
    hotel_types: f.types || [],
    min_price: minP > 0 ? minP : null,
    max_price: maxP < 2000 ? maxP : null,
    min_env_score: f.minEnv > 0 ? f.minEnv : null,
    min_service_score: f.minService > 0 ? f.minService : null,
    hotel_features: f.features || []
  }
}

const applyAutoHotel = (hotel) => {
  if (!hotel) return
  selectedHotelId.value = hotel.hotel_id || hotel.id
  selectedHotel.value = {
    id: hotel.hotel_id || hotel.id,
    name: hotel.hotel_name || hotel.name,
    price_per_day: hotel.price ?? hotel.price_per_day,
    address: hotel.address,
    env_score: hotel.env_score,
    service_score: hotel.service_score,
    facilities: hotel.facilities,
    cover_img: hotel.cover_img,
    description: hotel.description
  }
  hotelPerDay.value = Number(hotel.price ?? hotel.price_per_day) || 0
  generatedHotelPerDay.value = hotelPerDay.value
  autoHotelApplied.value = true
}

const slimRouteData = (data) => {
  if (!data) return null
  const clone = JSON.parse(JSON.stringify(data))
  delete clone.recommended_hotels
  return clone
}

const slimHotel = (hotel) => {
  if (!hotel) return null
  return {
    id: hotel.id,
    name: hotel.name,
    price_per_day: hotel.price_per_day,
    address: hotel.address,
    env_score: hotel.env_score,
    service_score: hotel.service_score,
    facilities: hotel.facilities
  }
}

const savePlanCache = () => {
  try {
    const payload = {
      startLocation: startLocation.value,
      startLat: startLat.value,
      startLng: startLng.value,
      targetCity: targetCity.value,
      travelType: travelType.value,
      preferences: preferences.value,
      days: days.value,
      hotelFilters: hotelFilters.value,
      hotelPerDay: hotelPerDay.value,
      selectedHotelId: selectedHotelId.value,
      selectedHotel: slimHotel(selectedHotel.value),
      generatedHotelPerDay: generatedHotelPerDay.value,
      routeData: slimRouteData(routeData.value),
      planName: planName.value,
      savedTripId: savedTripId.value,
      bookingStart: bookingStart.value,
      bookingEnd: bookingEnd.value,
      guestCount: guestCount.value,
      remark: remark.value
    }
    sessionStorage.setItem(PLAN_CACHE_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn('[Plan] 保存会话缓存失败:', e?.message)
  }
}

const restorePlanCache = () => {
  try {
    const raw = sessionStorage.getItem(PLAN_CACHE_KEY)
    if (!raw) return false
    const data = JSON.parse(raw)
    startLocation.value = data.startLocation || ''
    startLat.value = data.startLat || ''
    startLng.value = data.startLng || ''
    targetCity.value = data.targetCity || ''
    travelType.value = data.travelType || '单人出行'
    preferences.value = data.preferences || []
    days.value = data.days || 2
    hotelFilters.value = data.hotelFilters || defaultHotelFilters()
    hotelPerDay.value = data.hotelPerDay ?? 300
    selectedHotelId.value = data.selectedHotelId ?? ''
    selectedHotel.value = data.selectedHotel || null
    generatedHotelPerDay.value = data.generatedHotelPerDay ?? null
    routeData.value = data.routeData || null
    planName.value = data.planName || ''
    savedTripId.value = data.savedTripId ?? null
    bookingStart.value = data.bookingStart || ''
    bookingEnd.value = data.bookingEnd || ''
    guestCount.value = data.guestCount ?? 1
    remark.value = data.remark || ''
    return true
  } catch (e) {
    console.warn('[Plan] 读取会话缓存失败:', e?.message)
    return false
  }
}

const clearPlanCache = () => {
  try {
    sessionStorage.removeItem(PLAN_CACHE_KEY)
  } catch (e) {
    // ignore
  }
}

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
    // 生成时由后端自动挑选酒店并按该酒店单价计算预算；手动切换在生成后本地重算
    const res = await api.post('/api/v1/trip/smart-recommend', {
      start_lat: startLat.value === '' ? null : Number(startLat.value),
      start_lng: startLng.value === '' ? null : Number(startLng.value),
      start_location: startLocation.value || undefined,
      target_city: targetCity.value.trim(),
      travel_type: travelType.value,
      preferences: preferences.value,
      days: days.value,
      hotel_per_day: null,
      ...buildHotelFilterPayload()
    })
    routeData.value = res.data
    planName.value = ''
    savedTripId.value = null
    const autoHotel = res.data?.recommended_hotel
    if (autoHotel) {
      applyAutoHotel(autoHotel)
      generatedHotelPerDay.value = Number(res.data?.hotel_per_day ?? autoHotel.price ?? 0)
    } else {
      // 无匹配酒店：不渲染酒店节点，提示用户放宽筛选
      selectedHotelId.value = ''
      selectedHotel.value = null
      autoHotelApplied.value = false
      generatedHotelPerDay.value = Number(res.data?.hotel_per_day ?? hotelPerDay.value)
      ElMessage.warning('暂无匹配酒店，可放宽筛选条件')
    }
    fillBookingDates(res.data?.budget?.days ?? days.value)
    savePlanCache()
    await nextTick()
    initChart()
  } catch (e) {
    ElMessage.error(extractError(e, '生成智能行程失败'))
  } finally {
    generating.value = false
  }
}

const resetAll = (clearCache = false) => {
  targetCity.value = ''
  startLocation.value = ''
  startLat.value = ''
  startLng.value = ''
  travelType.value = '单人出行'
  preferences.value = []
  days.value = 2
  hotelFilters.value = defaultHotelFilters()
  hotelResetSignal.value += 1
  hotelPerDay.value = 300
  selectedHotelId.value = ''
  selectedHotel.value = null
  autoHotelApplied.value = false
  routeData.value = null
  planName.value = ''
  generatedHotelPerDay.value = null
  savedTripId.value = null
  if (clearCache) clearPlanCache()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const handleReset = () => {
  // 预约表单（日期/人数/备注）保留，便于单独订酒店
  resetAll(true)
}

const openMapPicker = () => {
  tempName.value = startLocation.value || ''
  tempLat.value = startLat.value || ''
  tempLng.value = startLng.value || ''
  mapDialogVisible.value = true
}

const pickCity = (city) => {
  const coord = CITY_COORDS[city]
  if (!coord) return
  tempName.value = city
  tempLat.value = coord[0].toFixed(4)
  tempLng.value = coord[1].toFixed(4)
}

const useCurrentLocation = () => {
  if (!navigator.geolocation) {
    ElMessage.warning('当前浏览器不支持定位，请手动填写经纬度')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = Number(pos.coords.latitude.toFixed(6))
      const lng = Number(pos.coords.longitude.toFixed(6))
      tempLat.value = String(lat)
      tempLng.value = String(lng)
      const city = nearestCity(lat, lng)
      if (city) tempName.value = city
      ElMessage.success('已获取当前位置坐标')
    },
    () => ElMessage.warning('定位失败，请手动填写经纬度')
  )
}

const confirmLocation = () => {
  const name = String(tempName.value || '').trim()
  const lat = String(tempLat.value || '').trim()
  const lng = String(tempLng.value || '').trim()
  if (!lat || !lng) {
    ElMessage.warning('请选择城市或填写经纬度')
    return
  }
  // 名称与坐标双向统一：名称优先，缺失时用最近城市名回填
  startLocation.value = name || nearestCity(Number(lat), Number(lng)) || startLocation.value
  startLat.value = lat
  startLng.value = lng
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
  const rawNodes = routeData.value.nodes || []
  const hotelInfo = selectedHotel.value

  // 按 nodes 顺序构建图数据；酒店节点位置取前后景点中点
  const sequence = []
  if (rawNodes.length) {
    rawNodes.forEach((node) => {
      if (node.node_type === 'hotel') {
        if (hotelInfo) sequence.push({ kind: 'hotel', node })
      } else {
        sequence.push({ kind: 'spot', node })
      }
    })
  } else {
    route.forEach((spot) => sequence.push({ kind: 'spot', node: { id: spot.id, name: spot.name } }))
  }

  const graphNodes = []
  const links = []
  const coordOf = new Map()
  route.forEach((spot) => coordOf.set(String(spot.id), { x: spot.x, y: spot.y }))

  sequence.forEach((entry, idx) => {
    if (entry.kind === 'spot') {
      const spot = route.find((s) => s.id === entry.node.id)
      if (!spot) return
      graphNodes.push({
        name: 'spot-' + spot.id,
        value: spot.name,
        x: spot.x,
        y: spot.y,
        symbolSize: 16,
        itemStyle: { color: '#67c23a' },
        label: { show: true, formatter: spot.name, position: 'right' }
      })
    } else {
      if (!hotelInfo) return
      // 取前后景点坐标中点作为酒店位置
      const prev = sequence[idx - 1]
      const next = sequence[idx + 1]
      const prevCoord = prev?.kind === 'spot' ? coordOf.get(String(prev.node.id)) : null
      const nextCoord = next?.kind === 'spot' ? coordOf.get(String(next.node.id)) : null
      let pos = { x: 300, y: 300 }
      if (prevCoord && nextCoord) {
        pos = { x: (prevCoord.x + nextCoord.x) / 2, y: (prevCoord.y + nextCoord.y) / 2 }
      } else if (prevCoord) {
        pos = { x: prevCoord.x + 20, y: prevCoord.y + 20 }
      } else if (nextCoord) {
        pos = { x: nextCoord.x - 20, y: nextCoord.y - 20 }
      }
      graphNodes.push({
        name: 'hotel-' + hotelInfo.id,
        value: hotelInfo.name,
        x: pos.x,
        y: pos.y,
        symbol: 'diamond',
        symbolSize: 14,
        itemStyle: { color: '#409eff' },
        label: { show: true, formatter: hotelInfo.name, position: 'right' }
      })
    }
  })

  for (let i = 0; i < graphNodes.length - 1; i += 1) {
    links.push({ source: graphNodes[i].name, target: graphNodes[i + 1].name })
  }

  const option = {
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          return params.value
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
        data: graphNodes,
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

// 手动切换酒店时同步刷新路线图中的酒店节点
watch(selectedHotel, () => {
  if (routeData.value) {
    nextTick(() => initChart())
  }
})

onBeforeRouteLeave((to) => {
  leftToDetail = to.name === 'SpotDetail' || to.name === 'HotelDetail'
  if (leftToDetail && routeData.value) {
    savePlanCache()
  }
})

onMounted(() => {})

onActivated(() => {
  if (leftToDetail) {
    leftToDetail = false
    // 会话兜底：组件状态意外丢失时从 sessionStorage 恢复
    if (!routeData.value && restorePlanCache()) {
      nextTick(() => initChart())
    } else if (routeData.value) {
      nextTick(() => initChart())
    }
    return
  }
  // 从导航菜单或地址栏直接进入：全新初始化，不加载旧缓存
  resetAll(true)
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
.booking-block {
  margin-top: 4px;
}
.booking-tip {
  margin-left: 12px;
  color: #e6a23c;
  font-size: 12px;
}
.route-timeline {
  padding: 4px 0 4px 4px;
}
.timeline-row {
  display: flex;
  align-items: stretch;
  gap: 12px;
  min-height: 44px;
}
.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
  padding-top: 4px;
}
.timeline-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.timeline-dot.spot {
  background: #67c23a;
  box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.15);
}
.timeline-dot.hotel {
  background: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}
.timeline-connector {
  flex: 1;
  width: 2px;
  min-height: 20px;
  background: #e4e7ed;
  margin-top: 4px;
}
.timeline-content {
  flex: 1;
  padding: 0 8px 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}
.timeline-content:hover {
  background: #f5f7fa;
}
.timeline-title {
  color: #303133;
  font-size: 14px;
  line-height: 20px;
  font-weight: 500;
}
.timeline-row.hotel .timeline-title {
  color: #409eff;
}
.timeline-meta {
  color: #909399;
  font-size: 13px;
  line-height: 18px;
  margin-top: 4px;
}
</style>
