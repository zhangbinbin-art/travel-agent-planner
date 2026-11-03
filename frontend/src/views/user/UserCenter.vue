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

        <el-tab-pane label="我关注的" name="follow" lazy>
          <div class="embedded-pane">
            <MyFollow />
          </div>
        </el-tab-pane>

        <el-tab-pane label="粉丝" name="fans" lazy>
          <div class="embedded-pane">
            <MyFans />
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
import MyFollow from '@/views/user/MyFollow.vue'
import MyFans from '@/views/user/MyFans.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const TAB_NAMES = ['collect', 'trip', 'booking', 'post', 'comment', 'like', 'follow', 'fans']
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
/* ===== v0.17 与全站功能页统一：容器宽度/卡片间距/字体/控件尺寸 ===== */
.user-center {
  /* 与旅游攻略、旅游景点页一致（1320 居中） */
  max-width: 1320px;
  margin: 0 auto;
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.user-center :deep(.el-card) {
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(34, 34, 34, 0.08);
}
.user-center :deep(.el-card__header) {
  padding: 14px 20px;
}
.user-center :deep(.el-card__body) {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.card-title {
  font-size: 16px;
  font-weight: 800;
  color: #222;
}

/* 实名认证信息行 */
.realname-info {
  display: flex;
  flex-direction: column;
}
.info-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 9px 0;
  font-size: 14px;
  color: #3d4753;
  border-bottom: 1px dashed rgba(34, 34, 34, 0.08);
}
.info-row:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
}
.info-row .label {
  width: 84px;
  flex-shrink: 0;
  font-size: 13px;
  color: #7b8794;
}
.hint {
  margin-top: 8px;
  font-size: 12.5px;
  color: #7b8794;
}
.hint-inline {
  margin-left: 8px;
  font-size: 12.5px;
  color: #909399;
}

/* 表单与按钮尺寸统一（36px 高） */
.realname-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.realname-form :deep(.el-input__wrapper) {
  min-height: 36px;
}
.realname-form :deep(.el-button) {
  height: 36px;
  padding: 0 18px;
}

/* Tab 栏与攻略页筛选 tab 统一 */
.hub-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
.hub-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: rgba(34, 34, 34, 0.1);
}
.hub-tabs :deep(.el-tabs__item) {
  height: 40px;
  font-size: 14px;
  font-weight: 600;
  color: #5a6472;
}
.hub-tabs :deep(.el-tabs__item.is-active) {
  color: #f06818;
}
.hub-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 3px;
  background-color: #ff7a2f;
}

.embedded-pane {
  padding-top: 2px;
}

/* 帖子缩略图统一尺寸与裁切比例，避免忽大忽小 */
.embedded-pane :deep(.post-cover) {
  width: 132px;
  height: 88px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: #f2f8ff;
}
.embedded-pane :deep(.post-cover img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
