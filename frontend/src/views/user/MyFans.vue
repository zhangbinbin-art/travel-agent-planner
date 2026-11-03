<template>
  <div class="my-fans" v-loading="loading">
    <template v-if="list.length">
      <div class="list-head">
        <span class="list-count">共 {{ total }} 人</span>
      </div>

      <div class="user-list">
        <div
          v-for="item in list"
          :key="item.id"
          class="user-card"
          @click="goSpace(item.id)"
        >
          <div class="avatar" :style="{ background: avatarColor(item.username) }">
            {{ avatarText(item.username) }}
          </div>
          <div class="user-main">
            <div class="username">{{ item.username || '未知用户' }}</div>
            <div class="user-meta">关注于 {{ formatDate(item.create_time) }}</div>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>
      </div>

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
      description="还没有粉丝"
      hint="其他用户关注你后会显示在这里"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { getFansList } from '@/api/social'
import EmptyState from '@/components/EmptyState.vue'

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#5b8ff9']

const router = useRouter()

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)

const avatarText = (name) => {
  const text = String(name || '').trim()
  return text ? Array.from(text)[0].toUpperCase() : '?'
}

const avatarColor = (name) => {
  let sum = 0
  for (const ch of String(name || '')) sum += ch.codePointAt(0) || 0
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}

const formatDate = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getFansList({ page: page.value, page_size: pageSize.value })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    list.value = []
    total.value = 0
    ElMessage.error(e?.response?.data?.detail || '获取粉丝列表失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p) => {
  page.value = p
  fetchList()
}

// 统一跳转到新版用户主页 /user/:userId
const goSpace = (id) => router.push(`/user/${id}`)

onMounted(fetchList)
</script>

<style scoped>
.my-fans {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}
.list-head {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.list-count {
  font-size: 13px;
  color: #909399;
}
.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 14px;
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.user-card:hover {
  border-color: #dbe7fb;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
.avatar {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  user-select: none;
}
.user-main {
  flex: 1;
  min-width: 0;
}
.username {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
.arrow {
  flex-shrink: 0;
  color: #c0c4cc;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 4px;
}
</style>
