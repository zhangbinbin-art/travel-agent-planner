<template>
  <div class="comment-review">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">内容审核 · 评论审核</span>
          <div class="header-actions">
            <el-radio-group v-model="status" size="small" @change="handleSearch">
              <el-radio-button value="0">待审核</el-radio-button>
              <el-radio-button value="1">已通过</el-radio-button>
              <el-radio-button value="2">已驳回</el-radio-button>
              <el-radio-button value="">全部</el-radio-button>
            </el-radio-group>
            <el-input v-model="keyword" placeholder="按评论内容搜索" clearable class="kw-input" @keyup.enter="handleSearch" />
            <el-button size="small" @click="handleSearch">查询</el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredList" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="用户" width="120">
          <template #default="{ row }">{{ row.author?.username || row.user?.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="content" label="评论内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="success" :disabled="row.status === 1" @click="review(row, 1)">通过</el-button>
            <el-button size="small" type="warning" :disabled="row.status === 2" @click="review(row, 2)">驳回</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState v-if="!loading && !filteredList.length" description="暂无评论记录" />

      <el-pagination
        v-if="total > pageSize"
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import EmptyState from '@/components/EmptyState.vue'

const status = ref('0')
const keyword = ref('')
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)

const statusText = (s) => ({ 0: '待审核', 1: '已通过', 2: '已驳回' }[s] ?? '-')
const statusType = (s) => ({ 0: 'warning', 1: 'success', 2: 'danger' }[s] || 'info')
const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-')

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return list.value
  return list.value.filter((c) => String(c.content || '').toLowerCase().includes(kw))
})

const fetchList = async () => {
  loading.value = true
  try {
    const res = await api.get('/api/v1/admin/comment/list', {
      params: { status: status.value, page: page.value, page_size: pageSize.value }
    })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取评论列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  fetchList()
}

const handlePageChange = (val) => {
  page.value = val
  fetchList()
}

const review = async (row, nextStatus) => {
  try {
    await api.put(`/api/v1/admin/comment/${row.id}/review`, { status: nextStatus })
    ElMessage.success(nextStatus === 1 ? '已通过' : '已驳回')
    await fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？删除后不可恢复', '提示', { type: 'warning' })
    await api.delete(`/api/v1/admin/comment/${row.id}`)
    ElMessage.success('已删除')
    await fetchList()
  } catch (e) {
    /* 取消 */
  }
}

onMounted(fetchList)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.kw-input {
  width: 200px;
}
.card-title {
  font-weight: 800;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
