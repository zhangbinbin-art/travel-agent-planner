<template>
  <div>
    <el-dialog
      v-model="visible"
      title="聊天消息"
      width="460px"
      class="conv-dialog"
      @open="load"
    >
      <div v-loading="loading" class="conv-body">
        <div v-if="items.length" class="conv-list">
          <div
            v-for="item in items"
            :key="item.user.id"
            class="conv-item"
            :class="{ 'is-blocked': item.blocked }"
            @click="openChat(item)"
          >
            <div class="conv-avatar" :style="{ background: avatarColor(item.user.username) }">
              {{ avatarText(item.user.username) }}
              <i v-if="item.unread" class="conv-dot"></i>
            </div>
            <div class="conv-main">
              <div class="conv-top">
                <span class="conv-name">{{ item.user.username }}</span>
                <span class="conv-time">{{ formatTime(item.last_message?.create_time) }}</span>
              </div>
              <div class="conv-msg">
                <template v-if="item.blocked">已被拉黑，无法发起私聊</template>
                <template v-else>
                  <span v-if="item.last_message?.from_me" class="conv-self">我：</span>
                  {{ item.last_message?.content }}
                </template>
              </div>
            </div>
            <el-tag v-if="item.blocked" size="small" type="info">已拉黑</el-tag>
          </div>
        </div>
        <EmptyState
          v-else-if="!loading"
          description="暂无聊天记录"
          hint="在攻略详情或用户主页点击「私聊」即可开始"
        />
      </div>
    </el-dialog>

    <ChatDialog
      v-model="chatVisible"
      :target-user-id="chatTargetId"
      :target-name="chatTargetName"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getConversations } from '@/api/social'
import ChatDialog from './ChatDialog.vue'
import EmptyState from '@/components/EmptyState.vue'

const AVATAR_COLORS = ['#ff7a2f', '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#5b8ff9']

const visible = defineModel({ type: Boolean, default: false })

const loading = ref(false)
const items = ref([])

const chatVisible = ref(false)
const chatTargetId = ref('')
const chatTargetName = ref('')

const avatarText = (name) => {
  const text = String(name || '').trim()
  return text ? Array.from(text)[0].toUpperCase() : '?'
}

const avatarColor = (name) => {
  let sum = 0
  for (const ch of String(name || '')) sum += ch.codePointAt(0) || 0
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}

const formatTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const sameDay = date.toDateString() === now.toDateString()
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  if (sameDay) return `${hh}:${mm}`
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${m}-${d} ${hh}:${mm}`
}

const load = async () => {
  loading.value = true
  try {
    const res = await getConversations()
    items.value = res.data?.items || []
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

const openChat = (item) => {
  if (item.blocked) {
    ElMessage.warning('无法发起私聊')
    return
  }
  chatTargetId.value = item.user.id
  chatTargetName.value = item.user.username
  chatVisible.value = true
}

// 关闭对话后刷新会话列表，让最新一条消息同步
watch(chatVisible, (val) => {
  if (!val) load()
})
</script>

<style scoped>
.conv-body {
  min-height: 120px;
}

.conv-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border: 2px solid rgba(34, 34, 34, 0.14);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.conv-item:hover {
  border-color: #222;
  background: #fff7ef;
}

.conv-item.is-blocked {
  cursor: not-allowed;
  opacity: 0.65;
}

.conv-avatar {
  position: relative;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid #222;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
}

.conv-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #f56c6c;
  border: 2px solid #fff;
}

.conv-main {
  flex: 1;
  min-width: 0;
}

.conv-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.conv-name {
  font-size: 14px;
  font-weight: 700;
  color: #222;
}

.conv-time {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}

.conv-msg {
  margin-top: 2px;
  font-size: 12.5px;
  color: #7b8794;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-self {
  color: #f06818;
}
</style>
