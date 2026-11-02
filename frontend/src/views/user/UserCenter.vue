<template>
  <div class="user-center">
    <el-card class="realname-card" id="realname">
      <template #header>
        <div class="card-header">
          <span class="card-title">实名认证</span>
          <el-tag :type="profile.is_real_name_auth ? 'success' : 'warning'" size="small">
            {{ profile.is_real_name_auth ? '已实名' : '未实名' }}
          </el-tag>
        </div>
      </template>

      <div v-if="profile.is_real_name_auth" class="realname-info">
        <div class="info-row"><span class="label">姓名</span><span>{{ profile.real_name || '-' }}</span></div>
        <div class="info-row"><span class="label">身份证号</span><span>{{ maskedIdCard }}</span></div>
        <div class="hint">已完成实名认证，可正常预定酒店。</div>
      </div>

      <el-form v-else :model="form" label-width="90px" class="realname-form">
        <el-form-item label="姓名" required>
          <el-input v-model="form.real_name" placeholder="请输入真实姓名" maxlength="50" />
        </el-form-item>
        <el-form-item label="身份证号" required>
          <el-input v-model="form.id_card" placeholder="请输入18位身份证号" maxlength="30" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">提交实名认证</el-button>
          <span class="hint-inline">仅用于毕设模拟校验，不调用公安接口</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="hub-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">个人中心</span>
        </div>
      </template>

      <el-tabs v-model="active" class="hub-tabs">
        <el-tab-pane label="我的收藏" name="collect" lazy>
          <div class="embedded-pane">
            <MyFavorite />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的行程" name="trip" lazy>
          <div class="embedded-pane">
            <MyPlan />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的酒店预约" name="booking" lazy>
          <div class="embedded-pane">
            <MyBooking />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的帖子" name="post" lazy>
          <div class="embedded-pane">
            <MyPost />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的评论" name="comment" lazy>
          <!-- TODO(backend): GET /api/v1/user/comments 提供后，用真实评论列表替换此处空态。 -->
          <div class="embedded-pane">
            <EmptyState description="暂无评论" hint="你在游记下的评论会显示在这里" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我点赞的帖子" name="like" lazy>
          <div class="embedded-pane">
            <MyLikePost />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProfile, submitRealName } from '@/api/hotel'
import MyFavorite from '@/views/user/MyFavorite.vue'
import MyPlan from '@/views/user/MyPlan.vue'
import MyBooking from '@/views/user/MyBooking.vue'
import MyLikePost from '@/views/user/MyLikePost.vue'
import MyPost from '@/views/user/MyPost.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const TAB_NAMES = ['collect', 'trip', 'booking', 'post', 'comment', 'like']
const initialTab = TAB_NAMES.includes(route.query.tab) ? route.query.tab : 'collect'

const active = ref(initialTab)
const profile = ref({})
const submitting = ref(false)
const form = reactive({ real_name: '', id_card: '' })

// 仅当 tab 真正变化时同步到 URL，保留 ?tab=，且永不写入 realname
watch(active, (val) => {
  if (!TAB_NAMES.includes(val)) return
  if (route.query.tab === val) return
  router.replace({ query: { ...route.query, tab: val } })
})

const maskedIdCard = computed(() => {
  const id = profile.value.id_card || ''
  if (id.length < 8) return id || '-'
  return id.slice(0, 4) + '**********' + id.slice(-4)
})

const fetchProfile = async () => {
  try {
    const res = await getProfile()
    profile.value = res.data || {}
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取实名信息失败')
  }
}

const submit = async () => {
  if (!form.real_name || !form.id_card) {
    ElMessage.warning('请填写姓名和身份证号')
    return
  }
  submitting.value = true
  try {
    const res = await submitRealName({
      real_name: form.real_name.trim(),
      id_card: form.id_card.trim()
    })
    profile.value = res.data || {}
    ElMessage.success('实名认证成功')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '实名认证失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchProfile()
  if (route.query.tab === 'realname') {
    const el = document.getElementById('realname')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }
})
</script>

<style scoped>
.user-center {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.realname-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.info-row {
  display: flex;
  gap: 12px;
  color: #606266;
}
.label {
  width: 90px;
  color: #909399;
}
.hint {
  color: #67c23a;
  font-size: 13px;
}
.hint-inline {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

/* 个人中心 Hub 卡片 */
.hub-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}
.hub-card :deep(.el-card__body) {
  padding-top: 12px;
}

/* 标签栏：15px 标签，窄屏可横向滚动不换行 */
.hub-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}
.hub-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
}
.hub-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  white-space: nowrap;
}
.hub-tabs :deep(.el-tabs__item.is-active) {
  color: #2c3e50;
  font-weight: 700;
}
.hub-tabs :deep(.el-tabs__active-bar) {
  background-color: #409eff;
}

/* 内嵌组件外层卡片扁平化，避免卡片套卡片 */
.hub-tabs :deep(.my-plan > .el-card),
.hub-tabs :deep(.my-booking > .el-card),
.hub-tabs :deep(.my-favorite > .el-card) {
  border: none;
  box-shadow: none;
  background: transparent;
}
.hub-tabs :deep(.my-plan > .el-card > .el-card__body),
.hub-tabs :deep(.my-booking > .el-card > .el-card__body),
.hub-tabs :deep(.my-favorite > .el-card > .el-card__body) {
  padding: 0;
}
.hub-tabs :deep(.my-plan > .el-card > .el-card__header),
.hub-tabs :deep(.my-booking > .el-card > .el-card__header),
.hub-tabs :deep(.my-favorite > .el-card > .el-card__header) {
  padding: 0 0 14px;
  border-bottom: 1px solid #f0f0f0;
}
.embedded-pane {
  padding: 4px 0;
}
</style>
