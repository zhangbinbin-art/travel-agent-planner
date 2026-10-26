<template>
  <div class="my-favorite">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="card-title">我的收藏</span>
        </div>
      </template>

      <div v-loading="loading">
        <el-row v-if="favorites.length" :gutter="16">
          <el-col v-for="item in favorites" :key="item.id" :xs="24" :sm="12" :md="8" class="favorite-col">
            <el-card shadow="hover" class="favorite-card" @click="goDetail(item.spot_id)">
              <div class="favorite-title">{{ getSpot(item).name || '未命名景点' }}</div>
              <div class="favorite-city">{{ getSpot(item).city }}</div>
              <div v-if="tagList(item).length" class="favorite-tags">
                <el-tag v-for="tag in tagList(item)" :key="tag" size="small">{{ tag }}</el-tag>
              </div>
              <div class="favorite-desc">{{ excerpt(item) }}</div>
              <div class="favorite-score">{{ getSpot(item).score }} 分</div>
              <div class="favorite-actions">
                <el-button size="small" @click.stop="goDetail(item.spot_id)">详情</el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :loading="removingId === item.spot_id"
                  @click.stop="handleRemove(item)"
                >
                  取消收藏
                </el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-else-if="!loading" description="还没有收藏的景点">
          <el-button type="primary" @click="goSpotList">去逛逛</el-button>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyFavoriteSpots, toggleFavorite } from '@/api/favorite'
import { auth } from '@/utils/auth'

const router = useRouter()

const favorites = ref([])
const loading = ref(false)
const removingId = ref(null)

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

const getSpot = (item) => item?.spot || {}

const tagList = (item) => {
  const tags = getSpot(item).tags
  if (Array.isArray(tags)) return tags
  if (typeof tags === 'string') return tags.split(/[,，;；]/).filter(Boolean)
  return []
}

const excerpt = (item) => {
  const desc = getSpot(item).description || getSpot(item).desc || '暂无简介'
  return desc.length > 80 ? `${desc.slice(0, 80)}…` : desc
}

const fetchFavorites = async () => {
  if (!auth.token) return
  loading.value = true
  try {
    const res = await getMyFavoriteSpots()
    favorites.value = res.data?.items || []
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.warning('请先登录')
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      return
    }
    ElMessage.error(extractError(e, '获取收藏列表失败'))
  } finally {
    loading.value = false
  }
}

const handleRemove = async (item) => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  removingId.value = item.spot_id
  try {
    await toggleFavorite(item.spot_id)
    favorites.value = favorites.value.filter((fav) => fav.id !== item.id)
    ElMessage.success('取消收藏成功')
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.warning('请先登录')
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      return
    }
    ElMessage.error(extractError(e, '取消收藏失败'))
  } finally {
    removingId.value = null
  }
}

const goDetail = (spotId) => {
  if (spotId === undefined || spotId === null) return
  router.push(`/spot-detail/${spotId}`)
}

const goSpotList = () => {
  router.push('/spot-list')
}

onMounted(() => {
  fetchFavorites()
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
.favorite-col {
  margin-bottom: 16px;
}
.favorite-card {
  cursor: pointer;
  height: 100%;
}
.favorite-title {
  font-weight: 600;
  font-size: 16px;
}
.favorite-city {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}
.favorite-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.favorite-desc {
  color: #606266;
  font-size: 13px;
  margin: 8px 0;
  min-height: 40px;
}
.favorite-score {
  color: #f59e0b;
}
.favorite-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
