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

    <el-card>
      <template #header>个人中心</template>
      <el-tabs v-model="active">
        <el-tab-pane label="我的收藏" name="collect">
          <el-empty description="请前往“我的收藏”菜单查看" />
        </el-tab-pane>
        <el-tab-pane label="我的行程" name="trip">
          <el-empty description="请前往“我的路线”菜单查看" />
        </el-tab-pane>
        <el-tab-pane label="我的帖子" name="post">
          <el-empty description="暂无帖子" />
        </el-tab-pane>
        <el-tab-pane label="我的评论" name="comment">
          <el-empty description="暂无评论" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProfile, submitRealName } from '@/api/hotel'

const route = useRoute()
const router = useRouter()
const active = ref('collect')
const profile = ref({})
const submitting = ref(false)
const form = reactive({ real_name: '', id_card: '' })

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
  gap: 16px;
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
</style>
