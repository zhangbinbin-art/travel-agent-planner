<template>
  <div class="my-comment" v-loading="loading">
    <template v-if="items.length">
      <article v-for="item in items" :key="item.id" class="comment-card">
        <div class="comment-head">
          <span class="comment-post" @click="goPost(item.post_id)">
            {{ item.post_title || '游记已删除' }}
          </span>
          <el-tag size="small" :type="statusType(item.status)">{{ item.status_text }}</el-tag>
        </div>
        <p class="comment-content">{{ item.content }}</p>
        <div class="comment-meta">{{ formatTime(item.created_at) }}</div>
      </article>

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
      description="暂无评论"
      hint="你在游记下发表的评论会显示在这里"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)

const statusType = (s) => ({ 0: 'warning', 1: 'success', 2: 'danger' }[s] || 'info')
const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')

const goPost = (id) => {
  if (id) router.push(`/post-detail/${id}`)
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await api.get('/api/v1/user/my-comments', {
      params: { page: page.value, page_size: pageSize.value }
    })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取评论失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (val) => {
  page.value = val
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.my-comment {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.comment-card {
  padding: 12px 14px;
  background: #fff;
  border: 2px solid rgba(34, 34, 34, 0.14);
  border-radius: 10px;
}
.comment-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.comment-post {
  font-size: 13.5px;
  font-weight: 700;
  color: #222;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.comment-post:hover {
  color: #f06818;
}
.comment-content {
  margin: 8px 0 6px;
  font-size: 14px;
  color: #3d4753;
  line-height: 1.6;
}
.comment-meta {
  font-size: 12px;
  color: #909399;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}
</style>
