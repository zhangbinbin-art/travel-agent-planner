<template>
  <div class="post-detail" v-loading="loading">
    <el-card v-if="post">
      <template #header>
        <div class="detail-header">
          <span class="detail-title" :title="post.title">{{ post.title }}</span>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button v-if="canManage" @click="goEdit">编辑</el-button>
            <el-button v-if="canManage" type="danger" @click="handleDeletePost">删除</el-button>
          </div>
        </div>
      </template>

      <div class="post-meta">
        <span>作者：{{ authorName }}</span>
        <span>发布时间：{{ formattedTime }}</span>
        <span>热度：{{ post.heat ?? 0 }}</span>
      </div>
      <el-divider />
      <div class="post-content">{{ post.content }}</div>

      <el-divider content-position="left">评论 ({{ comments.length }})</el-divider>

      <div v-if="!auth.token" class="comment-login">
        <el-input readonly placeholder="登录后参与评论" class="login-input" @click="promptLogin" />
        <el-button type="primary" @click="promptLogin">登录</el-button>
      </div>
      <div v-else class="comment-form">
        <el-input
          v-model="commentContent"
          type="textarea"
          :rows="3"
          placeholder="写下你的评论…"
        />
        <div class="comment-form-foot">
          <div class="score-wrap">
            <span class="score-label">评分</span>
            <el-input-number v-model="commentScore" :min="1" :max="5" />
          </div>
          <el-button type="primary" :loading="submitting" @click="handleSubmitComment">发表评论</el-button>
        </div>
      </div>

      <div class="comment-list">
        <el-card v-for="c in comments" :key="c.id" shadow="never" class="comment-item">
          <div class="comment-head">
            <div class="comment-info">
              <span class="comment-author">{{ c.author?.username || '匿名' }}</span>
              <span class="comment-time">{{ formatTime(c.created_at) }}</span>
              <el-tag size="small" type="warning">{{ c.score }} 分</el-tag>
            </div>
            <el-button
              v-if="canDeleteComment(c)"
              size="small"
              type="danger"
              @click="handleDeleteComment(c)"
            >
              删除
            </el-button>
          </div>
          <div class="comment-content">{{ c.content }}</div>
        </el-card>
        <el-empty v-if="!comments.length" description="暂无评论" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPostDetail, deletePost } from '@/api/post'
import { createComment, deleteComment } from '@/api/comment'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const post = ref(null)
const comments = ref([])
const loading = ref(false)
const submitting = ref(false)
const commentContent = ref('')
const commentScore = ref(5)

const canManage = computed(
  () =>
    !!post.value &&
    (auth.role === 'admin' || (auth.userId !== null && auth.userId === post.value.user_id))
)

const authorName = computed(() => post.value?.author?.username || '匿名')
const formattedTime = computed(() => formatTime(post.value?.created_at))

const canDeleteComment = (comment) =>
  auth.role === 'admin' || (auth.userId !== null && auth.userId === comment.user_id)

function formatTime(value) {
  if (value === null || value === undefined || value === '') return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
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

const promptLogin = () => {
  ElMessage.warning('请先登录')
  router.push('/login')
}

const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await getPostDetail(route.params.id)
    post.value = res.data || null
    comments.value = res.data?.comments || []
  } catch (e) {
    if (e?.response?.status === 404) {
      ElMessage.error('游记不存在')
      router.push('/post-list')
    } else {
      ElMessage.error(extractError(e, '获取游记详情失败'))
    }
  } finally {
    loading.value = false
  }
}

const goList = () => {
  router.push('/post-list')
}

const goEdit = () => {
  if (!auth.token) {
    promptLogin()
    return
  }
  router.push(`/post-edit/${post.value.id}`)
}

const handleDeletePost = async () => {
  if (!auth.token) {
    promptLogin()
    return
  }
  try {
    await ElMessageBox.confirm('确定删除这篇游记吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deletePost(post.value.id)
    ElMessage.success('删除成功')
    router.push('/post-list')
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

const handleSubmitComment = async () => {
  if (!auth.token) {
    promptLogin()
    return
  }
  if (!commentContent.value.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }
  submitting.value = true
  try {
    await createComment(route.params.id, {
      content: commentContent.value.trim(),
      score: commentScore.value
    })
    ElMessage.success('评论成功')
    commentContent.value = ''
    commentScore.value = 5
    await fetchDetail()
  } catch (e) {
    ElMessage.error(extractError(e, '评论失败'))
  } finally {
    submitting.value = false
  }
}

const handleDeleteComment = async (comment) => {
  if (!auth.token) {
    promptLogin()
    return
  }
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteComment(comment.id)
    ElMessage.success('删除成功')
    await fetchDetail()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.post-detail {
  max-width: 960px;
  margin: 0 auto;
}
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.detail-title {
  font-weight: 600;
  font-size: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.post-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #909399;
  font-size: 13px;
}
.post-content {
  white-space: pre-wrap;
  color: #303133;
  line-height: 1.8;
  word-break: break-word;
}
.comment-login {
  display: flex;
  gap: 12px;
  align-items: center;
}
.login-input {
  flex: 1;
}
.comment-form-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}
.score-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.score-label {
  color: #606266;
  font-size: 14px;
}
.comment-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.comment-item {
  border: 1px solid #ebeef5;
}
.comment-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.comment-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.comment-author {
  font-weight: 600;
  color: #303133;
}
.comment-time {
  color: #909399;
  font-size: 12px;
}
.comment-content {
  margin-top: 8px;
  white-space: pre-wrap;
  color: #606266;
  line-height: 1.7;
  word-break: break-word;
}
</style>
