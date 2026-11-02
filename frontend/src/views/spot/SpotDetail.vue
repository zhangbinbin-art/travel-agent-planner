<template>
  <div class="spot-detail">
    <div class="spot-inner">
      <!-- ========== ① 首屏 Hero ========== -->
      <section class="spot-hero">
        <img
          v-if="spot.cover"
          class="hero-cover"
          :src="spot.cover"
          :alt="spot.name || '景点封面'"
        />
        <div v-else class="hero-placeholder">
          <span class="hero-watermark">{{ spot.theme || '目的地' }}</span>
        </div>
        <div class="hero-mask"></div>

        <div class="hero-body">
          <div class="hero-info">
            <h1 class="hero-title">{{ spot.name || '景点详情' }}</h1>
            <div class="hero-meta">
              <span v-if="locationText" class="hero-location">
                <el-icon><Location /></el-icon>
                <span>{{ locationText }}</span>
              </span>
              <span v-if="tagList.length" class="hero-tags" :title="tagText">
                <span v-for="t in tagList" :key="t" class="hero-tag">{{ t }}</span>
              </span>
              <span class="hero-meta-text">{{ scoreText === '暂无评分' ? scoreText : '评分 ' + scoreText }}</span>
              <span class="hero-meta-text">热度 {{ heat }}</span>
            </div>
          </div>

          <div class="hero-actions">
            <el-button type="primary" class="hero-btn" @click="goPlan">
              <el-icon class="btn-icon"><Position /></el-icon>
              <span>生成路线</span>
            </el-button>
            <el-button
              class="hero-btn fav-btn"
              :class="{ 'is-favorited': isFavorited }"
              plain
              :loading="favoriteLoading"
              @click="handleFavorite"
            >
              <el-icon class="btn-icon">
                <StarFilled v-if="isFavorited" />
                <Star v-else />
              </el-icon>
              <span>{{ isFavorited ? '已收藏' : '收藏景点' }}</span>
            </el-button>
            <el-button class="hero-btn share-btn" circle aria-label="分享" @click="copyShareLink">
              <el-icon><Share /></el-icon>
            </el-button>
          </div>
        </div>
      </section>

      <!-- ========== ② 下划线 Tab ========== -->
      <nav class="spot-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <!-- ========== ③ 景点介绍 ========== -->
      <div v-if="activeTab === 'intro'" class="tab-panel">
        <section class="content-card">
          <h2 class="card-title">基本信息</h2>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">城市</span>
              <span class="info-value">{{ locationText || '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">地址</span>
              <span class="info-value">{{ addressText }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">评分</span>
              <span class="info-value">{{ scoreText }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">热度</span>
              <span class="info-value">{{ heat }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">门票</span>
              <span class="info-value">{{ priceText }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">建议游玩时长</span>
              <span class="info-value">—</span>
            </div>
            <div class="info-item info-item--full">
              <span class="info-label">标签</span>
              <span v-if="tagList.length" class="info-value tag-list">
                <el-tag v-for="t in tagList" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
              </span>
              <span v-else class="info-value">—</span>
            </div>
          </div>
        </section>

        <section class="content-card">
          <h2 class="card-title">景点介绍</h2>
          <template v-if="descParagraphs.length">
            <p class="desc-text">{{ descParagraphs[0] }}</p>
            <img
              v-if="spot.cover"
              class="desc-image"
              :src="spot.cover"
              :alt="spot.name || '景点图片'"
            />
            <p v-for="(para, idx) in descParagraphs.slice(1)" :key="idx" class="desc-text">{{ para }}</p>
          </template>
          <p v-else class="desc-empty">暂无介绍</p>
        </section>
      </div>

      <!-- ========== ④ 推荐路线 ========== -->
      <div v-else-if="activeTab === 'route'" class="tab-panel">
        <section class="content-card">
          <h2 class="card-title">推荐路线</h2>

          <div v-if="tripLoading" class="skeleton-block">
            <el-skeleton :rows="4" animated />
          </div>

          <div v-else-if="spotTrip" class="trip-card">
            <div class="trip-head">
              <h3 class="trip-name">{{ spotTrip.name }}</h3>
              <div class="trip-meta">
                <span class="trip-meta-item">天数 <strong>{{ tripDays }}</strong> 天</span>
                <span class="trip-meta-item">总距离 <strong>{{ tripDistance }}</strong> km</span>
                <span class="trip-meta-item">预算 <strong class="trip-budget">¥{{ tripBudget }}</strong></span>
              </div>
            </div>

            <div class="trip-route-label">途径景点</div>
            <div class="trip-route">
              <span
                v-for="(r, idx) in sortedTripRoute"
                :key="r.id ?? idx"
                class="route-chip"
                :class="{ 'is-current': String(r.id) === String(route.params.id) }"
              >
                {{ r.order ?? idx + 1 }}. {{ r.name }}
              </span>
            </div>

            <div class="trip-foot">
              <el-button type="primary" plain @click="router.push('/user/my-plan')">查看完整路线</el-button>
            </div>
          </div>

          <div v-else class="trip-empty">
            <div class="trip-empty-title">还没有包含该景点的行程</div>
            <p class="trip-empty-desc">根据当前目的地一键生成智能路线，自动规划景点顺序与酒店</p>
            <el-button type="primary" @click="goPlan">生成路线</el-button>
          </div>
        </section>
      </div>

      <!-- ========== ⑤ 周边酒店 ========== -->
      <div v-else-if="activeTab === 'hotel'" class="tab-panel">
        <section class="content-card hotel-card-section" v-loading="hotelLoading">
          <h2 class="card-title">周边酒店</h2>

          <div v-if="nearbyHotels.length" class="hotel-grid">
            <article
              v-for="h in nearbyHotels"
              :key="h.id"
              class="hotel-card"
              @click="goHotel(h.id)"
            >
              <el-image v-if="h.cover_img" class="hotel-cover" :src="h.cover_img" fit="cover">
                <template #error>
                  <div class="hotel-cover-ph">暂无图片</div>
                </template>
              </el-image>
              <div v-else class="hotel-cover-ph">暂无图片</div>
              <div class="hotel-body">
                <h3 class="hotel-name" :title="h.name">{{ h.name }}</h3>
                <div class="hotel-price">¥{{ formatPrice(h.price_per_day) }}<span class="hotel-price-unit">/晚</span></div>
                <div class="hotel-score">环境 {{ scoreOrDash(h.env_score) }} · 服务 {{ scoreOrDash(h.service_score) }}</div>
                <div v-if="h.distance != null" class="hotel-distance">距景点约 {{ Number(h.distance).toFixed(1) }} km</div>
              </div>
            </article>
          </div>

          <el-empty v-else-if="!hotelLoading" :image-size="60" description="暂无周边酒店" />
        </section>
      </div>

      <!-- ========== ⑥ 用户点评 ========== -->
      <div v-else-if="activeTab === 'comment'" class="tab-panel">
        <section class="content-card sentiment-card">
          <div class="sentiment-chart-wrap">
            <div v-if="sentimentLoading" v-loading="sentimentLoading" class="emotion-chart chart-loading"></div>
            <div v-else-if="sentimentTotal === 0" class="sentiment-empty">
              <el-empty :image-size="50" description="暂无点评数据" />
            </div>
            <div v-else id="emotion-chart" ref="chartRef" class="emotion-chart"></div>
          </div>

          <div class="sentiment-overview" :class="{ 'is-muted': sentimentTotal === 0 }">
            <div class="overview-eyebrow">点评概览</div>
            <div class="overview-total">共 <strong>{{ sentimentTotal }}</strong> 条点评</div>
            <div class="overview-legend">
              <span class="legend-item"><i class="legend-dot dot-positive"></i>正面 {{ sentiment.positive }}</span>
              <span class="legend-item"><i class="legend-dot dot-neutral"></i>中性 {{ sentiment.neutral }}</span>
              <span class="legend-item"><i class="legend-dot dot-negative"></i>负面 {{ sentiment.negative }}</span>
            </div>
            <p class="overview-hint">数据来自关联游记评论的情感分析</p>
          </div>
        </section>

        <section class="content-card comments-card" v-loading="commentLoading">
          <h2 class="card-title">用户点评</h2>

          <div v-if="spotComments.length" class="comment-list">
            <article v-for="(c, idx) in spotComments" :key="`${c.id}-${idx}`" class="comment-item">
              <div class="comment-avatar" :style="{ backgroundColor: avatarColorOf(c.author?.username) }">
                {{ avatarTextOf(c.author?.username) }}
              </div>
              <div class="comment-main">
                <div class="comment-head">
                  <span class="comment-author">{{ c.author?.username || '匿名' }}</span>
                  <span v-if="c.score !== null && c.score !== undefined" class="comment-score">{{ c.score }} 分</span>
                  <span class="comment-time">{{ formatDate(c.created_at) }}</span>
                </div>
                <p class="comment-content">{{ c.content }}</p>
                <div v-if="c.postTitle" class="comment-source">来自游记《{{ c.postTitle }}》</div>
              </div>
            </article>
          </div>

          <div v-else-if="!commentLoading" class="comment-empty">
            <el-empty :image-size="60" description="暂无景点点评" />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Star, StarFilled, Share, Position, Location } from '@element-plus/icons-vue'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getSpotDetail } from '@/api/spot'
import { toggleFavorite, getMyFavoriteSpots } from '@/api/favorite'
import { getSpotSentiment, getPostList, getCommentList } from '@/api/post'
import { getMyTrips, getTripDetail } from '@/api/trip'
import { getOnShelfHotels } from '@/api/hotel'
import { auth } from '@/utils/auth'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()

/* ---------- 基础状态（逻辑保留） ---------- */
const spot = ref({})
const isFavorited = ref(false)
const favoriteLoading = ref(false)
const sentimentLoading = ref(false)
const sentimentTotal = ref(0)
const sentiment = ref({ positive: 0, neutral: 0, negative: 0 })
const chartRef = ref(null)
let chartInstance = null
let resizeHandler = null
// 情感数据缓存：图表容器只在「用户点评」Tab 挂载，切 Tab 后用它重绘
let sentimentData = null

/* ---------- 新增状态 ---------- */
const activeTab = ref('intro')
const tabs = [
  { key: 'intro', label: '景点介绍' },
  { key: 'route', label: '推荐路线' },
  { key: 'hotel', label: '周边酒店' },
  { key: 'comment', label: '用户点评' }
]

const relatedPosts = ref([])
const spotComments = ref([])
const commentLoading = ref(false)
const nearbyHotels = ref([])
const hotelLoading = ref(false)
const spotTrip = ref(null)
const tripLoading = ref(false)

/* ---------- 计算属性 ---------- */
const tagList = computed(() => {
  const tags = spot.value.tags
  if (Array.isArray(tags)) return tags.filter(Boolean).map((t) => String(t).trim()).filter(Boolean)
  if (typeof tags === 'string') {
    return tags
      .split(/[,，;；|]/)
      .map((t) => t.trim())
      .filter(Boolean)
  }
  return []
})

const tagText = computed(() => tagList.value.join('、'))

const locationText = computed(() => {
  const province = String(spot.value.province || '').trim()
  const city = String(spot.value.city || '').trim()
  if (!province && !city) return ''
  if (!province) return city
  if (!city) return province
  if (province === city) return province
  return `${province}·${city}`
})

const addressText = computed(() => {
  const province = String(spot.value.province || '').trim()
  const city = String(spot.value.city || '').trim()
  if (!province && !city) return '—'
  if (!province) return city
  if (!city) return province
  if (province === city) return province
  return `${province} ${city}`
})

const scoreText = computed(() => {
  const score = spot.value.score
  if (score === null || score === undefined || score === '') return '暂无评分'
  const num = Number(score)
  if (!Number.isFinite(num)) return '暂无评分'
  return `${num} 分`
})

const priceText = computed(() => {
  const price = spot.value.price
  if (price === null || price === undefined || price === '') return '—'
  const num = Number(price)
  if (!Number.isFinite(num)) return '—'
  return num > 0 ? `¥${num}` : '免费'
})

const descriptionText = computed(() => {
  const text = spot.value.description || spot.value.desc || ''
  return typeof text === 'string' ? text.trim() : ''
})

const descParagraphs = computed(() => {
  if (!descriptionText.value) return []
  return descriptionText.value
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean)
})

// 热度 = 关联游记 heat 之和；无关联游记时为 0
const heat = computed(() =>
  (relatedPosts.value || []).reduce((sum, p) => sum + (Number(p.heat) || 0), 0)
)

const sortedTripRoute = computed(() => {
  const routeList = spotTrip.value?.route
  if (!Array.isArray(routeList)) return []
  return [...routeList].sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0))
})

const tripDays = computed(() => {
  const days = spotTrip.value?.days ?? spotTrip.value?.budget?.days
  return days ?? '—'
})

const tripDistance = computed(() => {
  const num = Number(spotTrip.value?.total_distance)
  return Number.isFinite(num) ? num.toFixed(1) : '—'
})

const tripBudget = computed(() => formatMoney(spotTrip.value?.budget?.grand_total))

/* ---------- 纯工具函数（新增） ---------- */
const formatMoney = (value) => {
  if (value === null || value === undefined || value === '') return '—'
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return Number.isInteger(num) ? String(num) : num.toFixed(2)
}

const formatPrice = (value) => formatMoney(value)

const scoreOrDash = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  return Number.isFinite(num) ? String(num) : '-'
}

const formatDate = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#909399', '#8e7cc3', '#2f9e7e']

const avatarTextOf = (name) => {
  const text = String(name || '匿').trim()
  return (text.charAt(0) || '匿').toUpperCase()
}

const avatarColorOf = (name) => {
  const text = String(name || '匿名').trim() || '匿名'
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) % 100000
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

const toRad = (deg) => (Number(deg) * Math.PI) / 180

const haversine = (lat1, lng1, lat2, lng2) => {
  const earthRadius = 6371
  const dLat = toRad(Number(lat2) - Number(lat1))
  const dLng = toRad(Number(lng2) - Number(lng1))
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * earthRadius * Math.asin(Math.sqrt(a))
}

/* ---------- 收藏（逻辑语义保持不变） ---------- */
const loadFavoriteState = async () => {
  if (!auth.token) return
  try {
    const res = await getMyFavoriteSpots()
    const items = res.data?.items || []
    isFavorited.value = items.some((it) => String(it.spot_id) === String(route.params.id))
  } catch (e) {
    // 静默失败，不影响详情展示
  }
}

const handleFavorite = async () => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  favoriteLoading.value = true
  try {
    const res = await toggleFavorite(route.params.id)
    const favorited = res.data?.favorited
    isFavorited.value = typeof favorited === 'boolean' ? favorited : !isFavorited.value
    ElMessage.success(res.data?.message || (isFavorited.value ? '收藏成功' : '取消收藏成功'))
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.warning('请先登录')
      router.push({ path: '/login', query: { redirect: route.fullPath } })
      return
    }
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    favoriteLoading.value = false
  }
}

/* ---------- 情感图表（缩小版环形图） ---------- */
const initChart = (data) => {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      show: false
    },
    series: [
      {
        type: 'pie',
        radius: ['44%', '64%'],
        avoidLabelOverlap: false,
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: false
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: data.positive || 0, name: '正面', itemStyle: { color: '#67c23a' } },
          { value: data.neutral || 0, name: '中性', itemStyle: { color: '#909399' } },
          { value: data.negative || 0, name: '负面', itemStyle: { color: '#f56c6c' } }
        ]
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

const loadSentiment = async () => {
  sentimentLoading.value = true
  sentimentTotal.value = 0
  sentiment.value = { positive: 0, neutral: 0, negative: 0 }
  sentimentData = null
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  let data = null
  try {
    const res = await getSpotSentiment(route.params.id)
    data = res.data || {}
    sentimentTotal.value = data.total || 0
    sentiment.value = {
      positive: data.positive || 0,
      neutral: data.neutral || 0,
      negative: data.negative || 0
    }
    sentimentData = data
  } catch (e) {
    sentimentTotal.value = 0
    sentiment.value = { positive: 0, neutral: 0, negative: 0 }
    sentimentData = null
  } finally {
    sentimentLoading.value = false
  }
  // 必须等 loading 关闭、图表容器真正挂载后再 init，否则 ref 为 null 画不出饼图
  if (data && sentimentTotal.value > 0) {
    await nextTick()
    if (chartRef.value) initChart(data)
  }
}

/* ---------- 关联游记 + 景点点评 ---------- */
const loadRelatedAndComments = async () => {
  commentLoading.value = true
  relatedPosts.value = []
  spotComments.value = []
  try {
    const res = await getPostList({ spot_id: route.params.id, page: 1, page_size: 5 })
    const posts = res.data?.items || []
    relatedPosts.value = posts
    if (!posts.length) return

    const results = await Promise.allSettled(
      posts.map((p) => getCommentList(p.id, { page: 1, page_size: 5 }))
    )

    const merged = []
    results.forEach((result, index) => {
      if (result.status !== 'fulfilled') return
      const post = posts[index]
      const items = result.value?.data?.items || []
      items.forEach((c) => {
        if (!c) return
        // 只保留审核通过的评论（字段缺失时不过滤）
        if (c.status !== undefined && c.status !== 1) return
        merged.push({ ...c, postTitle: post?.title || '' })
      })
    })

    merged.sort((a, b) => {
      const ta = new Date(a.created_at).getTime()
      const tb = new Date(b.created_at).getTime()
      return (Number.isFinite(tb) ? tb : 0) - (Number.isFinite(ta) ? ta : 0)
    })
    spotComments.value = merged.slice(0, 10)
  } catch (e) {
    relatedPosts.value = []
    spotComments.value = []
  } finally {
    commentLoading.value = false
  }
}

/* ---------- 周边酒店 ---------- */
const loadNearbyHotels = async () => {
  hotelLoading.value = true
  nearbyHotels.value = []
  try {
    const res = await getOnShelfHotels()
    const items = (res.data?.items || []).filter(Boolean)

    const lat = spot.value.lat
    const lng = spot.value.lng
    const hasCoord =
      lat !== null &&
      lat !== undefined &&
      lng !== null &&
      lng !== undefined &&
      Number.isFinite(Number(lat)) &&
      Number.isFinite(Number(lng))

    if (hasCoord) {
      const spotLat = Number(lat)
      const spotLng = Number(lng)
      nearbyHotels.value = items
        .filter((h) => {
          const valid =
            h.lat !== null &&
            h.lat !== undefined &&
            h.lng !== null &&
            h.lng !== undefined &&
            Number.isFinite(Number(h.lat)) &&
            Number.isFinite(Number(h.lng))
          return valid
        })
        .map((h) => ({
          ...h,
          distance: haversine(spotLat, spotLng, Number(h.lat), Number(h.lng))
        }))
        .sort((a, b) => a.distance - b.distance)
        .slice(0, 4)
    } else {
      const city = String(spot.value.city || '').trim()
      const pool = city
        ? items.filter((h) => typeof h.address === 'string' && h.address.includes(city))
        : items
      nearbyHotels.value = [...pool]
        .sort((a, b) => (Number(b.env_score) || 0) - (Number(a.env_score) || 0))
        .slice(0, 4)
    }
  } catch (e) {
    nearbyHotels.value = []
  } finally {
    hotelLoading.value = false
  }
}

/* ---------- 包含本景点的行程 ---------- */
const loadSpotTrip = async () => {
  tripLoading.value = true
  spotTrip.value = null
  try {
    const res = await getMyTrips({ page: 1, page_size: 20 })
    const items = (res.data?.items || []).slice(0, 10)
    if (!items.length) return

    const details = await Promise.allSettled(items.map((trip) => getTripDetail(trip.id)))
    const found = details
      .filter((result) => result.status === 'fulfilled')
      .map((result) => result.value?.data)
      .find(
        (detail) =>
          detail &&
          Array.isArray(detail.route) &&
          detail.route.some((r) => String(r.id) === String(route.params.id))
      )
    spotTrip.value = found || null
  } catch (e) {
    spotTrip.value = null
  } finally {
    tripLoading.value = false
  }
}

/* ---------- 景点详情 ---------- */
const loadSpotDetail = async () => {
  spot.value = {}
  try {
    const res = await getSpotDetail(route.params.id)
    spot.value = res.data || {}
  } catch (e) {
    if (e?.response?.status === 404) {
      ElMessage.error('景点不存在')
    } else {
      ElMessage.error('获取景点详情失败')
    }
  }
}

/* ---------- 分享 / 跳转 ---------- */
const copyShareLink = async () => {
  const link = window.location.href
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(link)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = link
      textarea.style.position = 'fixed'
      textarea.style.top = '-1000px'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    ElMessage.success('链接已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动复制地址栏链接')
  }
}

const goPlan = () => {
  router.push('/plan')
}

const goHotel = (id) => {
  router.push(`/hotel-detail/${id}`)
}

/* ---------- 加载全部模块 ---------- */
const loadAll = async () => {
  await loadSpotDetail()
  loadFavoriteState()
  loadSentiment()
  loadRelatedAndComments()
  loadNearbyHotels()
  loadSpotTrip()
}

watch(
  () => route.params.id,
  () => {
    loadAll()
  }
)

// 图表容器只在点评 Tab 里；切回点评时用缓存数据重绘，离开时销毁避免 resize 已卸载节点
watch(activeTab, async (tab) => {
  if (tab === 'comment') {
    if (sentimentData && sentimentTotal.value > 0) {
      await nextTick()
      initChart(sentimentData)
    }
  } else if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

onMounted(() => {
  loadAll()
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
/* ================= A. 页面背景与容器 ================= */
.spot-detail {
  margin: -20px;
  padding: 20px;
  min-height: calc(100vh - 60px);
  box-sizing: border-box;
  background: #f5f8fa;
}
.spot-inner {
  max-width: 1040px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ================= B. 首屏 Hero ================= */
.spot-hero {
  position: relative;
  height: 300px;
  border-radius: 12px;
  overflow: hidden;
  background: #dbe4ee;
}
.hero-cover {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #8ec5fc, #e0c3fc);
}
.hero-watermark {
  font-size: 64px;
  font-weight: 700;
  letter-spacing: 6px;
  color: rgba(255, 255, 255, 0.55);
  user-select: none;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.hero-mask {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.72) 0%,
    rgba(0, 0, 0, 0.25) 45%,
    transparent 100%
  );
}
.hero-body {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: flex-end;
  padding: 24px;
}
.hero-info {
  max-width: calc(100% - 300px);
  min-width: 0;
}
.hero-title {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.3;
  color: #fff;
  word-break: break-word;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
}
.hero-location {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.hero-tags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}
.hero-tag {
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
  color: #fff;
}
.hero-meta-text {
  white-space: nowrap;
}
.hero-actions {
  position: absolute;
  right: 24px;
  bottom: 24px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.hero-btn {
  height: 36px;
  border-radius: 8px;
}
.btn-icon {
  margin-right: 6px;
  font-size: 15px;
}
.fav-btn {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.12);
}
.fav-btn:hover {
  color: #fff;
  border-color: #fff;
  background: rgba(255, 255, 255, 0.24);
}
.hero-btn.fav-btn.is-favorited {
  color: #e6a23c;
  border-color: #f7ba2a;
  background: #fffbf0;
}
.hero-btn.fav-btn.is-favorited:hover {
  color: #d48f1f;
  border-color: #f7ba2a;
  background: #fff7e0;
}
.share-btn {
  width: 36px;
  color: #fff;
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.12);
}
.share-btn:hover {
  color: #fff;
  border-color: #fff;
  background: rgba(255, 255, 255, 0.24);
}

/* ================= C. 下划线 Tab ================= */
.spot-tabs {
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: #fff;
  border-radius: 12px;
  border-bottom: 1px solid #f0f2f5;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  overflow-x: auto;
  scrollbar-width: none;
}
.spot-tabs::-webkit-scrollbar {
  display: none;
}
.tab-item {
  position: relative;
  margin-right: 32px;
  padding: 14px 4px;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.4;
  color: #606266;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.2s;
}
.tab-item:last-child {
  margin-right: 0;
}
.tab-item:hover {
  color: #409eff;
}
.tab-item.active {
  font-weight: 700;
  color: #2c3e50;
}
.tab-item.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  border-radius: 2px;
  background: #409eff;
}

/* ================= D. 通用内容卡 ================= */
.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.content-card {
  padding: 24px;
  background: #fff;
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
}
.card-title {
  margin: 0 0 18px;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

/* ================= E. 基本信息卡 ================= */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px 24px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.info-item--full {
  grid-column: 1 / -1;
}
.info-label {
  font-size: 12.5px;
  color: #909399;
}
.info-value {
  font-size: 15px;
  line-height: 1.5;
  color: #303133;
  word-break: break-word;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-list :deep(.el-tag) {
  border-radius: 999px;
}

/* ================= F. 图文介绍卡 ================= */
.desc-text {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.7;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}
.desc-text:last-child {
  margin-bottom: 0;
}
.desc-image {
  display: block;
  width: 100%;
  max-height: 320px;
  margin: 0 0 16px;
  border-radius: 8px;
  object-fit: cover;
}
.desc-empty {
  margin: 0;
  font-size: 14px;
  color: #a8abb2;
}

/* ================= G. 推荐路线 ================= */
.skeleton-block {
  padding: 8px 0;
}
.trip-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 20px;
}
.trip-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}
.trip-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  font-size: 13px;
  color: #909399;
}
.trip-meta strong {
  font-weight: 600;
  color: #303133;
}
.trip-meta .trip-budget {
  color: #e6a23c;
}
.trip-route-label {
  margin: 20px 0 10px;
  font-size: 13px;
  color: #909399;
}
.trip-route {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.route-chip {
  padding: 5px 12px;
  border-radius: 999px;
  background: #f4f6f9;
  font-size: 13px;
  color: #606266;
}
.route-chip.is-current {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}
.trip-foot {
  margin-top: 20px;
}
.trip-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 20px;
  border: 1px dashed #c6dcff;
  border-radius: 10px;
  background: #f5f9ff;
  text-align: center;
}
.trip-empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}
.trip-empty-desc {
  max-width: 420px;
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #909399;
}

/* ================= H. 周边酒店 ================= */
.hotel-card-section {
  min-height: 140px;
}
.hotel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.hotel-card {
  overflow: hidden;
  border: 1px solid #f0f2f5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.hotel-card:hover {
  transform: translateY(-2px);
  border-color: #e4e9f0;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
}
.hotel-cover {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #f2f4f7;
}
.hotel-cover :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hotel-cover-ph {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #f2f4f7;
  font-size: 12px;
  color: #c0c4cc;
}
.hotel-body {
  padding: 12px 14px 14px;
}
.hotel-name {
  margin: 0;
  overflow: hidden;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.hotel-price {
  margin-top: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #e6a23c;
}
.hotel-price-unit {
  font-size: 12px;
  font-weight: 400;
  color: #c0a16b;
}
.hotel-score {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}
.hotel-distance {
  margin-top: 4px;
  font-size: 12px;
  color: #a8abb2;
}

/* ================= I. 用户点评：情感概览 ================= */
.sentiment-card {
  display: flex;
  align-items: center;
  gap: 28px;
}
.sentiment-chart-wrap {
  flex: 0 0 240px;
  width: 240px;
}
.emotion-chart {
  width: 100%;
  height: 200px;
}
.chart-loading {
  border-radius: 8px;
}
.sentiment-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
}
.sentiment-empty :deep(.el-empty) {
  padding: 0;
}
.sentiment-empty :deep(.el-empty__description p) {
  font-size: 12px;
  color: #c0c4cc;
}
.sentiment-overview {
  flex: 1 1 auto;
  min-width: 0;
}
.sentiment-overview.is-muted {
  opacity: 0.65;
}
.overview-eyebrow {
  font-size: 12px;
  letter-spacing: 1px;
  color: #a8abb2;
}
.overview-total {
  margin-top: 8px;
  font-size: 16px;
  color: #303133;
}
.overview-total strong {
  margin: 0 4px;
  font-size: 26px;
  color: #2c3e50;
}
.overview-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-top: 14px;
  font-size: 13px;
  color: #606266;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-positive {
  background: #67c23a;
}
.dot-neutral {
  background: #909399;
}
.dot-negative {
  background: #f56c6c;
}
.overview-hint {
  margin: 14px 0 0;
  font-size: 12px;
  color: #c0c4cc;
}

/* ================= J. 用户点评：评论列表 ================= */
.comments-card {
  min-height: 160px;
}
.comment-list {
  display: flex;
  flex-direction: column;
}
.comment-item {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #f7f8fa;
}
.comment-item:first-child {
  padding-top: 0;
}
.comment-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}
.comment-avatar {
  display: flex;
  flex: 0 0 36px;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  line-height: 1;
  user-select: none;
}
.comment-main {
  flex: 1;
  min-width: 0;
}
.comment-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.comment-author {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.comment-score {
  padding: 1px 8px;
  border-radius: 999px;
  background: #fdf6ec;
  font-size: 12px;
  color: #e6a23c;
}
.comment-time {
  font-size: 12px;
  color: #a8abb2;
}
.comment-content {
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-source {
  margin-top: 8px;
  font-size: 12px;
  color: #c0c4cc;
}
.comment-empty {
  padding: 8px 0;
}
.comment-empty :deep(.el-empty) {
  padding: 24px 0;
}
.comment-empty :deep(.el-empty__description p) {
  font-size: 13px;
  color: #c0c4cc;
}

/* ================= K. 响应式 ================= */
@media (max-width: 768px) {
  .spot-inner {
    gap: 16px;
  }
  .spot-hero {
    height: 220px;
  }
  .hero-body {
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-end;
    gap: 12px;
    padding: 18px;
  }
  .hero-info {
    max-width: 100%;
  }
  .hero-title {
    font-size: 24px;
  }
  .hero-meta {
    gap: 8px 12px;
    margin-top: 8px;
    font-size: 13px;
  }
  .hero-watermark {
    font-size: 38px;
    letter-spacing: 3px;
  }
  .hero-actions {
    position: static;
    flex-wrap: wrap;
  }
  .hero-btn {
    height: 34px;
  }
  .spot-tabs {
    padding: 0 14px;
    border-radius: 10px;
  }
  .tab-item {
    margin-right: 24px;
    font-size: 14px;
  }
  .content-card {
    padding: 18px;
  }
  .card-title {
    margin-bottom: 14px;
  }
  .info-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .sentiment-card {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }
  .sentiment-chart-wrap {
    flex-basis: auto;
    width: 100%;
  }
  .overview-total strong {
    font-size: 22px;
  }
  .comment-avatar {
    flex-basis: 32px;
    width: 32px;
    height: 32px;
    font-size: 14px;
  }
  .trip-empty {
    padding: 30px 16px;
  }
}
</style>
