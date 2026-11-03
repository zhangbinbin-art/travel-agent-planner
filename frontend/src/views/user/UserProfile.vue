<template>
  <div class="user-profile">
    <div class="profile-top">
      <el-button text class="back-btn" @click="goBack">← 返回</el-button>
    </div>

    <!-- 被对方拉黑：整页提示 -->
    <section v-if="blockedByTarget" class="page-card blocked-card">
      <EmptyState description="你已被该用户拉黑，无法访问主页" hint="如有疑问可联系对方解除拉黑" />
    </section>

    <template v-else>
      <!-- ① 个人信息卡片 -->
      <section class="page-card profile-card" v-loading="loading">
        <div class="profile-main">
          <div class="avatar-lg" :style="{ background: avatarColor(username) }">
            {{ avatarText(username) }}
          </div>

          <div class="profile-info">
            <h2 class="profile-name">{{ username || '用户主页' }}</h2>
            <p class="profile-bio">{{ bio }}</p>
            <div class="profile-stats">
              <span class="stat"><strong>{{ postCount }}</strong> 帖子</span>
              <span class="stat"><strong>{{ followerCount }}</strong> 粉丝</span>
              <span class="stat"><strong>{{ followingCount }}</strong> 关注</span>
            </div>
          </div>

          <!-- 自己主页不显示关注/私聊/更多 -->
          <div v-if="!isSelf" class="profile-actions">
            <el-button
              :type="isFollowing ? 'default' : 'primary'"
              :loading="followLoading"
              @click="handleToggleFollow"
            >
              {{ isFollowing ? '已关注' : '关注' }}
            </el-button>

            <el-tooltip :disabled="!chatDisabled" content="无法发起私聊" placement="top">
              <span class="chat-btn-wrap">
                <el-button :disabled="chatDisabled" @click="openChat">私聊</el-button>
              </span>
            </el-tooltip>

            <el-dropdown trigger="click" @command="handleBlockCommand">
              <el-button circle class="more-btn" aria-label="更多操作">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="toggle">
                    {{ iBlocked ? '解除拉黑' : '拉黑该用户' }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </section>

      <!-- ② 帖子列表 -->
      <section class="page-card posts-card">
        <header class="posts-head">
          <h3 class="posts-title">发布的游记 / 攻略</h3>
          <span v-if="total" class="posts-count">共 {{ total }} 篇</span>
        </header>

        <div v-loading="postLoading" class="posts-body">
          <div v-if="posts.length" class="post-grid">
            <PostCard v-for="post in posts" :key="post.id" :post="post" />
          </div>
          <EmptyState
            v-else-if="!postLoading"
            description="该用户暂未发布游记攻略"
            hint="关注TA，有更新更容易被发现"
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
      </section>

      <ChatDialog v-model="chatVisible" :target-user-id="userId" :target-name="username" />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MoreFilled } from '@element-plus/icons-vue'
import { getUserProfile, getUserPosts, toggleFollow, toggleBlock } from '@/api/social'
import PostCard from '@/components/PostCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChatDialog from '@/components/message/ChatDialog.vue'

const AVATAR_COLORS = ['#ff7a2f', '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#5b8ff9']

const route = useRoute()
const router = useRouter()

const userId = computed(() => Number(route.params.userId))
const loading = ref(false)
const postLoading = ref(false)

const user = ref({})
const bio = ref('')
const postCount = ref(0)
const followerCount = ref(0)
const followingCount = ref(0)
const isFollowing = ref(false)
const viewerIsSelf = ref(false)
const iBlocked = ref(false)
const blockedByTarget = ref(false)
const followLoading = ref(false)
const chatVisible = ref(false)

const posts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)

const username = computed(() => user.value.username || '')
const isSelf = computed(() => viewerIsSelf.value)
// 双方任一拉黑 -> 不允许私聊
const chatDisabled = computed(() => iBlocked.value || blockedByTarget.value)

const avatarText = (name) => {
  const text = String(name || '').trim()
  return text ? Array.from(text)[0].toUpperCase() : '?'
}

const avatarColor = (name) => {
  let sum = 0
  for (const ch of String(name || '')) sum += ch.codePointAt(0) || 0
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}

const goBack = () => {
  if (window.history.length > 1) router.back()
  else router.push('/strategy')
}

const loadProfile = async () => {
  loading.value = true
  try {
    const res = await getUserProfile(userId.value)
    const data = res.data || {}
    user.value = data.user || {}
    bio.value = data.bio || '这个人很懒，还没有填写简介'
    postCount.value = Number(data.post_count) || 0
    followerCount.value = Number(data.follower_count) || 0
    followingCount.value = Number(data.following_count) || 0
    isFollowing.value = !!data.is_following
    viewerIsSelf.value = !!data.viewer_is_self
    iBlocked.value = !!data.i_blocked
    blockedByTarget.value = !!data.blocked_by_target
  } catch (e) {
    if (e?.response?.status === 403) {
      blockedByTarget.value = true
      return
    }
    ElMessage.error(e?.response?.data?.detail || '获取用户主页失败')
  } finally {
    loading.value = false
  }
}

const loadPosts = async () => {
  postLoading.value = true
  try {
    const res = await getUserPosts(userId.value, { page: page.value, page_size: pageSize.value })
    posts.value = res.data?.items || []
    total.value = Number(res.data?.total) || 0
  } catch (e) {
    if (e?.response?.status === 403) {
      blockedByTarget.value = true
      posts.value = []
      total.value = 0
      return
    }
    posts.value = []
    total.value = 0
  } finally {
    postLoading.value = false
  }
}

const handleToggleFollow = async () => {
  if (followLoading.value) return
  followLoading.value = true
  try {
    const res = await toggleFollow(userId.value)
    const data = res.data || {}
    isFollowing.value = !!data.following
    followerCount.value = Number(data.follower_count) || 0
    followingCount.value = Number(data.following_count) || 0
    ElMessage.success(isFollowing.value ? '关注成功' : '已取消关注')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    followLoading.value = false
  }
}

const openChat = () => {
  if (chatDisabled.value) {
    ElMessage.warning('无法发起私聊')
    return
  }
  chatVisible.value = true
}

const handleBlockCommand = async (command) => {
  if (command !== 'toggle') return
  try {
    const res = await toggleBlock(userId.value)
    const data = res.data || {}
    iBlocked.value = !!data.blocked
    ElMessage.success(iBlocked.value ? '已拉黑该用户' : '已解除拉黑')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const handlePageChange = (val) => {
  page.value = val
  loadPosts()
}

const loadAll = () => {
  page.value = 1
  loadProfile()
  loadPosts()
}

watch(
  () => route.params.userId,
  () => {
    if (route.params.userId) loadAll()
  }
)

loadAll()
</script>

<style scoped>
.user-profile {
  max-width: 1320px;
  margin: 0 auto;
  padding: 16px;
  box-sizing: border-box;
}

.profile-top {
  margin-bottom: 10px;
}

.back-btn {
  font-weight: 600;
  color: #3d4753;
}

.page-card {
  background: #fff;
  border: 2px solid #222;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(34, 34, 34, 0.08);
  padding: 16px;
  box-sizing: border-box;
}

.blocked-card {
  padding: 40px 16px;
}

/* ================= 个人信息 ================= */
.profile-card {
  margin-bottom: 18px;
}

.profile-main {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  flex-wrap: wrap;
}

.avatar-lg {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid #222;
  color: #fff;
  font-size: 28px;
  font-weight: 800;
}

.profile-info {
  flex: 1 1 240px;
  min-width: 0;
}

.profile-name {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 800;
  color: #222;
}

.profile-bio {
  margin: 0 0 10px;
  font-size: 13px;
  color: #7b8794;
  line-height: 1.6;
}

.profile-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #5a6472;
}

.profile-stats strong {
  font-size: 15px;
  color: #222;
  margin-right: 2px;
}

.profile-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.chat-btn-wrap {
  display: inline-flex;
}

.more-btn {
  width: 34px;
  height: 34px;
}

/* ================= 帖子列表 ================= */
.posts-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px dashed rgba(34, 34, 34, 0.12);
}

.posts-title {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: #222;
}

.posts-count {
  font-size: 13px;
  color: #7b8794;
}

.post-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 18px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
