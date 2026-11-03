<template>
  <div class="post-page">
    <section class="page-card" v-loading="loading">
      <header class="page-head">
        <div class="page-heading">
          <span class="tr-section-sub">Strategy</span>
          <h1 class="tr-section-title">旅游攻略</h1>
        </div>
        <div class="page-search">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索游记标题"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
      </header>

      <div class="action-bar">
        <button
          type="button"
          class="chip"
          :class="{ 'is-active': sort === 'latest' }"
          @click="switchSort('latest')"
        >
          最新发布
        </button>
        <button
          type="button"
          class="chip"
          :class="{ 'is-active': sort === 'hot' }"
          @click="switchSort('hot')"
        >
          热门排序
        </button>
        <button type="button" class="chip" @click="goMyPosts">我的攻略</button>
        <button v-if="auth.token" type="button" class="chip chip--primary" @click="goCreate">
          发布攻略
        </button>
        <el-button text class="reset-btn" @click="reset">清空筛选</el-button>
      </div>

      <div v-if="posts.length" class="post-grid">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
      <EmptyState v-else-if="loaded" description="暂无游记" hint="发布你的第一篇攻略吧" />

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
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPostList, deletePost } from '@/api/post'
import { auth } from '@/utils/auth'
import PostCard from '@/components/PostCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const route = useRoute()

const filters = reactive({ keyword: String(route.query.keyword || '') })
const posts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const loading = ref(false)
const loaded = ref(false)
const sort = ref('latest')

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

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getPostList({
      keyword: filters.keyword || undefined,
      page: page.value,
      page_size: pageSize.value,
      sort: sort.value
    })
    posts.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    ElMessage.error(extractError(e, '获取游记列表失败'))
  } finally {
    loading.value = false
    loaded.value = true
  }
}

const handleSearch = () => {
  page.value = 1
  fetchList()
}

const reset = () => {
  filters.keyword = ''
  page.value = 1
  fetchList()
}

// 顶部导航栏搜索：同步 keyword 查询参数
watch(
  () => route.query.keyword,
  (val) => {
    const next = String(val || '')
    if (next === filters.keyword) return
    filters.keyword = next
    page.value = 1
    fetchList()
  }
)

const handleSortChange = () => {
  page.value = 1
  fetchList()
}

const switchSort = (value) => {
  if (sort.value === value) return
  sort.value = value
  handleSortChange()
}

const goMyPosts = () => {
  if (!auth.token) {
    router.push({ path: '/login', query: { redirect: '/user' } })
    return
  }
  router.push('/user?tab=post')
}

const handlePageChange = (p) => {
  page.value = p
  fetchList()
}

const goCreate = () => {
  router.push('/post-edit')
}

const handleEdit = (post) => {
  router.push(`/post-edit/${post.id}`)
}

const handleDelete = async (post) => {
  try {
    await ElMessageBox.confirm('确定删除这篇游记吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deletePost(post.id)
    ElMessage.success('删除成功')
    await fetchList()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

onMounted(() => {
  fetchList()
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
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.search-form {
  margin-bottom: 0;
}
.post-col {
  margin-bottom: 16px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

/* ===== 页面容器（与旅游景点页统一） ===== */
.post-page {
  max-width: 1320px;
  margin: 0 auto;
  padding-bottom: 24px;
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
  width: 240px;
}
.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 0 16px;
  margin-bottom: 16px;
  border-top: 1px dashed rgba(34, 34, 34, 0.12);
}
.chip {
  padding: 6px 16px;
  border: 2px solid rgba(34, 34, 34, 0.14);
  border-radius: 999px;
  background: #fff;
  color: #3d4753;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}
.chip:hover {
  background: #eef6ff;
  border-color: #222;
}
.chip.is-active {
  background: #fff1e6;
  border-color: #222;
  color: #f06818;
}
.chip--primary {
  background: #ff7a2f;
  border-color: #ff7a2f;
  color: #fff;
}
.chip--primary:hover {
  background: #f06818;
  border-color: #f06818;
  color: #fff;
}
.reset-btn {
  margin-left: auto;
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
  margin-top: 22px;
}
</style>
