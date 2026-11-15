<template>
  <div class="plan">
    <section class="page-card">
      <header class="page-head">
        <div class="page-heading">
          <span class="tr-section-sub">AI PLANNER</span>
          <h1 class="tr-section-title">智能路线规划</h1>
        </div>
      </header>

      <div class="action-bar">
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成路线</el-button>
        <el-button :disabled="!routeData" :loading="generating" @click="handleRegenerate">重新生成</el-button>
        <el-button :disabled="!routeData" :loading="saving" @click="handleSave">保存路线</el-button>
        <el-button :disabled="!routeData" @click="exportRoute">导出路线</el-button>
        <el-input
          v-model="planName"
          class="plan-name-input"
          placeholder="路线名称（保存用）"
        />
        <el-button text @click="handleReset">重置</el-button>
      </div>

      <div class="plan-grid">
        <div class="plan-col plan-col--left">
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
              <div class="target-city-row">
                <el-input
                  v-model="targetCity"
                  placeholder="例如：杭州"
                  clearable
                  @keyup.enter="handleGenerate"
                />
                <el-button type="primary" :loading="generating" @click="handleGenerate">搜索路线</el-button>
              </div>
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

            <div class="form-block days-section">
              <div class="section-label">每日景点数量</div>
              <el-input-number v-model="perDay" :min="1" :max="4" :step="1" />
            </div>
            <div class="field-hint">每天规划 1~4 个景点</div>

            <div class="hotel-block">
              <div class="panel-title">酒店预订（可选）</div>

              <div class="form-block">
                <div class="section-label">酒店筛选与选择</div>
                <HotelPicker
                  v-model="selectedHotelId"
                  :city="targetCity.trim()"
                  :allow-custom="!hasGeneratedRoute"
                  :generated="hasGeneratedRoute"
                  :hotel-markers="routeData?.hotel_markers || []"
                  :reset-signal="hotelResetSignal"
                  :filter-seed="hotelFilterSeed"
                  @change="onHotelChange"
                  @filters-change="hotelFilters = $event"
                />
              </div>

              <div v-if="selectedHotelId" class="hotel-hint">已按所选酒店单价自动带入预算</div>

              <div class="booking-block">
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
                </el-form-item>
              </el-form>
              </div>
            </div>
          </div>
        </div>

        <div class="plan-col plan-col--right">
          <div class="panel" v-if="routeData">
            <div class="panel-title">路线结果</div>
            <div class="summary">
              <div>总距离：<span class="highlight">{{ formatDistance(routeData.total_distance) }} km</span></div>
              <div>途经景点数：<span class="highlight">{{ routeData.route.length }}</span></div>
              <div>目标城市：<span class="highlight">{{ routeData.target_city || targetCity }}</span></div>
              <div>起点：<span class="highlight">{{ startSpotName }}</span></div>
            </div>

            <div v-if="routeData.spot_reused" class="reuse-hint">
              ⚠️ 符合偏好景点数量不足，部分日期复用热门景点
            </div>

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
                    <template v-if="item.kind === 'spot'">
                      评分：{{ item.score }} ｜ 票价：{{ Number(item.price) > 0 ? item.price + '元' : '免费' }} ｜
                    </template>
                    第{{ item.day }}天
                  </div>
                </div>
              </div>
            </div>

            <el-divider content-position="left">配套酒店推荐</el-divider>
            <div class="hotel-recommend">
              <div v-if="hotelMarkers.length" class="hotel-list">
                <article
                  v-for="h in hotelMarkers"
                  :key="h.id"
                  class="hotel-item"
                  @click="goHotelDetail(h.id)"
                >
                  <div class="hotel-item-main">
                    <div class="hotel-item-name">{{ h.name }}</div>
                    <div class="hotel-item-addr">{{ h.address || '地址信息暂无' }}</div>
                  </div>
                  <div class="hotel-item-price">
                    ¥{{ formatMoney(h.price) }}<span class="unit">/晚</span>
                  </div>
                </article>
              </div>
              <div v-else class="hotel-empty">暂无配套推荐酒店</div>
            </div>

            <el-divider content-position="left">路线图</el-divider>
            <el-tabs v-model="routeView" class="route-view-tabs" @tab-change="onRouteViewChange">
              <el-tab-pane label="高德地图" name="map">
                <div v-show="mapVisible" class="map-wrap">
                  <div ref="mapRef" class="plan-map"></div>
                  <div class="map-legend">
                    <span class="legend-item"><i class="legend-dot legend-spot"></i>游览景点</span>
                    <span class="legend-item"><i class="legend-dot legend-hotel"></i>周边酒店</span>
                  </div>
                </div>
                <el-empty
                  v-if="!mapVisible"
                  description="地图暂不可用，可切换到“路线示意图”查看"
                  :image-size="60"
                />
              </el-tab-pane>
              <el-tab-pane label="路线示意图" name="chart">
                <div ref="chartRef" class="plan-chart"></div>
              </el-tab-pane>
            </el-tabs>

          </div>
          <el-empty v-else description="请填写偏好并生成智能行程" />
        </div>
      </div>
    </section>

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
import { createHotelOrder } from '@/api/hotel'
import { auth } from '@/utils/auth'
import HotelPicker from '@/components/hotel/HotelPicker.vue'
import { loadAMap } from '@/utils/amap'

defineOptions({ name: 'Plan' })

const router = useRouter()

// 缓存按登录用户隔离，避免同一标签页切换账号后串到别人的行程
const planCacheKey = () => `last_trip_plan_${auth.userId || 'guest'}`

// 按需注册 ECharts 模块（「路线示意图」Tab 使用）
echarts.use([GraphChart, GridComponent, TooltipComponent, CanvasRenderer])

const travelTypes = ['单人出行', '情侣出行', '家庭亲子', '老年休闲']
const prefOptions = ['自然风光', '人文古迹', '美食探店', '游乐乐园', '城市逛街', '徒步登山', '海滨海岛', '亲子出游']

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
// 每日游玩景点数量（1~4）
const perDay = ref(3)

const defaultHotelFilters = () => ({
  types: [],
  price: [0, 2000],
  minEnv: 0,
  minService: 0,
  features: []
})
const hotelFilters = ref(defaultHotelFilters())
const hotelResetSignal = ref(0)
// 回退恢复时把筛选条件一次性同步给酒店筛选组件（避免双向循环）
const hotelFilterSeed = ref(null)
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
// 酒店下拉的两套交互：
//   false = 尚未生成路线 -> 允许手动搜索任意酒店
//   true  = 已生成路线   -> 只允许选择本次行程返回的 hotel_markers（周边配套酒店）
const hasGeneratedRoute = ref(false)
const planName = ref('')
const saving = ref(false)

// 路线图区域两个 Tab：高德地图（真实道路）/ 路线示意图（ECharts 画布）
const routeView = ref('map')
const mapRef = ref(null)
// 地图仅在 SDK 加载成功且绘制成功时展示；任一环节失败（未配置 Key / 加载失败 / 驾车接口失败）都隐藏，保留文字路线
const mapVisible = ref(false)
const chartRef = ref(null)
let chartInstance = null
let amapApi = null
let mapInstance = null
let mapOverlays = []
let mapInfoWindow = null
let hotelInfoWindow = null
let drivingRouters = []
let mapRenderToken = 0
// Tab 未激活时不初始化（隐藏容器宽高为 0，初始化会得到错误尺寸），切回时再补渲染
let mapDirty = true
let chartDirty = true
let viewResizeHandler = null

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
// route_list 里带 price（免费景点为 0）
const routePriceMap = computed(() => {
  const map = {}
  ;(routeData.value?.route_list || []).forEach((item) => {
    map[item.id] = Number(item.price) || 0
  })
  return map
})

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
      price: routePriceMap.value[node.id] ?? 0,
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
      // 文字行程只渲染景点；酒店只在地图上打点，不进入日程列表
      if (node.node_type === 'hotel') return
      pushSpot(node)
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

// 后端返回的配套酒店（已按 40km 过滤）
const hotelMarkers = computed(() => routeData.value?.hotel_markers || [])

const goHotelDetail = (id) => {
  if (!id) return
  router.push(`/hotel-detail/${id}`)
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
      per_day: Number(perDay.value) || 3,
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
    sessionStorage.setItem(planCacheKey(), JSON.stringify(payload))
  } catch (e) {
    console.warn('[Plan] 保存会话缓存失败:', e?.message)
  }
}

const restorePlanCache = () => {
  try {
    const raw = sessionStorage.getItem(planCacheKey())
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
    hotelFilterSeed.value = {
      ...hotelFilters.value,
      _ts: Date.now()
    }
    perDay.value = Number(data.perDay) >= 1 && Number(data.perDay) <= 4 ? Number(data.perDay) : 3
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
    sessionStorage.removeItem(planCacheKey())
  } catch (e) {
    // ignore
  }
}

// 重新生成：先重置为“未生成路线”状态（酒店恢复可搜索），再重新请求行程
const handleRegenerate = async () => {
  hasGeneratedRoute.value = false
  await handleGenerate()
}

const handleGenerate = async () => {
  if (!(Number(perDay.value) >= 1 && Number(perDay.value) <= 4)) {
    ElMessage.warning('每日景点数量需在 1~4 之间')
    return
  }
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
  try {
    // 直接使用当前表单最新参数请求；成功后覆盖旧行程/nodes/预算，无需先重置
    const res = await api.post('/api/v1/trip/smart-recommend', {
      start_lat: startLat.value === '' ? null : Number(startLat.value),
      start_lng: startLng.value === '' ? null : Number(startLng.value),
      start_location: startLocation.value || undefined,
      target_city: targetCity.value.trim(),
      travel_type: travelType.value,
      preferences: preferences.value,
      days: days.value,
      per_day: perDay.value,
      hotel_per_day: null,
      ...buildHotelFilterPayload()
    })
    routeData.value = res.data
    // 生成成功 -> 进入“已生成路线”状态，酒店下拉锁定为本次行程配套酒店
    hasGeneratedRoute.value = true
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
    await nextTick()
    await renderRouteMap()
    renderRouteChart()
    savePlanCache()
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
  hotelFilterSeed.value = null
  hotelResetSignal.value += 1
  hotelPerDay.value = 300
  perDay.value = 3
  selectedHotelId.value = ''
  selectedHotel.value = null
  autoHotelApplied.value = false
  routeData.value = null
  // 重置路线 -> 回到“未生成路线”状态，酒店下拉恢复可搜索
  hasGeneratedRoute.value = false
  planName.value = ''
  generatedHotelPerDay.value = null
  savedTripId.value = null
  if (clearCache) clearPlanCache()
  mapRenderToken += 1
  destroyMap()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  mapDirty = true
  chartDirty = true
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
    const res = await createHotelOrder({
      hotel_id: selectedHotelId.value,
      check_in: bookingStart.value,
      check_out: bookingEnd.value,
      people_count: guestCount.value
    })
    ElMessage.success('预定成功，正在跳转支付')
    router.push(`/pay/${res.data.id}`)
  } catch (e) {
    const detail = String(e?.response?.data?.detail || '')
    if (e?.response?.status === 403 && (detail.includes('实名') || detail.includes('REAL_NAME_REQUIRED'))) {
      try {
        await ElMessageBox.confirm(
          '您还未完成实名认证，请前往个人中心完成实名后再预定酒店',
          '实名认证提示',
          { confirmButtonText: '去实名', cancelButtonText: '暂不', type: 'warning' }
        )
        router.push({ path: '/user', query: { tab: 'realname' } })
      } catch (err) {
        // 用户取消
      }
    } else {
      ElMessage.error(extractError(e, '提交预约失败'))
    }
  } finally {
    bookingSubmitting.value = false
  }
}

// ---------------------- 高德地图可视化（方案A：只做展示，不参与距离/预算） ----------------------
// AMap.Driving 单次最多 16 个途经点，故一段最多 = 起点 + 16 途经 + 终点
const AMAP_CHUNK_SIZE = 18

const escapeMarkup = (text) =>
  String(text ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[ch])

// 自绘 Marker：序号徽标 + 景点名，起点用绿色区分
const buildMarkerHtml = (badge, name, isStart) => {
  const bg = isStart ? '#67c23a' : '#ff7a2f'
  return (
    '<div style="display:flex;align-items:center;gap:6px;transform:translate(-50%,-100%);white-space:nowrap;">'
    + `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 4px;border-radius:11px;background:${bg};color:#fff;font-size:12px;font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,.3);">${escapeMarkup(badge)}</span>`
    + `<span style="font-size:12px;color:#303133;background:rgba(255,255,255,.92);padding:2px 6px;border-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.2);">${escapeMarkup(name)}</span>`
    + '</div>'
  )
}

const isValidCoord = (lng, lat) =>
  Number.isFinite(lng) && Number.isFinite(lat)
  && Math.abs(lat) <= 90 && Math.abs(lng) <= 180
  && !(lng === 0 && lat === 0)

// 酒店 Marker：蓝色房子图标，与橙色景点标记视觉区分（只打点，不进路线）
const buildHotelMarkerHtml = (name) => (
  '<div style="display:flex;flex-direction:column;align-items:center;transform:translate(-50%,-100%);white-space:nowrap;">'
  + '<svg width="26" height="30" viewBox="0 0 30 34" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
  + '<path d="M15 1C7.3 1 1 7.2 1 14.9c0 9.6 11.6 17.4 13.2 18.4a1.6 1.6 0 0 0 1.6 0C17.4 32.3 29 24.5 29 14.9 29 7.2 22.7 1 15 1z" fill="#3b82f6" stroke="#1d4ed8" stroke-width="1.6"/>'
  + '<path d="M9.4 14.6 15 9.7l5.6 4.9v6.1a.8.8 0 0 1-.8.8h-3.1v-3.9h-3.4v3.9h-3.1a.8.8 0 0 1-.8-.8z" fill="#fff"/>'
  + '</svg>'
  + `<span style="margin-top:2px;font-size:11px;color:#1d4ed8;background:rgba(255,255,255,.94);padding:1px 6px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.2);">${escapeMarkup(name)}</span>`
  + '</div>'
)

// 景点点位：优先使用后端 route_list（只含景点），兼容旧数据的 route；严格按返回顺序，不做重排
const buildSpotPoints = (data) => {
  const points = []
  const startLng = Number(data?.start_lng)
  const startLat = Number(data?.start_lat)
  const hasDeparture = data?.departure_distance !== null && data?.departure_distance !== undefined
  if (hasDeparture && isValidCoord(startLng, startLat)) {
    points.push({
      lng: startLng,
      lat: startLat,
      name: data?.start_location || startLocation.value || '出发地',
      badge: '起',
      isStart: true
    })
  }
  const spotList = Array.isArray(data?.route_list) && data.route_list.length
    ? data.route_list
    : (Array.isArray(data?.route) ? data.route : [])
  let seq = 0
  spotList.forEach((spot) => {
    const lng = Number(spot?.lng)
    const lat = Number(spot?.lat)
    if (!isValidCoord(lng, lat)) return
    seq += 1
    points.push({
      lng,
      lat,
      name: spot?.name || '景点',
      badge: String(seq),
      isStart: false
    })
  })
  return points
}

// 酒店点位：只用于地图打点，绝不参与路线连线 / 距离计算
const buildHotelPoints = (data) => {
  const list = Array.isArray(data?.hotel_markers) ? data.hotel_markers : []
  return list
    .map((hotel) => ({
      id: hotel?.id,
      name: hotel?.name || '酒店',
      lng: Number(hotel?.lng),
      lat: Number(hotel?.lat),
      price: Number(hotel?.price) || 0,
      description: String(hotel?.description || ''),
      address: String(hotel?.address || '')
    }))
    .filter((hotel) => isValidCoord(hotel.lng, hotel.lat))
}

// 酒店弹窗：名称 + 地址 + 简介 + 价格 + 查看详情按钮（点击跳转酒店详情页）
const openHotelInfoWindow = (hotel) => {
  if (!mapInstance || !amapApi) return
  if (!hotelInfoWindow) {
    hotelInfoWindow = new amapApi.InfoWindow({ offset: new amapApi.Pixel(0, -34), isCustom: true })
  }
  const box = document.createElement('div')
  box.style.cssText =
    'min-width:210px;max-width:260px;background:#fff;border:2px solid #222;border-radius:12px;'
    + 'padding:10px 12px;box-shadow:0 8px 20px rgba(0,0,0,.2);box-sizing:border-box;'
  const desc = hotel.description ? hotel.description.slice(0, 46) : '暂无简介'
  box.innerHTML =
    `<div style="font-size:14px;font-weight:800;color:#222;margin-bottom:2px;">${escapeMarkup(hotel.name)}</div>`
    + (hotel.address
      ? `<div style="font-size:11.5px;color:#7b8794;margin-bottom:4px;">${escapeMarkup(hotel.address)}</div>`
      : '')
    + `<div style="font-size:12px;color:#5a6472;line-height:1.5;margin-bottom:8px;">${escapeMarkup(desc)}</div>`
    + '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">'
    + `<span style="font-size:14px;font-weight:800;color:#f06818;">¥${hotel.price}<span style="font-size:11px;font-weight:500;color:#7b8794;">/晚</span></span>`
    + '<button type="button" style="border:none;background:#ff7a2f;color:#fff;font-size:12px;font-weight:700;padding:5px 10px;border-radius:8px;cursor:pointer;">查看酒店详情</button>'
    + '</div>'
  const detailBtn = box.querySelector('button')
  if (detailBtn) {
    detailBtn.addEventListener('click', () => {
      hotelInfoWindow.close()
      if (hotel.id) router.push(`/hotel-detail/${hotel.id}`)
    })
  }
  hotelInfoWindow.setContent(box)
  hotelInfoWindow.open(mapInstance, [hotel.lng, hotel.lat])
}

const clearMapOverlays = () => {
  if (hotelInfoWindow) {
    try {
      hotelInfoWindow.close()
    } catch (e) {
      // 地图已销毁时忽略
    }
  }
  if (mapInfoWindow) {
    try {
      mapInfoWindow.close()
    } catch (e) {
      // 地图已销毁时忽略
    }
  }
  drivingRouters.forEach((driving) => {
    try {
      driving.clear()
    } catch (e) {
      // 插件未就绪时忽略
    }
  })
  drivingRouters = []
  if (mapInstance && mapOverlays.length) {
    mapInstance.remove(mapOverlays)
  }
  mapOverlays = []
}

const destroyMap = () => {
  clearMapOverlays()
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
  if (mapInfoWindow) {
    mapInfoWindow = null
  }
  mapVisible.value = false
}

// ---------------- 路线示意图（ECharts，沿用改造前的画布坐标渲染逻辑） ----------------
const renderRouteChart = () => {
  if (routeView.value !== 'chart') {
    chartDirty = true
    return
  }
  const view = routeData.value
  if (!view) {
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
    chartDirty = false
    return
  }
  if (!chartRef.value) {
    chartDirty = true
    return
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  chartInstance = echarts.init(chartRef.value)

  const route = view.route || []
  const rawNodes = view.nodes || []

  // 路线图只渲染 spot 节点，hotel 节点不参与点位与连线
  const spotIds = [
    ...new Set(rawNodes.filter((node) => node.node_type === 'spot').map((node) => node.id))
  ]
  const orderedRoute = spotIds.length
    ? spotIds.map((id) => route.find((s) => s.id === id)).filter(Boolean)
    : route.slice()

  const graphNodes = orderedRoute.map((spot) => ({
    name: 'spot-' + spot.id,
    value: spot.name,
    x: spot.x,
    y: spot.y,
    symbolSize: 16,
    itemStyle: { color: '#67c23a' },
    label: { show: true, formatter: spot.name, position: 'right' }
  }))
  const links = []
  for (let i = 0; i < graphNodes.length - 1; i += 1) {
    links.push({ source: graphNodes[i].name, target: graphNodes[i + 1].name })
  }

  chartInstance.setOption({
    tooltip: {
      formatter: (params) => (params.dataType === 'node' ? params.value : '')
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
  })
  chartDirty = false
}

// 两个 Tab 都懒初始化：切到哪个就渲染哪个，切走后再切回来只做 resize
const onRouteViewChange = (name) => {
  nextTick(() => {
    if (name === 'map') {
      if (mapDirty || !mapInstance) {
        renderRouteMap()
      } else {
        mapInstance.resize()
        mapInstance.setFitView(null, false, [60, 60, 80, 60])
      }
    } else if (name === 'chart') {
      if (chartDirty || !chartInstance) {
        renderRouteChart()
      } else {
        chartInstance.resize()
      }
    }
  })
}

const bindViewResize = () => {
  if (viewResizeHandler) return
  viewResizeHandler = () => {
    if (chartInstance) chartInstance.resize()
    if (mapInstance) mapInstance.resize()
  }
  window.addEventListener('resize', viewResizeHandler)
}

// 按“原顺序”请求真实驾车路线；点位超过单次上限时按段切分，段与段共用端点保证连续
const drawDrivingRoute = (points) =>
  new Promise((resolve) => {
    if (points.length < 2) {
      resolve(true)
      return
    }
    const segments = []
    for (let i = 0; i < points.length - 1; i += AMAP_CHUNK_SIZE - 1) {
      segments.push(points.slice(i, i + AMAP_CHUNK_SIZE))
    }
    let pending = segments.length
    let allOk = true
    segments.forEach((segment) => {
      const origin = new amapApi.LngLat(segment[0].lng, segment[0].lat)
      const destination = new amapApi.LngLat(segment[segment.length - 1].lng, segment[segment.length - 1].lat)
      const waypoints = segment.slice(1, -1).map((p) => new amapApi.LngLat(p.lng, p.lat))
      const driving = new amapApi.Driving({
        map: mapInstance,
        hideMarkers: true,
        showTraffic: false,
        autoFitView: false
      })
      drivingRouters.push(driving)
      // optimize: false —— 关闭高德自带的途经点顺序优化，严格按后端算法输出的顺序画线
      driving.search(origin, destination, { waypoints, optimize: false }, (status, result) => {
        if (status !== 'complete' || !result) allOk = false
        pending -= 1
        if (pending === 0) resolve(allOk)
      })
    })
  })

const renderRouteMap = async () => {
  const token = ++mapRenderToken
  clearMapOverlays()
  // 每次刷新先清空所有 marker / 折线，再按两类点位分别渲染
  const spotPoints = buildSpotPoints(routeData.value)
  const hotelPoints = buildHotelPoints(routeData.value)
  const anchorPoint = spotPoints[0] || hotelPoints[0]
  if (!anchorPoint) {
    destroyMap()
    mapDirty = false
    return
  }
  // 地图 Tab 未激活时先挂起，避免在 0 尺寸容器里初始化
  if (routeView.value !== 'map') {
    mapDirty = true
    return
  }
  try {
    amapApi = amapApi || (await loadAMap())
    if (token !== mapRenderToken) return
    mapVisible.value = true
    await nextTick()
    if (token !== mapRenderToken || !mapRef.value) return
    if (!mapInstance) {
      mapInstance = new amapApi.Map(mapRef.value, {
        zoom: 11,
        center: [anchorPoint.lng, anchorPoint.lat],
        resizeEnable: true,
        dragEnable: true,
        scrollWheel: true,
        doubleClickZoom: true
      })
    }
    if (!mapInfoWindow) {
      mapInfoWindow = new amapApi.InfoWindow({ offset: new amapApi.Pixel(0, -32), isCustom: false })
    }
    // 重新生成时先清空旧 Marker / 旧轨迹，再绘制新内容
    clearMapOverlays()

    // ① 景点（橙色）：参与路线
    const spotMarkers = spotPoints.map((point, index) => {
      const marker = new amapApi.Marker({
        position: [point.lng, point.lat],
        content: buildMarkerHtml(point.badge, point.name, point.isStart),
        offset: new amapApi.Pixel(0, 0),
        zIndex: 120 + index,
        title: (point.isStart ? '起点·' : `第${point.badge}站·`) + point.name,
        bubble: true
      })
      // 悬浮气泡显示点位名称
      marker.on('mouseover', () => {
        if (!mapInstance || !mapInfoWindow) return
        const label = point.isStart ? `起点 · ${point.name}` : `第${point.badge}站 · ${point.name}`
        mapInfoWindow.setContent(
          `<div style="padding:2px 6px;font-size:12px;line-height:18px;color:#303133;">${escapeMarkup(label)}</div>`
        )
        mapInfoWindow.open(mapInstance, [point.lng, point.lat])
      })
      marker.on('mouseout', () => {
        if (mapInfoWindow) mapInfoWindow.close()
      })
      marker.setMap(mapInstance)
      return marker
    })

    // ② 酒店（蓝色房子）：只打点，不进入 drawDrivingRoute 的坐标数组
    const hotelMarkers = hotelPoints.map((hotel, index) => {
      const marker = new amapApi.Marker({
        position: [hotel.lng, hotel.lat],
        content: buildHotelMarkerHtml(hotel.name),
        offset: new amapApi.Pixel(0, 0),
        zIndex: 200 + index,
        title: `酒店·${hotel.name}`,
        bubble: true
      })
      marker.on('click', () => openHotelInfoWindow(hotel))
      marker.setMap(mapInstance)
      return marker
    })

    mapOverlays = [...spotMarkers, ...hotelMarkers]
    // 折线只串联景点（route_list 顺序）；酒店从不参与连线
    const ok = spotPoints.length > 1 ? await drawDrivingRoute(spotPoints) : true
    if (token !== mapRenderToken) return
    // 高德返回的里程全部丢弃，只用它画轨迹
    if (!ok) throw new Error('驾车路线请求失败')
    mapInstance.setFitView(null, false, [60, 60, 80, 60])
    mapDirty = false
  } catch (e) {
    console.warn('[Plan] 高德地图渲染失败，已隐藏地图:', e?.message || e)
    if (token === mapRenderToken) {
      destroyMap()
      mapDirty = false
    }
  }
}

// 导出当前路线为 JSON 文件（纯前端下载，不新增/不调用任何接口）
const exportRoute = () => {
  if (!routeData.value) return
  const name = (planName.value || '').trim() || '智能路线规划'
  const payload = {
    name,
    exported_at: new Date().toISOString(),
    start_location: startLocation.value || null,
    start_lat: startLat.value === '' ? null : Number(startLat.value),
    start_lng: startLng.value === '' ? null : Number(startLng.value),
    target_city: routeData.value.target_city || targetCity.value,
    total_distance: routeData.value.total_distance,
    budget: routeData.value.budget,
    route: (routeData.value.route || []).map((spot) => ({
      order: spot.order,
      name: spot.name,
      city: spot.city,
      lng: spot.lng,
      lat: spot.lat
    })),
    legs: routeData.value.legs,
    day_plans: routeData.value.day_plans
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name + '.json'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('路线已导出')
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

// 路线图只画景点，手动切换酒店无需重绘地图（列表与预算由 timeline/refreshBudgetHotel 更新）

// 离开规划页（详情页 / 实名页 / 支付页 / 其他）都写入缓存，保证浏览器回退可恢复
onBeforeRouteLeave(() => {
  savePlanCache()
})

onMounted(() => {
  bindViewResize()
})

onActivated(() => {
  // 返回规划页时优先读取缓存回填，不自动清空表单
  if (restorePlanCache()) {
    nextTick(() => {
      if (routeData.value) {
        renderRouteMap()
        renderRouteChart()
      }
    })
  } else if (routeData.value) {
    nextTick(() => {
      renderRouteMap()
      renderRouteChart()
    })
  }
})

onBeforeUnmount(() => {
  mapRenderToken += 1
  destroyMap()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  if (viewResizeHandler) {
    window.removeEventListener('resize', viewResizeHandler)
    viewResizeHandler = null
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
  color: #f06818;
  font-weight: 700;
}
.reuse-hint {
  margin-top: 10px;
  color: #909399;
  font-size: 12px;
  background: #f7f8fa;
  border-radius: 4px;
  padding: 8px 10px;
}
.route-view-tabs {
  margin-top: 16px;
}
.plan-map {
  width: 100%;
  height: 420px;
  border-radius: 12px;
  overflow: hidden;
}
.plan-chart {
  width: 100%;
  height: 420px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
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
.hotel-recommend {
  border: 2px solid #222;
  border-radius: 10px;
  background: #fff;
  padding: 8px;
}
.hotel-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.hotel-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(34, 34, 34, 0.14);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}
.hotel-item:hover {
  background: #fff7ef;
  border-color: #222;
  transform: translateY(-1px);
}
.hotel-item-main {
  min-width: 0;
}
.hotel-item-name {
  font-size: 14px;
  font-weight: 700;
  color: #222;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hotel-item-addr {
  margin-top: 2px;
  font-size: 12px;
  color: #7b8794;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hotel-item-price {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 800;
  color: #f06818;
}
.hotel-item-price .unit {
  font-size: 11px;
  font-weight: 500;
  color: #7b8794;
}
.hotel-empty {
  padding: 14px 0;
  text-align: center;
  font-size: 13px;
  color: #909399;
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

/* ================= TR 主题适配（仅样式，逻辑未动） ================= */
.plan {
  max-width: 1320px;
  margin: 0 auto;
  padding-bottom: 24px;
  background: transparent;
}
.page-card {
  padding: 20px 22px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 18px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.page-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.page-heading .tr-section-title {
  margin: 0;
}
.page-search {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-search :deep(.el-input) {
  width: 260px;
}
.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 0 16px;
  margin-bottom: 6px;
  border-top: 1px dashed rgba(34, 34, 34, 0.12);
}
.action-bar .plan-name-input {
  width: 210px;
  margin-left: auto;
}
.plan > :deep(.el-card) {
  border: 2px solid #222;
  border-radius: 16px;
}
.panel {
  border: 2px solid #222;
  border-radius: 14px;
  background: #fff;
  box-shadow: 3px 3px 0 rgba(34, 34, 34, 0.1);
}
.panel-title {
  font-size: 15px;
  font-weight: 800;
  color: #222;
}
.section-label {
  color: #5a6472;
  font-weight: 600;
}
.coord-tip {
  color: #f06818;
  font-weight: 600;
}
.timeline-content {
  background: #fff;
  border: 2px solid #222;
  border-radius: 12px;
  padding: 10px 12px;
  box-shadow: 2px 2px 0 rgba(34, 34, 34, 0.08);
}
.timeline-content:hover {
  background: #fff7ef;
}
.timeline-title {
  font-weight: 700;
  color: #222;
}
.timeline-meta {
  color: #7b8794;
}
.timeline-dot {
  border: 2px solid #222;
}
.timeline-dot.spot {
  background: #ff7a2f;
}
.timeline-dot.hotel {
  background: #4aa3ff;
}
.reuse-hint {
  border: 1px dashed rgba(34, 34, 34, 0.18);
  background: #f7fbff;
}
.plan-map,
.plan-chart {
  border: 2px solid #222;
  border-radius: 14px;
}
.plan-map {
  background: #f7fbff;
}

/* ===== 地图图例（右下角）：橙色=景点，蓝色房子=酒店 ===== */
.map-wrap {
  position: relative;
}
.map-legend {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.94);
  border: 2px solid #222;
  border-radius: 10px;
  font-size: 12px;
  color: #222;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.legend-spot {
  background: #ff7a2f;
}
.legend-hotel {
  background: #3b82f6;
  border-radius: 3px;
}

/* ==================================================================
   v0.15 布局防爆框：1440 容器 + 350px/1fr 两栏 + 控件 100% 自适应
   仅样式，未改动任何业务逻辑
   ================================================================== */
.plan {
  max-width: 1440px;
  margin: 0 auto;
  padding: 16px;
  box-sizing: border-box;
}
.page-card {
  padding: 16px;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(34, 34, 34, 0.08);
  box-sizing: border-box;
}

/* 两栏：左侧固定 350px，右侧自适应；窄屏自动堆叠 */
.plan-grid {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.plan-col {
  min-width: 0;
}
@media (max-width: 1080px) {
  .plan-grid {
    grid-template-columns: 1fr;
  }
}

/* ================= 左侧偏好面板 ================= */
.panel {
  padding: 16px;
  border-radius: 10px;
  box-shadow: 0 6px 16px rgba(34, 34, 34, 0.08);
  min-width: 0;
  box-sizing: border-box;
}
.panel-title {
  font-size: 18px;
  margin-bottom: 12px;
}
.section-label {
  font-size: 13px;
  margin-bottom: 6px;
}
.form-block {
  margin-bottom: 14px;
}
.panel :deep(.el-input),
.panel :deep(.el-select),
.panel :deep(.el-date-editor),
.panel :deep(.el-slider) {
  width: 100%;
  box-sizing: border-box;
}
.panel :deep(.el-form-item) {
  margin-bottom: 12px;
}
.panel :deep(.el-form-item__label) {
  font-size: 13px;
}
.panel :deep(.el-form-item__content) {
  min-width: 0;
}

/* 出发位置 / 目标城市：输入框弹性收缩，不撑破 350px */
.start-location-row,
.target-city-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.start-city-input {
  flex: 1 1 150px;
  min-width: 0;
}
.target-city-row :deep(.el-input) {
  flex: 1 1 150px;
  min-width: 0;
}

/* 标签组：自动换行 + 6px 间距 */
.type-group,
.pref-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.type-group :deep(.el-radio-button__inner),
.pref-group :deep(.el-checkbox-button__inner) {
  padding: 6px 10px;
  font-size: 13px;
}
.days-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.days-section :deep(.el-input-number) {
  width: 110px;
}
.field-hint {
  margin: -8px 0 14px;
  font-size: 12px;
  color: #909399;
}

/* ================= 酒店预订板块 ================= */
.hotel-block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(34, 34, 34, 0.12);
  min-width: 0;
}
.booking-block {
  min-width: 0;
}
.booking-block :deep(.el-date-editor) {
  width: 100%;
}
.booking-block :deep(.el-input-number) {
  width: 110px;
}

/* 酒店筛选（HotelFilter 组件内部，需要 :deep） */
.panel :deep(.hotel-filter) {
  width: 100%;
  padding: 10px;
  border-radius: 10px;
  box-sizing: border-box;
  gap: 8px;
}
.panel :deep(.filter-row) {
  gap: 8px;
  min-width: 0;
}
.panel :deep(.filter-label) {
  width: 58px;
  font-size: 13px;
}
.panel :deep(.filter-tags) {
  gap: 6px;
  min-width: 0;
}
.panel :deep(.filter-tags .el-checkbox-button__inner) {
  padding: 4px 8px;
  font-size: 12px;
}
.panel :deep(.price-slider) {
  gap: 8px;
  min-width: 0;
}
.panel :deep(.price-slider .el-slider) {
  flex: 1;
  min-width: 0;
}
.panel :deep(.price-text) {
  font-size: 12px;
}
.panel :deep(.score-inputs) {
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
}
.panel :deep(.filter-row--score) {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.panel :deep(.filter-row--score .filter-label) {
  width: auto;
}

/* ================= 右侧路线结果 ================= */
.plan-col--right,
.plan-col--right > .panel {
  min-width: 0;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  font-size: 14px;
}
.timeline-row {
  min-width: 0;
}
.timeline-content {
  min-width: 0;
  overflow: hidden;
  border-radius: 10px;
}
.timeline-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.timeline-meta {
  font-size: 13px;
}

/* ================= 地图 / 图表防溢出 ================= */
.route-view-tabs {
  margin-top: 12px;
}
.plan-chart,
.plan-map {
  border-radius: 10px;
  overflow: hidden;
  box-sizing: border-box;
}
.map-wrap {
  overflow: hidden;
  border-radius: 10px;
  max-width: 100%;
}
.plan-map {
  height: 420px;
  width: 100%;
  box-sizing: border-box;
}
/* 强制高德根容器与 canvas 撑满父级，不再溢出 */
.plan-map :deep(.amap-container),
.plan-map :deep(.amap-maps),
.plan-map :deep(.amap-maps > div) {
  width: 100% !important;
  height: 100% !important;
}
.plan-map :deep(.amap-container canvas) {
  max-width: 100%;
}

/* ================= 按钮尺寸统一 ================= */
.action-bar :deep(.el-button) {
  padding: 6px 14px;
}
</style>
