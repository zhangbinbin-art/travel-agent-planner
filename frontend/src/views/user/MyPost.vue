<template>
  <div class="my-post" v-loading="loading">
    <template v-if="posts.length">
      <article v-for="p in posts" :key="p.id" class="post-card" @click="goDetail(p.id)">
        <div class="post-cover">
          <img v-if="coverOf(p)" :src="coverOf(p)" alt="" @error="onImgError" />
          <div v-else class="cover-fallback">{{ (p.title || '游').slice(0, 1) }}</div>
        </div>

        <div class="post-main">
          <div class="post-head">
            <h3 class="post-title" :title="p.title">{{ p.title }}</h3>
            <el-tag size="small" :type="statusType(p.status)" effect="light" class="post-status">
              {{ p.status_text || statusText(p.status) }}
            </el-tag>
          </div>
          <p class="post-excerpt">{{ excerpt(p.content) }}</p>
          <div class="post-foot">
            <span class="post-date">{{ formatDate(p.created_at) }}</span>
            <span class="post-stats">
              <span>浏览 {{ p.view_count ?? 0 }}</span>
              <span>点赞 {{ p.like_count ?? 0 }}</span>
              <span>评论 {{ p.comment_count ?? 0 }}</span>
            </span>
          </div>
        </div>

        <div class="post-actions">
          <el-button size="small" @click.stop="goDetail(p.id)">查看</el-button>
          <el-button size="small" type="primary" plain @click.stop="goEdit(p.id)">编辑</el-button>
        </div>
      </article>

      <p v-if="hasPending" class="status-tip">
        待审核的游记只有你自己能看到，审核通过后才会在游记广场公开展示。
      </p>

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
    </template>

    <EmptyState
      v-else-if="!loading"
      description="暂无帖子"
      hint="你发布的游记会显示在这里，待审核的也能看到"
    >
      <el-button type="primary" @click="goCreate">去发布游记</el-button>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyPosts } from '@/api/post'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()

const posts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)

const hasPending = computed(() => posts.value.some((p) => Number(p.status) === 0))

const statusText = (status) => {
  const s = Number(status)
  if (s === 1) return '已通过'
  if (s === 2) return '已驳回'
  if (s === 0) return '待审核'
  return '未知状态'
}

const statusType = (status) => {
  const s = Number(status)
  if (s === 1) return 'success'
  if (s === 2) return 'danger'
  return 'warning'
}

const coverOf = (p) => {
  const images = Array.isArray(p?.images) ? p.images : []
  const first = images.find((x) => typeof x === 'string' && x.trim())
  return first || p?.cover || ''
}

const onImgError = (e) => {
  e.target.style.display = 'none'
}

const excerpt = (text) => {
  const plain = String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!plain) return '暂无正文摘要'
  return plain.length > 80 ? plain.slice(0, 80) + '…' : plain
}

const formatDate = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const fetchPosts = async () => {
  loading.value = true
  try {
    const res = await getMyPosts({ page: page.value, page_size: pageSize.value })
    posts.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    posts.value = []
    total.value = 0
    ElMessage.error(e?.response?.data?.detail || '获取我的帖子失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p) => {
  page.value = p
  fetchPosts()
}

const goDetail = (id) => router.push(`/post-detail/${id}`)
const goEdit = (id) => router.push(`/post-edit/${id}`)
const goCreate = () => router.push('/post-edit')

onMounted(fetchPosts)
</script>

<style scoped>
.my-post {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}
.post-card {
  display: flex;
  align-items: stretch;
  gap: 14px;
  padding: 12px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 14px;
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.post-card:hover {
  border-color: #dbe7fb;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
.post-cover {
  width: 120px;
  height: 84px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f8fa;
}
.post-cover img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  font-size: 22px;
  font-weight: 600;
  background: #f2f7ff;
}
.post-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.post-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.post-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.post-status {
  flex-shrink: 0;
}
.post-excerpt {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.post-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #909399;
}
.post-stats {
  display: flex;
  gap: 12px;
}
.post-actions {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  flex-shrink: 0;
}
.post-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}
.status-tip {
  margin: 0;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fdf6ec;
  color: #b88230;
  font-size: 12px;
  line-height: 1.6;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 4px;
}
@media (max-width: 768px) {
  .post-card {
    flex-wrap: wrap;
  }
  .post-cover {
    width: 100%;
    height: 140px;
  }
  .post-actions {
    flex-direction: row;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
