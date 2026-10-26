<template>
  <div class="spot-detail">
    <el-card>
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span>景点详情（ID：{{ $route.params.id }}）</span>
          <el-button :type="isFavorited ? 'warning' : 'primary'" :loading="favoriteLoading" @click="handleFavorite">
            {{ isFavorited ? '已收藏' : '收藏' }}
          </el-button>
        </div>
      </template>
      <el-descriptions title="基本信息" :column="2" border>
        <el-descriptions-item label="景点名称">{{ spot.name }}</el-descriptions-item>
        <el-descriptions-item label="城市">{{ spot.city }}</el-descriptions-item>
        <el-descriptions-item label="评分">{{ spot.score }} 分</el-descriptions-item>
        <el-descriptions-item label="标签">{{ tagText }}</el-descriptions-item>
        <el-descriptions-item label="简介" :span="2">{{ spot.description || spot.desc }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>评论情感占比</el-divider>
      <div v-if="sentimentLoading" v-loading="sentimentLoading" class="emotion-chart"></div>
      <div v-else-if="sentimentTotal === 0" class="emotion-empty">
        <el-empty description="暂无评论数据" />
      </div>
      <div v-else id="emotion-chart" ref="chartRef" class="emotion-chart"></div>
      <el-divider>评论列表</el-divider>
      <el-empty description="暂无景点评论" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getSpotDetail } from '@/api/spot'
import { addFavorite, removeFavorite, getMyFavorites } from '@/api/favorite'
import { getSpotSentiment } from '@/api/post'
import { auth } from '@/utils/auth'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const spot = ref({})
const isFavorited = ref(false)
const favoriteLoading = ref(false)
const sentimentLoading = ref(false)
const sentimentTotal = ref(0)
const chartRef = ref(null)
let chartInstance = null
let resizeHandler = null

const tagText = computed(() => {
  if (Array.isArray(spot.value.tags)) return spot.value.tags.join('、')
  if (typeof spot.value.tags === 'string') return spot.value.tags
  return ''
})

const loadFavoriteState = async () => {
  if (!auth.token) return
  try {
    const res = await getMyFavorites({ page: 1, page_size: 100 })
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
    if (isFavorited.value) {
      await removeFavorite(route.params.id)
      isFavorited.value = false
      ElMessage.success('取消收藏成功')
    } else {
      await addFavorite(route.params.id)
      isFavorited.value = true
      ElMessage.success('收藏成功')
    }
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
      bottom: 0
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          formatter: '{b}: {c} ({d}%)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: true
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
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  let data = null
  try {
    const res = await getSpotSentiment(route.params.id)
    data = res.data || {}
    sentimentTotal.value = data.total || 0
  } catch (e) {
    sentimentTotal.value = 0
  } finally {
    sentimentLoading.value = false
  }
  // 必须等 loading 关闭、图表容器真正挂载后再 init，否则 ref 为 null 画不出饼图
  if (data && sentimentTotal.value > 0) {
    await nextTick()
    initChart(data)
  }
}

watch(
  () => route.params.id,
  () => {
    loadSentiment()
  }
)

onMounted(async () => {
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
  loadFavoriteState()
  loadSentiment()
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
.emotion-chart {
  width: 100%;
  height: 320px;
}
.emotion-empty {
  width: 100%;
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
