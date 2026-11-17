<template>
  <div class="plan layout3">
    <!-- ===== 左栏：Agent 任务会话 + 底部提问框 ===== -->
    <aside class="col-tasks">
      <div class="tasks-head">
        <span class="tasks-title">Agent 任务</span>
        <el-button class="tasks-add" size="small" circle @click="createTask">+</el-button>
      </div>

      <div class="task-list">
        <div
          v-for="t in tasks"
          :key="t.id"
          class="task-item"
          :class="{ active: t.id === currentTaskId }"
          @click="switchTask(t.id)"
        >
          <div class="task-name">{{ t.title }}</div>
          <div class="task-sub">{{ t.updatedAt }} · {{ t.messages.length }} 条</div>
        </div>
      </div>

    </aside>

    <!-- ===== 中栏：主对话区（可滚动） ===== -->
    <main class="col-chat">
      <div class="chat-head">
        <div>
          <div class="chat-title">AI 行程助手</div>
          <div class="chat-sub">Agent 会先查真实景点，再生成路线并自检</div>
        </div>
        <el-button text class="chat-new" @click="createTask">新对话</el-button>
      </div>

      <!-- 操作按钮行：保留原有生成/保存/导出能力 -->
      <div class="chat-toolbar">
        <el-button size="small" type="primary" :loading="generating" @click="handleGenerate()">生成路线</el-button>
        <el-button size="small" :disabled="!routeData" @click="handleRegenerate">重新生成</el-button>
        <el-button size="small" :disabled="!routeData" :loading="saving" @click="handleSave">保存</el-button>
        <el-button size="small" :disabled="!routeData" @click="exportRoute">导出</el-button>
        <el-button size="small" text @click="handleReset">重置</el-button>
        <el-input v-model="planName" size="small" class="plan-name-input" placeholder="路线名称（保存用）" />
      </div>

      <!-- 偏好快照：默认一行展示，可展开编辑 -->
      <div class="pref-bar">
        <div class="pref-line" @click="prefOpen = !prefOpen">
          <span class="pref-title">偏好快照</span>
          <span class="pref-summary">{{ prefSummary }}</span>
          <span class="pref-toggle">{{ prefOpen ? '收起' : '展开' }}</span>
        </div>
        <div v-show="prefOpen" class="pref-body">
          <div class="pref-grid">
            <div class="pref-field">
              <div class="field-label">出发位置</div>
              <div class="start-location-row">
                <el-input v-model="startLocation" placeholder="如：惠州" clearable />
                <el-button @click="openMapPicker">地图选点</el-button>
              </div>
              <div v-if="startLat && startLng" class="coord-tip">已选取：{{ startLat }}, {{ startLng }}</div>
            </div>
            <div class="pref-field">
              <div class="field-label">目标地区（单城市）</div>
              <el-input v-model="targetCity" placeholder="如：广州" clearable @keyup.enter="handleGenerate()" />
            </div>
          </div>

          <div class="pref-field">
            <div class="field-label">出行类型</div>
            <el-radio-group v-model="travelType" class="type-group">
              <el-radio-button v-for="t in travelTypes" :key="t" :value="t">{{ t }}</el-radio-button>
            </el-radio-group>
          </div>

          <div class="pref-field">
            <div class="field-label">游玩偏好（可多选）</div>
            <el-checkbox-group v-model="preferences" class="pref-group">
              <el-checkbox-button v-for="p in prefOptions" :key="p" :value="p">{{ p }}</el-checkbox-button>
            </el-checkbox-group>
          </div>

          <div class="pref-grid">
            <div class="pref-field pref-field--num">
              <div class="field-label">游玩天数</div>
              <el-input-number v-model="days" :min="1" :max="10" />
            </div>
            <div class="pref-field pref-field--num">
              <div class="field-label">每日景点</div>
              <el-input-number v-model="perDay" :min="1" :max="4" :step="1" />
            </div>
          </div>

        </div>
      </div>

      <!-- 消息流滚动区：chat-flow 为滚动容器；chat-lead 负责把内容压到中下部 -->
      <div ref="messageListRef" class="chat-flow">
        <div class="chat-lead"></div>
        <div v-for="m in currentMessages" :key="m.id" class="msg-row" :class="m.role">
          <div class="msg-avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
          <div class="msg-bubble">
            <div class="msg-text" :class="{ typing: m.typing }" v-html="renderMessage(m.content)"></div>
            <div v-if="m.tools && m.tools.length" class="msg-tools">
              <span v-for="(t, ti) in m.tools" :key="ti" class="tool-chip">{{ toolLabel(t) }}</span>
            </div>
          </div>
        </div>

        <div v-if="agentSending" class="msg-row assistant">
          <div class="msg-avatar">AI</div>
          <div class="msg-bubble"><span class="msg-loading">正在查询景点 / 生成路线 / 自检…</span></div>
        </div>

        <!-- 路线卡片：地图内嵌在 AI 消息区域内 -->
        <div v-if="routeData" class="route-card">
          <div class="route-summary">
            <div><span class="k">总距离</span><span class="v">{{ formatDistance(routeData.total_distance) }} km</span></div>
            <div><span class="k">景点数</span><span class="v">{{ routeData.route.length }}</span></div>
            <div><span class="k">目标城市</span><span class="v">{{ routeData.target_city || targetCity }}</span></div>
            <div><span class="k">起点</span><span class="v">{{ startSpotName }}</span></div>
          </div>

          <div v-if="routeData.tips" class="route-tips">{{ routeData.tips }}</div>

          <el-tabs v-model="routeView" class="route-view-tabs" @tab-change="onRouteViewChange">
            <el-tab-pane label="高德地图" name="map">
              <div v-show="mapVisible" class="map-wrap">
                <div ref="mapRef" class="plan-map"></div>
                <div class="map-legend">
                  <span class="legend-item"><i class="legend-dot legend-spot"></i>游览景点</span>
                  <span class="legend-item"><i class="legend-dot legend-hotel"></i>周边酒店</span>
                </div>
              </div>
              <div v-if="!mapVisible" class="map-fallback">
                  <el-empty description="地图暂不可用，可切换到“路线示意图”查看" :image-size="60" />
                  <div v-if="mapError" class="map-error">{{ mapError }}</div>
                  <el-button size="small" @click="retryMap">重试加载地图</el-button>
                </div>
            </el-tab-pane>
            <el-tab-pane label="路线示意图" name="chart">
              <div ref="chartRef" class="plan-chart"></div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <el-empty
          v-if="!currentMessages.length && !routeData"
          description="输入出行需求，Agent 会先查景点再生成路线"
        />
      </div>

      <!-- 底部固定提问区（由左栏迁移而来，宽度与消息流对齐） -->
      <div class="chat-composer">
        <el-input
          v-model="aiMessage"
          type="textarea"
          :rows="2"
          resize="none"
          maxlength="200"
          placeholder="描述需求，例如：广州两天，喜欢爬山和美食"
          @keydown.enter.exact.prevent="sendAgentMessage"
        />
        <el-button type="primary" class="composer-send" :loading="agentSending" @click="sendAgentMessage">
          发送
        </el-button>
      </div>
    </main>

    <!-- ===== 右栏：Agent 工作台 ===== -->
    <aside class="col-workbench">
      <section class="wb-card">
        <div class="wb-title">任务关键词</div>
        <div class="wb-chips">
          <span v-for="k in workbenchKeywords" :key="k" class="wb-chip">{{ k }}</span>
          <span v-if="!workbenchKeywords.length" class="wb-empty">暂无</span>
        </div>
      </section>

      <section class="wb-card">
        <div class="wb-title">景点卡片</div>
        <div class="card-list">
          <div v-for="s in spotCards" :key="'s' + s.id" class="mini-card" @click="goSpotDetail(s.id)">
            <div class="mini-name"><span class="mini-tag spot">景点</span>{{ s.name }}</div>
            <div class="mini-meta">评分 {{ s.score ?? '-' }}</div>
          </div>
          <div v-if="!spotCards.length" class="wb-empty">生成路线后展示</div>
        </div>
      </section>

      <section class="wb-card">
        <div class="wb-title">酒店卡片</div>
        <div class="card-list">
          <div v-for="h in hotelCards" :key="'h' + h.id" class="mini-card" @click="goHotelDetail(h.id)">
            <div class="mini-name"><span class="mini-tag hotel">酒店</span>{{ h.name }}</div>
            <div class="mini-meta">¥{{ formatMoney(h.price) }}</div>
          </div>
          <div v-if="!hotelCards.length" class="wb-empty">暂无推荐酒店</div>
        </div>
      </section>

      <el-button class="graph-btn" @click="openGraph">图谱可视化</el-button>
    </aside>

    <!-- 图谱弹窗 -->
    <el-dialog v-model="graphVisible" title="知识图谱（关键词 / 景点 / 酒店）" width="760px">
      <div ref="graphRef" class="graph-canvas"></div>
    </el-dialog>

    <!-- 原地图选点弹窗 -->
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

// AI 一句话规划：原始句子、解析状态、解析回执、行程说明与“当前参数来自 AI”标记
const aiMessage = ref('')
const aiNote = ref('')
const aiNoteLoading = ref(false)
const aiFilled = ref(false)

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
// 地图失败原因（展示给用户，便于排查 Key/网络/容器问题）
const mapError = ref('')
let mapResizeObserver = null
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

// ===== 多步 Agent 对话 =====
const agentMessages = ref([])
const agentSending = ref(false)
const agentSessionId = ref('')
// Agent 重排时排除的景点：前端复算路线必须带上，否则会与 Agent 回复不一致
const agentExcludeSpots = ref([])

// 把 Agent 解析出的参数回填到左侧表单（复用原有字段）
const applyAgentParams = (params) => {
  if (!params) return
  if (params.target_city) targetCity.value = params.target_city
  const parsedDays = Number(params.days)
  if (Number.isFinite(parsedDays) && parsedDays >= 1) days.value = Math.min(10, Math.round(parsedDays))
  const parsedPerDay = Number(params.per_day)
  if (Number.isFinite(parsedPerDay) && parsedPerDay >= 1) perDay.value = Math.min(4, Math.round(parsedPerDay))
  if (Array.isArray(params.preferences)) preferences.value = [...params.preferences]
  if (params.travel_type && travelTypes.includes(params.travel_type)) travelType.value = params.travel_type
  if (params.start_location) startLocation.value = params.start_location
  agentExcludeSpots.value = Array.isArray(params.exclude_spots) ? [...params.exclude_spots] : []
  aiFilled.value = true
}

const sendAgentMessage = async () => {
  const text = String(aiMessage.value || '').trim()
  if (!text) {
    ElMessage.warning('请输入你的出行需求')
    return
  }
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  agentMessages.value.push({ role: 'user', content: text, tools: [] })
  aiMessage.value = ''
  agentSending.value = true
  try {
    // Agent 多步工具调用耗时可能超过全局 10s 超时，这里单独放宽到 180s
    const res = await api.post('/api/v1/ai/agent/plan', {
      message: text,
      session_id: agentSessionId.value || undefined
    }, { timeout: 180000 })
    const data = res.data || {}
    agentSessionId.value = data.session_id || agentSessionId.value
    const trace = Array.isArray(data.trace) ? data.trace : []
    // 本轮自检结果：用于消息内展示，并作为工作台“旅行提示”实体来源
    lastSelfCheck.value = data.self_check || null
    const fullReply = data.reply || '已处理'
    const replyMsg = {
      role: 'assistant',
      content: '',
      full: fullReply,
      typing: true,
      tools: trace.map((t) => t.tool).filter((name, idx, arr) => arr.indexOf(name) === idx),
      selfCheck: data.self_check || null,
      conflicts: Array.isArray(data.conflicts) ? data.conflicts : [],
      degraded: !!data.degraded
    }
    agentMessages.value.push(replyMsg)
    if (data.degraded) ElMessage.warning('AI 服务降级：已使用关键词解析')

    // 任务标题取首条用户消息；更新任务时间
    const task = currentTask.value
    if (task) {
      const firstUser = task.messages.find((m) => m.role === 'user')
      task.title = (firstUser?.content || text).slice(0, 18)
      task.updatedAt = nowLabel()
      task.sessionId = agentSessionId.value
    }

    const params = data.params || {}
    // 路线生成与文字流式输出并行：文字逐字出现，路线卡片就绪后自动插入
    const generatePromise = params.target_city
      ? (applyAgentParams(params), handleGenerate({ intro: false }))
      : Promise.resolve()
    await typewriter(replyMsg, fullReply)
    await generatePromise
    if (task && params.target_city) task.routeData = routeData.value
    scrollToBottom()
  } catch (e) {
    agentMessages.value.push({ role: 'assistant', content: 'AI 助手暂时不可用，请重试或手动填写表单', tools: [] })
    ElMessage.error(extractError(e, 'AI 助手请求失败'))
  } finally {
    agentSending.value = false
    scrollToBottom()
  }
}

const newAgentChat = async () => {
  const sid = agentSessionId.value
  agentMessages.value = []
  agentSessionId.value = ''
  if (!sid) return
  try {
    await api.post('/api/v1/ai/agent/reset', { session_id: sid })
  } catch (e) {
    // 清空失败不影响本地新对话
  }
}

// ===== 控制台布局：任务列表 / 工作台 / 实体高亮 / 图谱 =====
const prefOpen = ref(false)
const workbenchCollapsed = ref(false)
const routeDetailOpen = ref(true)
const messageListRef = ref(null)
const graphVisible = ref(false)
const graphRef = ref(null)
const lastSelfCheck = ref(null)
let graphInstance = null

const nowLabel = () =>
  new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

const makeTask = (title = '新的规划任务') => ({
  id: `task-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`,
  title,
  messages: [],
  sessionId: '',
  routeData: null,
  updatedAt: nowLabel()
})

const tasks = ref([makeTask()])
const currentTaskId = ref(tasks.value[0].id)
const currentTask = computed(
  () => tasks.value.find((t) => t.id === currentTaskId.value) || tasks.value[0]
)
const currentMessages = computed(() => currentTask.value?.messages || [])
// 重要：agentMessages 直接绑定当前任务的 messages 数组，保证原有 push 逻辑自动同步
agentMessages.value = currentTask.value.messages

const prefSummary = computed(() => {
  const pref = (preferences.value || []).join('/') || '未选偏好'
  const city = targetCity.value?.trim() || '未选城市'
  return `${city} · ${days.value}天 · 每天${perDay.value}个 · ${pref}`
})

// 工作台：关键词 / 实体 / 卡片
const spotCards = computed(() =>
  (routeData.value?.route || []).map((r) => ({
    id: r.id,
    name: r.name,
    score: r.score,
    city: r.city
  }))
)
const hotelCards = computed(() =>
  (routeData.value?.hotel_markers || []).map((h) => ({
    id: h.id,
    name: h.name,
    price: h.price,
    address: h.address
  }))
)
const workbenchKeywords = computed(() => {
  const set = new Set()
  if (targetCity.value) set.add(targetCity.value.trim())
  ;(preferences.value || []).forEach((p) => set.add(p))
  if (travelType.value) set.add(travelType.value)
  set.add(`${days.value}天`)
  set.add(`每天${perDay.value}个`)
  return Array.from(set).slice(0, 10)
})
const workbenchEntities = computed(() => {
  const list = []
  spotCards.value.forEach((s) =>
    list.push({ key: `spot-${s.id}`, type: 'spot', typeLabel: '景点', name: s.name, id: s.id })
  )
  hotelCards.value.forEach((h) =>
    list.push({ key: `hotel-${h.id}`, type: 'hotel', typeLabel: '酒店', name: h.name, id: h.id })
  )
  ;((lastSelfCheck.value?.issues_text) || []).slice(0, 2).forEach((text, i) =>
    list.push({ key: `tip-${i}`, type: 'tip', typeLabel: '提示', name: text, id: null })
  )
  return list
})

// 实体高亮：把文本中的景点/酒店名包成带下划线的 span（先转义再替换，避免 XSS）
const escapeHtml = (text) =>
  String(text || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
const escapeReg = (text) => String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const renderMessage = (text) => {
  const safe = escapeHtml(text)
  const names = [...spotCards.value.map((s) => s.name), ...hotelCards.value.map((h) => h.name)]
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .slice(0, 80)
  let html = safe
  if (names.length) {
    const pattern = new RegExp(`(${names.map(escapeReg).join('|')})`, 'g')
    html = html.replace(pattern, '<span class="entity-hl">$1</span>')
  }
  // 轻量清洗模型偶发的 Markdown 标记，避免页面出现 #、** 等符号
  html = html
    .replace(/^\s*#{1,6}\s*/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\s*[-*]\s+/gm, '• ')
  return html.replace(/\n/g, '<br/>')
}

const TOOL_LABELS = {
  search_spots: '查景点',
  make_route: '生成路线',
  critique_route: '路线自检',
  search_hotels: '查酒店',
  search_knowledge: '知识检索',
  degraded: '关键词解析'
}
const toolLabel = (name) => TOOL_LABELS[name] || name

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight
}

// 打字机效果：把完整回复逐字写入消息，形成“从上往下生成”的流式观感
const typewriter = (msg, full) =>
  new Promise((resolve) => {
    msg.content = ''
    msg.typing = true
    let i = 0
    const tick = () => {
      i = Math.min(full.length, i + 2 + Math.floor(Math.random() * 2))
      msg.content = full.slice(0, i)
      if (i % 24 === 0) scrollToBottom()
      if (i < full.length) {
        setTimeout(tick, 14)
      } else {
        msg.typing = false
        scrollToBottom()
        resolve()
      }
    }
    tick()
  })

const switchTask = (id) => {
  if (id === currentTaskId.value) return
  // 保存当前会话状态到旧任务
  const old = currentTask.value
  if (old) {
    old.sessionId = agentSessionId.value
    old.routeData = routeData.value
  }
  currentTaskId.value = id
  const task = currentTask.value
  agentMessages.value = task.messages
  agentSessionId.value = task.sessionId || ''
  routeData.value = task.routeData || null
  scrollToBottom()
  // 切回历史任务时重绘地图/示意图（地图容器随路线卡片重新挂载）
  if (routeData.value) {
    nextTick(() => {
      renderRouteMap()
      renderRouteChart()
    })
  }
}

const createTask = async () => {
  const sid = agentSessionId.value
  if (sid) {
    try {
      await api.post('/api/v1/ai/agent/reset', { session_id: sid })
    } catch (e) {
      // 清空失败不影响本地新任务
    }
  }
  const task = makeTask()
  tasks.value.unshift(task)
  currentTaskId.value = task.id
  agentMessages.value = task.messages
  agentSessionId.value = ''
  routeData.value = null
  hasGeneratedRoute.value = false
  lastSelfCheck.value = null
}

const goSpotDetail = (id) => {
  if (id) router.push(`/spot-detail/${id}`)
}

const openEntity = (entity) => {
  if (entity.type === 'spot') goSpotDetail(entity.id)
  else if (entity.type === 'hotel') goHotelDetail(entity.id)
}

// 图谱可视化：关键词为中心，连接景点/酒店实体
const buildGraph = () => {
  if (!graphRef.value) return
  if (!graphInstance) graphInstance = echarts.init(graphRef.value)
  const nodes = []
  const links = []
  const keywordNodes = workbenchKeywords.value.slice(0, 5)
  keywordNodes.forEach((k, i) => {
    nodes.push({ id: `k${i}`, name: k, category: 0, symbolSize: 34 })
  })
  spotCards.value.slice(0, 8).forEach((s, i) => {
    nodes.push({ id: `s${i}`, name: s.name, category: 1, symbolSize: 26 })
    if (keywordNodes.length) links.push({ source: `k${i % keywordNodes.length}`, target: `s${i}` })
  })
  hotelCards.value.slice(0, 6).forEach((h, i) => {
    nodes.push({ id: `h${i}`, name: h.name, category: 2, symbolSize: 22 })
    if (keywordNodes.length) links.push({ source: `k${i % keywordNodes.length}`, target: `h${i}` })
  })
  graphInstance.setOption({
    backgroundColor: 'transparent',
    legend: [{ data: ['关键词', '景点', '酒店'], textStyle: { color: '#c7d2da' }, top: 0 }],
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        label: { show: true, color: '#e6edf3', fontSize: 11 },
        force: { repulsion: 220, edgeLength: 90 },
        categories: [{ name: '关键词' }, { name: '景点' }, { name: '酒店' }],
        data: nodes,
        links,
        lineStyle: { color: '#3b4a55', width: 1 }
      }
    ]
  })
  graphInstance.resize()
}

const openGraph = async () => {
  graphVisible.value = true
  await nextTick()
  buildGraph()
}

// 只读汇总：从当前路线结果拼出给 AI 说明用的精简摘要（不改动 routeData / timelineItems）
const buildAiRouteSummary = () => {
  const route = routeData.value
  const spots = (timelineItems.value || [])
    .filter((item) => item.kind === 'spot')
    .map((item) => ({ name: item.name, day: item.day, price: Number(item.price) || 0 }))
  // 天数取“实际排出的天数”，不是用户设置值：景点不足时可能只排出 1 天
  const planDays = (route?.day_plans || []).length
  const maxSpotDay = spots.reduce((m, s) => Math.max(m, Number(s.day) || 0), 0)
  return {
    days: planDays || maxSpotDay || Number(days.value) || null,
    total_distance: Number(route?.total_distance) || 0,
    tips: route?.tips ?? null,
    spots
  }
}

// AI 行程说明：生成路线成功后补一条中文说明，失败静默（属于可选增强）
const aiExplainRoute = async () => {
  if (!aiFilled.value || !String(aiMessage.value || '').trim()) return
  aiNoteLoading.value = true
  try {
    const res = await api.post('/api/v1/ai/explain', {
      message: aiMessage.value,
      route_summary: buildAiRouteSummary()
    })
    aiNote.value = res.data?.note || ''
  } catch (e) {
    // 可选增强：失败不提示，保持页面原有行为
    aiNote.value = ''
  } finally {
    aiNoteLoading.value = false
  }
}

// 偏好面板直接生成路线后：按路线景点请求 AI 介绍，并以打字机形式追加到对话区
const pushSpotIntro = async (data) => {
  const names = (data?.route || []).map((r) => r.name).filter(Boolean).slice(0, 6)
  if (!names.length) return
  const msg = { role: 'assistant', content: '', typing: true, tools: ['景点介绍'] }
  agentMessages.value.push(msg)
  const task = currentTask.value
  if (task && (!task.title || task.title === '新的规划任务')) {
    task.title = `${targetCity.value || '路线'} · ${days.value} 天`
  }
  try {
    const res = await api.post('/api/v1/ai/spots/intro', { spot_names: names }, { timeout: 60000 })
    await typewriter(msg, res.data?.note || '暂无景点介绍')
  } catch (e) {
    msg.typing = false
    msg.content = '景点介绍生成失败，可稍后重试'
  }
  if (task) {
    task.updatedAt = nowLabel()
    task.routeData = routeData.value
  }
  scrollToBottom()
}

const handleGenerate = async (options = {}) => {
  // 新一轮生成开始前清掉旧的 AI 说明，避免展示过期内容
  aiNote.value = ''
  aiNoteLoading.value = false
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
      exclude_spots: agentExcludeSpots.value,
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
    // 新路线默认展示地图 Tab，避免停留在“示意图”导致地图看起来没渲染
    routeView.value = 'map'
    await nextTick()
    await nextTick()
    await renderRouteMap()
    renderRouteChart()
    savePlanCache()
    // 偏好面板直接生成路线时，补一段 AI 景点介绍（对话区不再空白）
    if (options.intro !== false) await pushSpotIntro(res.data)
    // 成功生成后补充 AI 行程说明（仅当本次参数来自 AI 解析）
    await aiExplainRoute()
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
  // 重置后 AI 行程说明与“参数来自 AI”标记一并失效
  aiNote.value = ''
  aiFilled.value = false
  agentExcludeSpots.value = []
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

const retryMap = () => {
  mapError.value = ''
  mapVisible.value = false
  mapDirty = true
  nextTick(() => renderRouteMap())
}

const destroyMap = () => {
  if (mapResizeObserver) {
    mapResizeObserver.disconnect()
    mapResizeObserver = null
  }
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
    mapError.value = ''
    await nextTick()
    // 容器可能未挂载或宽度为 0：最多等待 ~1s
    for (let i = 0; i < 20; i++) {
      if (token !== mapRenderToken) return
      if (mapRef.value && mapRef.value.clientWidth > 0) break
      await new Promise((r) => setTimeout(r, 50))
      await nextTick()
    }
    if (token !== mapRenderToken || !mapRef.value) {
      mapError.value = '地图容器未就绪（DOM 缺失），请刷新后重试'
      console.warn('[Plan] 地图容器未就绪，跳过本次渲染')
      return
    }
    if (mapRef.value.clientWidth === 0) {
      mapError.value = '地图容器宽度为 0（布局未完成），请点击重试'
      console.warn('[Plan] 地图容器宽度为 0')
      return
    }
    if (!mapInstance) {
      if (mapResizeObserver) mapResizeObserver.disconnect()
      if (typeof ResizeObserver !== 'undefined') {
        mapResizeObserver = new ResizeObserver(() => {
          if (mapInstance) mapInstance.resize()
        })
        mapResizeObserver.observe(mapRef.value)
      }
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
    // 布局是 flex + 滚动容器，初始化后补一次 resize，避免宽度按 0 计算导致空白
    setTimeout(() => {
      if (mapInstance && token === mapRenderToken) mapInstance.resize()
    }, 60)
    mapDirty = false
  } catch (e) {
    console.warn('[Plan] 高德地图渲染失败，已隐藏地图:', e?.message || e)
    if (token === mapRenderToken) {
      mapError.value = String(e?.message || e || '地图渲染失败')
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

/* ================= AI 一句话规划 / AI 行程说明 ================= */
.ai-entry {
  padding: 12px;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  background: #fafbfc;
}
.ai-entry .section-label {
  color: #303133;
  font-weight: 600;
}
.ai-entry-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.ai-entry-hint {
  margin: 8px 0 0;
  line-height: 1.5;
}
.agent-chat {
  max-height: 260px;
  overflow-y: auto;
  margin: 10px 0 8px;
  padding-right: 4px;
}

.agent-msg {
  display: flex;
  flex-direction: column;
  margin-bottom: 8px;
}

.agent-msg.user {
  align-items: flex-end;
}

.agent-msg.assistant {
  align-items: flex-start;
}

.agent-bubble {
  max-width: 92%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.agent-msg.user .agent-bubble {
  background: #4f9d7a;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.agent-msg.assistant .agent-bubble {
  background: #f2f7f4;
  color: #2f4f42;
  border-bottom-left-radius: 4px;
}

.agent-loading {
  color: #8aa79a;
}

.agent-tools {
  margin-top: 4px;
  font-size: 12px;
  color: #96a89f;
}

.ai-reply {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}
.ai-note-card {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #f7f8fa;
}
.ai-note-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #303133;
}
.ai-note-title::before {
  content: '';
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: #f06818;
}
.ai-note-body {
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-line;
}
.ai-note-foot {
  margin-top: 8px;
  color: #b0b3b8;
  font-size: 12px;
}

/* ===================== 白底三栏布局（v1.5） ===================== */
.layout3 {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: calc(100vh - 88px);
  min-height: 620px;
  background: #ffffff;
  box-sizing: border-box;
}

/* ---------- 左栏：Agent 任务 ---------- */
.col-tasks {
  width: 260px;
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  background: #fffaf7;
  border: 1px solid #f3e6dc;
  border-radius: 14px;
  padding: 12px;
  box-sizing: border-box;
}

.tasks-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid #f5e7dd;
}

.tasks-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.tasks-add {
  background: #fff !important;
  border-color: #ffd9c2 !important;
  color: #ff7a45 !important;
}

.task-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 0;
}

.task-item {
  padding: 9px 11px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f3e6dc;
  cursor: pointer;
  transition: all 0.2s;
}

.task-item:hover {
  box-shadow: 0 2px 10px rgba(255, 122, 69, 0.1);
}

.task-item.active {
  border-color: #ffb08a;
  background: #fff5ef;
}

.task-name {
  color: #374151;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-sub {
  margin-top: 4px;
  color: #9aa3b2;
  font-size: 11px;
}

/* 底部固定提问区：与消息流左右留白一致，不撑满屏幕 */
.chat-composer {
  flex: 0 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 12px 16px 14px;
  border-top: 1px solid #f5e7dd;
  background: #fff;
}

.chat-composer :deep(.el-textarea) {
  flex: 1;
  min-width: 0;
}

.chat-composer :deep(.el-textarea__inner) {
  border-radius: 12px;
  background: #fffaf7;
  box-shadow: 0 0 0 1px #f3e0d5 inset;
  font-size: 13px;
  padding: 10px 12px;
}

.chat-composer .composer-send {
  width: 96px;
  height: 56px;
  flex: 0 0 96px;
  border-radius: 12px;
  background: #ff7a45;
  border-color: #ff7a45;
  font-weight: 600;
}

/* ---------- 中栏：主对话区 ---------- */
.col-chat {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #f3e6dc;
  border-radius: 14px;
  overflow: hidden;
}

.chat-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 12px 16px 8px;
}

.chat-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.chat-sub {
  margin-top: 3px;
  font-size: 12px;
  color: #9aa3b2;
}

.chat-new {
  color: #ff7a45 !important;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-bottom: 1px solid #f5e7dd;
  flex-wrap: wrap;
}

.chat-toolbar .el-button {
  border-radius: 8px;
}

.plan-name-input {
  width: 180px;
  margin-left: auto;
}

/* 偏好快照一行 */
.pref-bar {
  border-bottom: 1px solid #f5e7dd;
  background: #fffdfb;
}

.pref-line {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 12px;
}

.pref-title {
  color: #374151;
  font-weight: 600;
}

.pref-summary {
  flex: 1;
  color: #9aa3b2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pref-toggle {
  color: #ff7a45;
}

.pref-body {
  padding: 4px 16px 14px;
  max-height: 300px;
  overflow-y: auto;
}

.pref-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.pref-field {
  flex: 1;
  min-width: 200px;
  margin-bottom: 10px;
}

.pref-field--num {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.start-location-row {
  display: flex;
  gap: 8px;
}

.coord-tip {
  margin-top: 4px;
  font-size: 11px;
  color: #9aa3b2;
}

.type-group :deep(.el-radio-button__inner),
.pref-group :deep(.el-checkbox-button__inner) {
  border-radius: 8px;
  margin-right: 6px;
}

.pref-group :deep(.el-checkbox-button.is-checked .el-checkbox-button__inner),
.type-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: #ff7a45;
  border-color: #ff7a45;
  box-shadow: -1px 0 0 0 #ff7a45;
}

.booking-block {
  margin-top: 6px;
  padding: 10px;
  border: 1px dashed #f0ddd2;
  border-radius: 10px;
}

/* 消息流滚动区 */
.chat-flow {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.msg-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #ff7a45;
}

.msg-row.user .msg-avatar {
  background: #94a3b8;
}

.msg-bubble {
  max-width: 78%;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8f8fa;
  border: 1px solid #eef0f3;
  color: #374151;
  font-size: 13px;
  line-height: 1.75;
  word-break: break-word;
}

.msg-row.user .msg-bubble {
  background: #fff5ef;
  border-color: #ffd9c2;
  color: #4b2e1e;
}

.msg-text :deep(.entity-hl) {
  color: #ff7a45;
  border-bottom: 1px dashed #ffb08a;
  cursor: help;
}

.msg-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.tool-chip {
  padding: 1px 8px;
  border-radius: 999px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 11px;
}

.msg-check {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #eceff3;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
}

.check-score {
  color: #16a34a;
}

.check-issues {
  color: #d97706;
}

.msg-conflict {
  margin-top: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: #fff7e6;
  border: 1px solid #ffe0a3;
  color: #b45309;
  font-size: 12px;
}

.msg-degraded {
  margin-top: 6px;
  color: #d97706;
  font-size: 11px;
}

.msg-loading {
  color: #9aa3b2;
}

/* 路线卡片 */
.route-card {
  background: #fff;
  border: 1px solid #f3e6dc;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 4px 16px rgba(31, 41, 55, 0.04);
}

.route-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f3f4f6;
}

.route-summary .k {
  color: #9aa3b2;
  font-size: 11px;
  margin-right: 4px;
}

.route-summary .v {
  color: #111827;
  font-size: 13px;
  font-weight: 600;
}

.route-fold-head {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding: 6px 0;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 1px dashed #f0e2d9;
}

.fold-hint {
  color: #ff7a45;
}

.route-tips {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #fff7e6;
  border: 1px solid #ffe0a3;
  color: #b45309;
  font-size: 12px;
}

.route-detail {
  padding-top: 6px;
}

.timeline-title {
  color: #374151;
}

.timeline-meta {
  color: #9aa3b2;
}

.timeline-connector {
  background: #f0e2d9;
}

.timeline-dot.spot {
  background: #ff7a45;
}

.timeline-dot.hotel {
  background: #3b82f6;
}

.hotel-item {
  background: #fffaf7;
  border: 1px solid #f6e7dd;
}

.hotel-item-name {
  color: #374151;
}

.hotel-item-addr,
.hotel-empty {
  color: #9aa3b2;
}

.hotel-item-price {
  color: #ff7a45;
}

.map-wrap {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #f3e6dc;
}

.plan-map {
  width: 100%;
  height: 320px;
}

.map-legend {
  position: absolute;
  left: 10px;
  bottom: 10px;
  display: flex;
  gap: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #ffffffdd;
  border: 1px solid #f3e6dc;
  font-size: 11px;
  color: #6b7280;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}

.legend-spot {
  background: #ff7a45;
}

.legend-hotel {
  background: #2f9cff;
}

.plan-chart {
  width: 100%;
  height: 320px;
}

/* ---------- 右栏：Agent 工作台 ---------- */
.col-workbench {
  width: 300px;
  flex: 0 0 300px;
  background: #fff;
  border: 1px solid #f3e6dc;
  border-radius: 14px;
  padding: 12px;
  box-sizing: border-box;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wb-card {
  background: #fffaf7;
  border: 1px solid #f6e7dd;
  border-radius: 10px;
  padding: 10px;
}

.wb-title {
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 8px;
}

.wb-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.wb-chip {
  padding: 2px 8px;
  border-radius: 999px;
  background: #fff1e8;
  color: #ff7a45;
  font-size: 11px;
}

.wb-empty {
  color: #9aa3b2;
  font-size: 11px;
}

.entity-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #f3e6dc;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.entity-item:hover {
  box-shadow: 0 2px 8px rgba(255, 122, 69, 0.12);
}

.entity-type {
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 10px;
  background: #fff1e8;
  color: #ff7a45;
}

.entity-type.hotel {
  background: #eef6ff;
  color: #2563eb;
}

.entity-type.tip {
  background: #fff7e6;
  color: #b45309;
}

.entity-name {
  color: #374151;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mini-card {
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #f3e6dc;
  cursor: pointer;
  transition: all 0.2s;
}

.mini-card:hover {
  box-shadow: 0 2px 10px rgba(255, 122, 69, 0.12);
  border-color: #ffb08a;
}

.mini-name {
  color: #374151;
  font-size: 12px;
}

.mini-meta {
  margin-top: 4px;
  color: #9aa3b2;
  font-size: 11px;
}

.graph-btn {
  margin-top: auto;
  background: #ff7a45 !important;
  border-color: #ff7a45 !important;
  color: #fff !important;
  border-radius: 10px;
}

.graph-canvas {
  width: 100%;
  height: 520px;
  background: #fff;
  border-radius: 10px;
}

/* 窄屏适配 */
@media (max-width: 1280px) {
  .col-tasks {
    width: 220px;
    flex-basis: 220px;
  }
  .col-workbench {
    width: 240px;
    flex-basis: 240px;
  }
}

@media (max-width: 1024px) {
  .layout3 {
    flex-wrap: wrap;
    height: auto;
  }
  .col-tasks,
  .col-workbench {
    width: 100%;
    flex-basis: 100%;
  }
  .chat-flow {
    max-height: 60vh;
  }
}


/* ===== 中间栏结果流下移（v1.6） ===== */
/* 标题与按钮区下方留白 */
.col-chat .chat-head {
  padding-top: 16px;
  padding-bottom: 12px;
}

.col-chat .chat-toolbar {
  padding-bottom: 10px;
}

/* 偏好快照与消息流之间再留出一段距离 */
.col-chat .pref-bar {
  margin-bottom: 6px;
}

/* 滚动容器：顶部留白，聚焦下方结果 */
.col-chat .chat-flow {
  padding-top: 28px;
}

/* 可伸缩留白：内容少时把消息压到中下部，内容多时自动收起为 0 */
.chat-lead {
  flex: 1 0 auto;
  min-height: 12px;
}

/* 内容较多时保证从顶部正常开始滚动，不被留白挤压 */
.chat-flow > .msg-row:first-of-type,
.chat-flow > .route-card:first-of-type {
  flex-shrink: 0;
}


/* 流式输出光标 */
.msg-text.typing::after {
  content: '▍';
  display: inline-block;
  margin-left: 2px;
  color: #ff7a45;
  animation: caret-blink 0.9s steps(2, start) infinite;
}

@keyframes caret-blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}


/* 卡片类型标签：景点橙 / 酒店蓝 */
.mini-tag {
  display: inline-block;
  padding: 0 5px;
  margin-right: 6px;
  border-radius: 4px;
  font-size: 10px;
  line-height: 16px;
  border: 1px solid transparent;
  vertical-align: middle;
}

.mini-tag.spot {
  background: #fff1e8;
  color: #ff7a45;
  border-color: #ffd2b8;
}

.mini-tag.hotel {
  background: #eef6ff;
  color: #2563eb;
  border-color: #c7e0ff;
}


.map-fallback { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 8px 0; }
.map-error { max-width: 92%; font-size: 12px; color: #b45309; background: #fff7e6;
  border: 1px solid #ffe0a3; border-radius: 8px; padding: 6px 10px; word-break: break-all; }

</style>
