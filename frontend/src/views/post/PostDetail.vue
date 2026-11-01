<template>
  <div class="post-detail" v-loading="loading">
    <div class="detail-inner">
      <el-card v-if="post" class="detail-card" shadow="never">
        <template #header>
          <div class="detail-header">
            <div class="detail-title-block">
              <h1 class="detail-title" :title="post.title">{{ post.title }}</h1>
              <div class="post-meta">
                <span>点赞：{{ post.like_count ?? 0 }}</span>
                <span>评论：{{ post.comment_count ?? 0 }}</span>
                <span>热度：{{ post.heat ?? 0 }}</span>
                <el-tag v-if="canManage && post.status !== 1" :type="post.status === 2 ? 'danger' : 'warning'" size="small">
                  {{ post.status_text || (post.status === 0 ? '待审核' : '已驳回') }}
                </el-tag>
                <span v-if="canManage && post.status !== 1" class="status-hint">审核通过后才会公开展示</span>
              </div>
              <div v-if="locationTags.length" class="post-location">
                <el-icon class="location-icon"><Location /></el-icon>
                <el-tag
                  v-for="item in locationTags"
                  :key="item.key"
                  size="small"
                  class="location-tag"
                  :class="{ 'is-custom': item.custom }"
                  @click="item.spotId ? goSpot(item.spotId) : null"
                >
                  {{ item.label }}
                </el-tag>
              </div>
            </div>
            <div class="header-actions">
              <el-button
                class="fav-btn"
                size="small"
                :class="{ 'is-favorited': post.favorited }"
                :loading="favoriting"
                @click="handleFavorite"
              >
                <el-icon class="fav-icon">
                  <StarFilled v-if="post.favorited" />
                  <Star v-else />
                </el-icon>
                <span class="fav-label">{{ post.favorited ? '已收藏' : '收藏' }}</span>
                <span class="fav-count">{{ post.favorite_count ?? 0 }}</span>
              </el-button>
              <el-dropdown trigger="click" @command="copyLink">
                <el-button size="small">
                  <el-icon class="share-icon"><Share /></el-icon>
                  <span>分享</span>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="copy">
                      <el-icon><Link /></el-icon>
                      复制链接
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button size="small" @click="goList">返回列表</el-button>
              <el-button v-if="canManage" size="small" @click="goEdit">编辑</el-button>
              <el-button v-if="canManage" size="small" type="danger" plain @click="handleDeletePost">删除</el-button>
            </div>
          </div>

          <div class="author-card">
            <div class="author-avatar" :style="{ backgroundColor: avatarColor }">{{ avatarText }}</div>
            <div class="author-main">
              <span class="author-name">{{ authorName }}</span>
              <span class="author-sub">
                <span>{{ formattedTime }}</span>
                <span class="author-sep">·</span>
                <span>浏览 {{ post.view_count ?? 0 }}</span>
              </span>
            </div>
          </div>
        </template>

        <div v-if="imageList.length" class="post-gallery">
          <el-carousel
            v-if="imageList.length > 1"
            class="post-carousel"
            :autoplay="false"
            indicator-position="outside"
            arrow="hover"
            trigger="click"
          >
            <el-carousel-item v-for="(src, idx) in imageList" :key="idx">
              <el-image
                class="gallery-image"
                :src="src"
                fit="cover"
                :preview-src-list="imageList"
                :initial-index="idx"
                preview-teleported
                @error="onCoverError"
              />
            </el-carousel-item>
          </el-carousel>
          <el-image
            v-else
            class="gallery-single"
            :src="imageList[0]"
            fit="cover"
            :preview-src-list="imageList"
            :initial-index="0"
            preview-teleported
            @error="onCoverError"
          />
        </div>

        <div class="post-content">{{ post.content }}</div>

        <div class="post-stats">
          <span>点赞 {{ post.like_count ?? 0 }}</span>
          <span class="stats-dot">·</span>
          <span>收藏 {{ post.favorite_count ?? 0 }}</span>
          <span class="stats-dot">·</span>
          <span>评论 {{ post.comment_count ?? 0 }}</span>
          <span class="stats-dot">·</span>
          <span>浏览 {{ post.view_count ?? 0 }}</span>
        </div>

        <div class="post-actions-row">
          <el-button class="like-btn" :type="post.liked ? 'primary' : 'default'" @click="handleLike">
            <svg class="like-heart" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 20.4 4.9 13.3a4.6 4.6 0 0 1 0-6.5 4.6 4.6 0 0 1 6.5 0l.6.6.6-.6a4.6 4.6 0 0 1 6.5 0 4.6 4.6 0 0 1 0 6.5Z"
                :fill="post.liked ? 'currentColor' : 'none'"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <span>{{ post.liked ? '已点赞' : '点赞' }}（{{ post.like_count ?? 0 }}）</span>
          </el-button>
        </div>

        <el-divider content-position="left">评论 ({{ commentTotal }})</el-divider>

        <div v-if="!auth.token" class="comment-login">
          <span>请先登录后评论</span>
          <el-button type="primary" link @click="promptLogin">去登录</el-button>
        </div>
        <div v-else class="comment-form">
          <el-input
            v-model="commentContent"
            class="comment-input"
            type="textarea"
            :rows="5"
            placeholder="写下你的评论…"
          />
          <div class="score-wrap">
            <span class="score-label">评分</span>
            <el-input-number v-model="commentScore" :min="1" :max="5" />
          </div>
          <div class="comment-form-foot">
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
                <el-tag v-if="c.status !== undefined && c.status !== 1" size="small" :type="c.status === 2 ? 'danger' : 'warning'">
                  {{ c.status_text || (c.status === 0 ? '待审核' : '已驳回') }}
                </el-tag>
              </div>
              <div class="comment-actions">
                <el-button size="small" :type="c.liked ? 'primary' : 'default'" @click="handleLikeComment(c)">
                  点赞（{{ c.like_count ?? 0 }}）
                </el-button>
                <el-button
                  v-if="canDeleteComment(c)"
                  size="small"
                  type="danger"
                  @click="handleDeleteComment(c)"
                >
                  删除
                </el-button>
              </div>
            </div>
            <div class="comment-content">{{ c.content }}</div>
          </el-card>
          <el-empty v-if="!comments.length" description="暂无评论" :image-size="60" />
        </div>
        <el-pagination
          v-if="commentTotal > 0"
          class="comment-pager"
          background
          layout="prev, pager, next"
          :total="commentTotal"
          :page-size="commentPageSize"
          :current-page="commentPage"
          @current-change="handleCommentPageChange"
        />

        <div v-if="relatedPosts.length" class="related-block">
          <div class="related-title">相关推荐</div>
          <div class="related-scroll">
            <div
              v-for="item in relatedPosts"
              :key="item.id"
              class="related-item"
              @click="router.push('/post-detail/' + item.id)"
            >
              <el-image v-if="item.cover" class="related-cover" :src="item.cover" fit="cover">
                <template #error>
                  <div class="related-cover-ph">暂无图片</div>
                </template>
              </el-image>
              <div v-else class="related-cover-ph">暂无图片</div>
              <div class="related-item-body">
                <div class="related-item-title">{{ item.title }}</div>
                <div class="related-item-meta">浏览量 {{ item.view_count ?? 0 }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled, Share, Link, Location } from '@element-plus/icons-vue'
import {
  getPostDetail,
  deletePost,
  likePost,
  getCommentList,
  createPostComment,
  getPostList,
  togglePostFavorite
} from '@/api/post'
import { deleteComment, likeComment } from '@/api/comment'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

// 关联地点：已有景点（可跳详情）+ 自定义地区（仅展示）
const locationTags = computed(() => {
  const list = []
  const spots = Array.isArray(post.value?.spots) ? post.value.spots : []
  spots.forEach((s) => {
    if (!s || s.id === undefined || s.id === null) return
    list.push({
      key: `spot-${s.id}`,
      label: s.city ? `${s.name} · ${s.city}` : String(s.name || ''),
      spotId: s.id,
      custom: false
    })
  })
  const customSpots = Array.isArray(post.value?.custom_spots) ? post.value.custom_spots : []
  customSpots.forEach((name, idx) => {
    const text = String(name || '').trim()
    if (!text) return
    list.push({ key: `custom-${idx}`, label: text, spotId: null, custom: true })
  })
  return list.filter((item) => item.label)
})

const goSpot = (id) => {
  router.push(`/spot-detail/${id}`)
}

const post = ref(null)
const comments = ref([])
const loading = ref(false)
const submitting = ref(false)
const commentContent = ref('')
const commentScore = ref(5)
const coverError = ref(false)
const commentPage = ref(1)
const commentPageSize = ref(10)
const commentTotal = ref(0)
const favoriting = ref(false)
const relatedPosts = ref([])

const canManage = computed(
  () =>
    !!post.value &&
    (auth.role === 'admin' || (auth.userId !== null && auth.userId === post.value.user_id))
)

const authorName = computed(() => post.value?.author?.username || '匿名')
const formattedTime = computed(() => formatTime(post.value?.created_at))

const imageList = computed(() => {
  const arr = (post.value?.images || []).filter((s) => typeof s === 'string' && s.trim())
  if (arr.length) return arr
  return post.value?.cover ? [post.value.cover] : []
})

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#909399', '#8e7cc3', '#2f9e7e']

const avatarText = computed(() =>
  (post.value?.author?.username || '匿').trim().charAt(0).toUpperCase()
)

const avatarColor = computed(() => {
  const name = (post.value?.author?.username || '匿').trim()
  let hash = 0
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) % 100000
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
})

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
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

const onCoverError = () => {
  coverError.value = true
}

const fetchComments = async () => {
  try {
    const res = await getCommentList(route.params.id, {
      page: commentPage.value,
      page_size: commentPageSize.value
    })
    comments.value = res.data?.items || []
    commentTotal.value = res.data?.total || 0
  } catch (e) {
    comments.value = []
    commentTotal.value = 0
  }
}

const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await getPostDetail(route.params.id)
    post.value = res.data || null
    await fetchComments()
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

const fetchRelated = async () => {
  try {
    const res = await getPostList({ page: 1, page_size: 8 })
    const items = res.data?.items || []
    relatedPosts.value = items
      .filter((item) => String(item.id) !== String(route.params.id))
      .slice(0, 6)
  } catch (e) {
    relatedPosts.value = []
  }
}

const handleFavorite = async () => {
  if (!auth.token) {
    promptLogin()
    return
  }
  if (favoriting.value) return
  favoriting.value = true
  try {
    const res = await togglePostFavorite(route.params.id)
    post.value.favorited = !!res.data?.favorited
    post.value.favorite_count = res.data?.favorite_count ?? 0
    ElMessage.success(res.data?.message || (post.value.favorited ? '收藏成功' : '已取消收藏'))
  } catch (e) {
    ElMessage.error(extractError(e, '操作失败'))
  } finally {
    favoriting.value = false
  }
}

const copyLink = async () => {
  const link = window.location.href
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(link)
    } else {
      const ta = document.createElement('textarea')
      ta.value = link
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('链接已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动复制地址栏链接')
  }
}

const handleCommentPageChange = (p) => {
  commentPage.value = p
  fetchComments()
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

const handleLike = async () => {
  if (!auth.token) {
    promptLogin()
    return
  }
  try {
    const res = await likePost(post.value.id)
    if (post.value) {
      post.value.liked = res.data?.liked
      post.value.like_count = res.data?.like_count
    }
  } catch (e) {
    ElMessage.error(extractError(e, '点赞失败'))
  }
}

const handleLikeComment = async (comment) => {
  if (!auth.token) {
    promptLogin()
    return
  }
  try {
    const res = await likeComment(comment.id)
    comment.liked = res.data?.liked
    comment.like_count = res.data?.like_count
  } catch (e) {
    ElMessage.error(extractError(e, '点赞失败'))
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
    await createPostComment(route.params.id, {
      content: commentContent.value.trim(),
      score: commentScore.value
    })
    ElMessage.success('评论成功')
    commentContent.value = ''
    commentScore.value = 5
    commentPage.value = 1
    await fetchComments()
    if (post.value) {
      post.value.comment_count = (post.value.comment_count || 0) + 1
    }
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
    await fetchComments()
    if (post.value && post.value.comment_count > 0) {
      post.value.comment_count -= 1
    }
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

onMounted(() => {
  fetchDetail()
  fetchRelated()
})
</script>

<style scoped>
/* ---------- A. 外层容器与卡片 ---------- */
.post-detail {
  margin: -20px;
  padding: 20px;
  min-height: calc(100vh - 60px);
  box-sizing: border-box;
  background: #f5f8fa;
}
.detail-inner {
  max-width: 860px;
  margin: 0 auto;
}
.detail-card {
  border: none;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
.detail-card :deep(.el-card__header) {
  padding: 28px 32px 22px;
  border-bottom: none;
}
.detail-card :deep(.el-card__body) {
  padding: 24px 32px 32px;
}

/* ---------- B. 标题与元信息 ---------- */
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}
.detail-title-block {
  flex: 1 1 320px;
  min-width: 0;
}
.detail-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.3px;
  color: #2c3e50;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.post-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px 18px;
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #909399;
}
.post-meta :deep(.el-tag) {
  height: 20px;
  padding: 0 7px;
  font-size: 12px;
  border-radius: 4px;
}
.status-hint {
  font-size: 12px;
  color: #c0c4cc;
}

/* ---------- C. 作者信息卡 ---------- */
.author-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #f8fafc;
}
.author-avatar {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  line-height: 1;
  user-select: none;
}
.author-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.author-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.author-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: #909399;
}
.author-sep {
  color: #c0c4cc;
}

/* ---------- D. 图片区（轮播 / 单图） ---------- */
.post-gallery {
  margin: 8px 0 28px;
}
.post-carousel :deep(.el-carousel__container) {
  height: 380px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
}
.post-carousel :deep(.el-carousel__item) {
  display: flex;
  align-items: center;
  background: #f5f7fa;
}
.post-carousel :deep(.el-carousel__indicators--outside) {
  margin-top: 10px;
}
.post-carousel :deep(.el-carousel__indicator .el-carousel__button) {
  width: 22px;
  height: 4px;
  border-radius: 2px;
}
.post-carousel :deep(.el-carousel__indicator.is-active .el-carousel__button) {
  background-color: #409eff;
}
.gallery-image {
  width: 100%;
  height: 100%;
}
.gallery-image :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gallery-single {
  display: block;
  width: 100%;
  height: 420px;
  max-height: 420px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
}
.gallery-single :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ---------- E. 正文 ---------- */
.post-content {
  margin: 0;
  font-size: 15.5px;
  line-height: 1.7;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---------- F. 正文底部统计行 ---------- */
.post-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 18px 0 20px;
  font-size: 13px;
  color: #a8abb2;
}
.stats-dot {
  color: #d4d7de;
}

/* ---------- G. 互动区 ---------- */
.post-actions-row {
  display: flex;
  justify-content: center;
  padding: 0 0 4px;
}
.like-btn {
  height: 36px;
  padding: 0 20px;
  border-radius: 999px;
  color: #606266;
  border-color: #dcdfe6;
  background: #fff;
  transition: all 0.2s ease;
}
.like-btn:hover {
  color: #409eff;
  border-color: #409eff;
  background: #ecf5ff;
}
.like-btn.el-button--primary {
  color: #fff;
  background: #409eff;
  border-color: #409eff;
}
.like-btn.el-button--primary:hover {
  color: #fff;
  background: #66b1ff;
  border-color: #66b1ff;
}
.like-heart {
  width: 15px;
  height: 15px;
  margin-right: 6px;
  flex-shrink: 0;
  vertical-align: -2px;
  transition: transform 0.2s ease;
}
.like-btn:hover .like-heart {
  transform: scale(1.12);
}
.like-btn:active .like-heart {
  transform: scale(0.94);
}

/* 分割线（评论标题） */
.detail-card :deep(.el-divider--horizontal) {
  margin: 28px 0;
  border-top-color: #f0f2f5;
}
.detail-card :deep(.el-divider__text) {
  padding: 0 14px 0 0;
  background: #fff;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.detail-card :deep(.el-divider--horizontal .el-divider__text.is-left) {
  left: 0;
}

/* ---------- H. 评论输入框 / 空状态 / 分页 ---------- */
.comment-login {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-radius: 12px;
  background: #fafbfc;
  font-size: 14px;
  color: #909399;
}
.comment-form {
  padding: 16px;
  border-radius: 12px;
  background: #fafbfc;
}
.comment-form :deep(.el-textarea__inner) {
  padding: 12px 14px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px #e8ebf0 inset;
  font-size: 14px;
  line-height: 1.6;
  transition: box-shadow 0.2s ease;
}
.comment-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}
.score-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}
.score-label {
  font-size: 14px;
  color: #606266;
}
.comment-form-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
.comment-form-foot :deep(.el-button) {
  padding: 0 20px;
  border-radius: 8px;
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin-top: 4px;
}
.comment-item {
  border: 1px solid #f0f2f5;
  border-radius: 10px;
  box-shadow: none;
  transition: border-color 0.2s ease;
}
.comment-item:hover {
  border-color: #dbe4ee;
}
.detail-card :deep(.comment-item > .el-card__body) {
  padding: 16px;
}
.comment-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.comment-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
}
.comment-author {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.comment-time {
  font-size: 12px;
  color: #a8abb2;
}
.comment-actions {
  display: flex;
  gap: 8px;
}
.comment-actions :deep(.el-button) {
  height: 26px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 12px;
}
.comment-content {
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-list :deep(.el-empty) {
  padding: 20px 0;
}
.comment-list :deep(.el-empty__description p) {
  font-size: 13px;
  color: #c0c4cc;
}
.comment-pager {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* ---------- I. 相关推荐 ---------- */
.related-block {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid #f0f2f5;
}
.related-title {
  margin-bottom: 14px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.related-scroll {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding: 2px 2px 8px;
  scrollbar-width: none;
}
.related-scroll::-webkit-scrollbar {
  display: none;
}
.related-item {
  flex: 0 0 200px;
  width: 200px;
  overflow: hidden;
  border: 1px solid #f0f2f5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.related-item:hover {
  transform: translateY(-2px);
  border-color: #dbe4ee;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
}
.related-cover,
.related-cover-ph {
  display: block;
  width: 100%;
  height: 112px;
  background: #f2f4f7;
}
.related-cover-ph {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #c0c4cc;
}
.related-cover :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.related-item-body {
  padding: 9px 10px 11px;
}
.related-item-title {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  color: #303133;
  word-break: break-word;
}
.related-item-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #a8abb2;
}

/* ---------- J. 右上角操作按钮 ---------- */
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}
.header-actions :deep(.el-button) {
  height: 32px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 13px;
}
.header-actions :deep(.el-dropdown) {
  display: inline-flex;
}
.fav-btn {
  color: #909399;
}
.fav-btn .fav-icon {
  color: #c0c4cc;
  font-size: 15px;
  transition: color 0.2s ease;
}
.fav-btn .fav-count {
  margin-left: 5px;
  font-size: 13px;
  color: #909399;
  transition: color 0.2s ease;
}
.header-actions .fav-btn:hover {
  color: #e6a23c;
  border-color: #f2d692;
  background: #fffaf0;
}
.fav-btn:hover .fav-icon,
.fav-btn:hover .fav-count {
  color: #f7ba2a;
}
.fav-btn.is-favorited {
  color: #e6a23c;
  border-color: #f5deb0;
  background: #fffbf2;
}
.fav-btn.is-favorited .fav-icon {
  color: #f7ba2a;
}
.fav-btn.is-favorited .fav-count {
  color: #e6a23c;
}
.share-icon {
  font-size: 15px;
}

/* ---------- K. 响应式 ---------- */
@media (max-width: 768px) {
  .detail-card :deep(.el-card__header) {
    padding: 20px 18px 16px;
  }
  .detail-card :deep(.el-card__body) {
    padding: 18px;
  }
  .detail-header {
    gap: 14px;
  }
  .detail-title {
    font-size: 22px;
  }
  .header-actions {
    width: 100%;
  }
  .post-meta {
    gap: 10px 14px;
  }
  .author-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .post-gallery {
    margin: 4px 0 20px;
  }
  .post-carousel :deep(.el-carousel__container) {
    height: 240px;
  }
  .gallery-single {
    height: 240px;
    max-height: 240px;
  }
  .post-content {
    font-size: 15px;
  }
  .detail-card :deep(.el-divider--horizontal) {
    margin: 22px 0;
  }
  .related-item {
    flex-basis: 160px;
    width: 160px;
  }
  .related-cover,
  .related-cover-ph {
    height: 96px;
  }
}
.post-location {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.location-icon {
  color: #909399;
  font-size: 14px;
}
.post-location .location-tag.el-tag {
  cursor: pointer;
  border-radius: 6px;
  border-color: #dbe7fb;
  background: #f2f7ff;
  color: #409eff;
}
.post-location .location-tag.el-tag:hover {
  border-color: #409eff;
}
.post-location .location-tag.is-custom.el-tag {
  cursor: default;
  border-style: dashed;
  border-color: #e4e7ed;
  background: #fff;
  color: #606266;
}
.post-location .location-tag.is-custom.el-tag:hover {
  border-color: #e4e7ed;
}
</style>
