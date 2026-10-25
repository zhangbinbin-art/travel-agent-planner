<template>
  <div class="post-list">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="card-title">游记列表</span>
          <el-button v-if="auth.token" type="primary" @click="goCreate">发布游记</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="filters" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索游记标题" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-row :gutter="16">
        <el-col v-for="post in posts" :key="post.id" :span="6" class="post-col">
          <PostCard :post="post" @edit="handleEdit" @delete="handleDelete" />
        </el-col>
      </el-row>
      <el-empty v-if="loaded && !posts.length" description="暂无游记" />
      <el-pagination
        class="pager"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="handlePageChange"
      />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPostList, deletePost } from '@/api/post'
import { auth } from '@/utils/auth'
import PostCard from '@/components/PostCard.vue'

const router = useRouter()

const filters = reactive({ keyword: '' })
const posts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const loading = ref(false)
const loaded = ref(false)

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
      page_size: pageSize.value
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
.post-col {
  margin-bottom: 16px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
