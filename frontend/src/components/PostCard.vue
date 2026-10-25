<template>
  <el-card shadow="hover" class="post-card" @click="goDetail">
    <div class="post-title" :title="post.title">{{ post.title }}</div>
    <div class="post-preview">{{ preview }}</div>
    <div class="post-meta">
      <span class="post-author">{{ authorName }}</span>
      <span class="post-heat">热度 {{ post.heat ?? 0 }}</span>
      <span class="post-time">{{ formattedTime }}</span>
    </div>
    <div v-if="canManage" class="post-actions">
      <el-button size="small" @click.stop="emit('edit', post)">编辑</el-button>
      <el-button size="small" type="danger" @click.stop="emit('delete', post)">删除</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/utils/auth'

const props = defineProps({
  post: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['edit', 'delete'])

const router = useRouter()

const goDetail = () => {
  router.push(`/post-detail/${props.post.id}`)
}

const preview = computed(() => {
  const content = typeof props.post.content === 'string' ? props.post.content : ''
  if (content.length > 80) return content.slice(0, 80) + '…'
  return content
})

const authorName = computed(() => props.post?.author?.username || '匿名')

const canManage = computed(
  () => auth.role === 'admin' || (auth.userId !== null && auth.userId === props.post.user_id)
)

const formattedTime = computed(() => formatTime(props.post.created_at))

function formatTime(value) {
  if (value === null || value === undefined || value === '') return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>

<style scoped>
.post-card {
  cursor: pointer;
  height: 100%;
}
.post-title {
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.post-preview {
  color: #606266;
  font-size: 13px;
  margin: 6px 0;
  min-height: 40px;
}
.post-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
.post-author {
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.post-heat {
  color: #f59e0b;
}
.post-time {
  white-space: nowrap;
}
.post-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  justify-content: flex-end;
}
</style>
