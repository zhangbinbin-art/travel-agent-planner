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
      <el-divider>评论情感占比（预留）</el-divider>
      <div id="emotion-chart" class="emotion-chart"></div>
      <el-divider>评论列表</el-divider>
      <el-table :data="comments" style="width: 100%">
        <el-table-column prop="user" label="用户" width="120" />
        <el-table-column prop="content" label="评论内容" />
        <el-table-column prop="score" label="评分" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSpotDetail } from '@/api/spot'
import { addFavorite, removeFavorite, getMyFavorites } from '@/api/favorite'
import { mockComments } from '@/api/mock'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const spot = ref({})
const comments = ref(mockComments)
const isFavorited = ref(false)
const favoriteLoading = ref(false)

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
    router.push('/login')
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
      router.push('/login')
      return
    }
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    favoriteLoading.value = false
  }
}

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
})
</script>

<style scoped>
.emotion-chart {
  width: 100%;
  height: 320px;
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}
.emotion-chart::after {
  content: 'ECharts 情感占比饼图预留位置（jieba + SnowNLP）';
}
</style>
