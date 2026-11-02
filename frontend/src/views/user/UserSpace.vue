<template>
  <div class="user-space">
    <el-card class="profile-card" v-loading="loading">
      <div class="profile">
        <div class="avatar-lg" :style="{ background: avatarColor(username) }">
          {{ avatarText(username) }}
        </div>
        <div class="profile-main">
          <h2 class="profile-name">{{ username || '用户主页' }}</h2>
          <div v-if="hasStats" class="profile-stats">
            <span class="stat"><strong>{{ followingCount }}</strong> 关注</span>
            <span class="stat"><strong>{{ followerCount }}</strong> 粉丝</span>
          </div>
        </div>
        <div v-if="showActions" class="profile-actions">
          <el-button
            :type="isFollowing ? 'success' : 'primary'"
            :plain="isFollowing"
            :loading="followLoading"
            @click="handleToggleFollow"
          >
            {{ isFollowing ? '已关注' : '关注' }}
          </el-button>
          <el-button @click="chatVisible = true">发消息</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="posts-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">TA 的游记</span>
          <span v-if="total" class="card-count">共 {{ total }} 篇</span>
        </div>
      </template>

      <div v-loading="loading" class="posts-body">
        <el-row v-if="posts.length" :gutter="16">
          <el-col
            v-for="post in posts"
            :key="post.id"
            :xs="24"
            :sm="12"
            :md="8"
            :lg="6"
            class="post-col"
          >
            <PostCard :post="post" />
          </el-col>
        </el-row>

        <EmptyState
          v-else-if="!loading"
          description="TA 还没有公开游记"
          hint="仅展示公开游记，私密内容只有作者本人可见"
        />

        <div v-if="total > pageSize" class="pager">
          <el-pagination
            background
            layout="prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </el-card>

    <ChatDialog
      v-model="chatVisible"
      :target-user-id="userId"
      :target-name="username"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUserPosts, toggleFollow } from '@/api/social'
import PostCard from '@/components/PostCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChatDialog from '@/components/message/ChatDialog.vue'

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#5b8ff9']

const route = useRoute()

const user = ref({})
const posts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const loading = ref(false)
const isFollowing = ref(false)
const followLoading = ref(false)
const viewerIsSelf = ref(false)
const followingCount = ref(null)
const followerCount = ref(null)
const chatVisible = ref(false)

const userId = computed(() => Number(route.params.userId))
const username = computed(() => user.value.username || '')
const hasStats = computed(
  () => followingCount.value !== null && followerCount.value !== null
)
const showActions = computed(() => !viewerIsSelf.value && !!user.value.id)

const avatarText = (name) => {
  const text = String(name || '').trim()
  return text ? Array.from(text)[0].toUpperCase() : '?'
}

const avatarColor = (name) => {
  let sum = 0
  for (const ch of String(name || '')) sum += ch.codePointAt(0) || 0
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}

const countOrNull = (value) => (Number.isFinite(value) ? value : null)

const fetchUserData = async () => {
  if (!Number.isFinite(userId.value)) return
  loading.value = true
  try {
    const res = await getUserPosts(userId.value, { page: page.value, page_size: pageSize.value })
    const data = res.data || {}
    posts.value = data.items || []
    total.value = data.total || 0
    user.value = data.user || {}
    isFollowing.value = !!data.is_following
    viewerIsSelf.value = !!data.viewer_is_self
    followingCount.value = countOrNull(data.following_count)
    followerCount.value = countOrNull(data.follower_count)
  } catch (e) {
    posts.value = []
    total.value = 0
    ElMessage.error(e?.response?.data?.detail || '获取用户主页失败')
  } finally {
    loading.value = false
  }
}

const resetState = () => {
  user.value = {}
  posts.value = []
  total.value = 0
  isFollowing.value = false
  viewerIsSelf.value = false
  followingCount.value = null
  followerCount.value = null
}

const handleToggleFollow = async () => {
  if (!Number.isFinite(userId.value) || followLoading.value) return
  followLoading.value = true
  try {
    const res = await toggleFollow(userId.value)
    const data = res.data || {}
    isFollowing.value = !!data.following
    if (Number.isFinite(data.follower_count)) followerCount.value = data.follower_count
    ElMessage.success(isFollowing.value ? '已关注' : '已取消关注')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    followLoading.value = false
  }
}

const handlePageChange = (p) => {
  page.value = p
  fetchUserData()
}

// 同一路由切换 userId 时组件会复用，需要重置状态并重新拉取
watch(
  () => route.params.userId,
  () => {
    page.value = 1
    resetState()
    fetchUserData()
  },
  { immediate: true }
)
</script>

<style scoped>
.user-space {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.profile-card {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}
.profile {
  display: flex;
  align-items: center;
  gap: 18px;
}
.avatar-lg {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-size: 30px;
  font-weight: 600;
  user-select: none;
}
.profile-main {
  flex: 1;
  min-width: 0;
}
.profile-name {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.profile-stats {
  display: flex;
  gap: 20px;
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}
.profile-stats strong {
  margin-right: 4px;
  font-size: 15px;
  color: #2c3e50;
}
.profile-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.profile-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}
.posts-card {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
  color: #2c3e50;
}
.card-count {
  font-size: 13px;
  color: #909399;
}
.posts-body {
  min-height: 120px;
}
.post-col {
  margin-bottom: 16px;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 4px;
}
@media (max-width: 768px) {
  .profile {
    flex-wrap: wrap;
  }
  .profile-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
