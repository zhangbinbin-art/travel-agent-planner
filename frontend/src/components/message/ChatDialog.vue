<template>
  <el-dialog
    v-model="visible"
    :title="`与 ${targetName || '对方'} 的对话`"
    width="min(560px, 92vw)"
    append-to-body
    class="chat-dialog"
    @closed="handleClosed"
  >
    <template #header>
      <div class="chat-header">
        <div class="avatar" :style="{ background: avatarColor(targetName) }">
          {{ avatarText(targetName) }}
        </div>
        <span class="chat-title">与 {{ targetName || '对方' }} 的对话</span>
      </div>
    </template>

    <div ref="scrollRef" class="chat-body" v-loading="loading">
      <div v-if="!loading && !messages.length" class="chat-empty">
        暂无消息，发条消息打个招呼吧
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        class="msg-row"
        :class="{ mine: isMine(msg) }"
      >
        <div class="msg-bubble">{{ msg.content }}</div>
        <div class="msg-time">{{ formatTime(msg.create_time) }}</div>
      </div>
    </div>

    <div class="chat-input">
      <el-alert
        v-if="!canSend"
        type="warning"
        :closable="false"
        show-icon
        title="对方暂未回复，请等待对方回话后再发送"
        class="chat-alert"
      />

      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        maxlength="200"
        show-word-limit
        resize="none"
        :disabled="!canSend"
        placeholder="输入消息…"
        @keydown.enter.exact.prevent="handleSend"
      />

      <div class="input-foot">
        <span class="input-tip">Enter 发送，Shift + Enter 换行</span>
        <el-button
          type="primary"
          :disabled="!canSend || !draft.trim()"
          :loading="sending"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getChat, sendMessage } from '@/api/social'
import { auth } from '@/utils/auth'

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#5b8ff9']

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  targetUserId: { type: Number, default: null },
  targetName: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const scrollRef = ref(null)
const messages = ref([])
const draft = ref('')
const canSend = ref(true)
const loading = ref(false)
const sending = ref(false)

const avatarText = (name) => {
  const text = String(name || '').trim()
  return text ? Array.from(text)[0].toUpperCase() : '?'
}

const avatarColor = (name) => {
  let sum = 0
  for (const ch of String(name || '')) sum += ch.codePointAt(0) || 0
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}

const isMine = (msg) => Number(msg.sender_id) === auth.userId

const formatTime = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const scrollToBottom = async () => {
  await nextTick()
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const loadChat = async () => {
  if (!Number.isFinite(props.targetUserId)) return
  loading.value = true
  try {
    const res = await getChat(props.targetUserId)
    const data = res.data || {}
    messages.value = data.items || []
    canSend.value = data.can_send !== false
    await scrollToBottom()
  } catch (e) {
    messages.value = []
    ElMessage.error(e?.response?.data?.detail || '获取聊天记录失败')
  } finally {
    loading.value = false
  }
}

const handleSend = async (event) => {
  if (event?.isComposing) return
  if (!canSend.value || sending.value) return
  const content = draft.value.trim()
  if (!content) return

  sending.value = true
  try {
    const res = await sendMessage({ receiver_id: props.targetUserId, content })
    messages.value.push(res.data)
    draft.value = ''
    // 我方刚发出一句，需等对方回复后才能继续发送
    canSend.value = false
    await scrollToBottom()
  } catch (e) {
    const detail = e?.response?.data?.detail
    const rateLimited =
      e?.response?.status === 400 &&
      typeof detail === 'string' &&
      detail.includes('等对方回复')
    if (rateLimited) {
      canSend.value = false
    } else {
      ElMessage.error(detail || '发送失败')
    }
  } finally {
    sending.value = false
  }
}

const handleClosed = () => {
  draft.value = ''
}

watch(
  () => props.modelValue,
  (val) => {
    if (!val) return
    messages.value = []
    draft.value = ''
    canSend.value = true
    loadChat()
  }
)

watch(
  () => props.targetUserId,
  () => {
    if (props.modelValue) loadChat()
  }
)
</script>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  user-select: none;
}
.chat-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-body {
  max-height: 360px;
  overflow-y: auto;
  padding: 4px 2px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 96px;
}
.chat-empty {
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
  color: #909399;
}
.msg-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.msg-row.mine {
  align-items: flex-end;
}
.msg-bubble {
  max-width: 76%;
  padding: 8px 12px;
  border-radius: 12px;
  background: #f4f4f5;
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-row.mine .msg-bubble {
  background: #409eff;
  color: #fff;
}
.msg-time {
  font-size: 11px;
  color: #909399;
}
.chat-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}
.chat-alert {
  margin-bottom: 2px;
}
.input-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.input-tip {
  font-size: 12px;
  color: #909399;
}
.chat-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}
</style>
