<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="login-title">智能旅行规划平台</div>
        <div class="login-subtitle">一体化旅行服务平台</div>
      </div>
      <div class="login-card">
        <div class="login-card-inner">
          <el-form :model="form" @submit.prevent>
            <el-form-item class="form-item">
              <el-input
                v-model="form.username"
                placeholder="账号"
                clearable
                size="large"
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item class="form-item">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                show-password
                size="large"
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="login-btn"
                size="large"
                :loading="loading"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>
          <div class="login-links">
            <span class="link-item" @click="$router.push('/register')">注册账号</span>
            <span class="link-divider">｜</span>
            <span class="link-item">忘记密码</span>
          </div>
          <div class="account-tip">
            <div>普通用户：favtest1 / abc123</div>
            <div>商家：shop01 / 123456</div>
            <div>管理员：admin / admin123</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '@/api'
import { setAuth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})

const resolveRedirect = () => {
  const raw = route.query.redirect
  if (typeof raw !== 'string') return null
  const target = raw.trim()
  if (!target || !target.startsWith('/')) return null
  if (target.startsWith('//') || target.includes('\\')) return null
  try {
    const url = new URL(target, window.location.origin)
    if (url.origin !== window.location.origin) return null
    if (url.pathname === '/login') return null
    return url.pathname + url.search + url.hash
  } catch (e) {
    return null
  }
}

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const res = await api.post('/api/v1/user/login', form)
    const { access_token, role, audit_status } = res.data || {}
    // 商家未审核：提示并留在登录页，不写入登录状态
    if (role === 'merchant' && audit_status !== 'approved') {
      ElMessage.warning(
        audit_status === 'rejected'
          ? '商家账号审核未通过，请联系管理员'
          : '商家账号待审核，请等待管理员审核通过后再登录'
      )
      return
    }
    setAuth(access_token, form.username, audit_status)
    ElMessage.success('登录成功')
    if (role === 'admin') {
      router.push('/admin')
      return
    }
    if (role === 'merchant') {
      router.push('/merchant/dashboard')
      return
    }
    const redirect = resolveRedirect()
    if (redirect) {
      router.push(redirect)
      return
    }
    router.push('/')
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.error('账号或密码错误')
    } else {
      ElMessage.error(e?.response?.data?.detail || '登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-image: url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=1920&q=80');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  position: relative;
  padding: 20px;
}

.login-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 28, 63, 0.45);
  z-index: 0;
}

.login-container {
  position: relative;
  z-index: 1;
}

.login-container {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  color: #ffffff;
}

.login-title {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 2px;
}

.login-subtitle {
  font-size: 14px;
  opacity: 0.9;
  letter-spacing: 1px;
}

.login-card {
  width: 100%;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.login-card-inner {
  padding: 40px 32px 32px;
}

.form-item {
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  background: linear-gradient(90deg, #1a73e8 0%, #1976d2 100%);
  border: none;
  border-radius: 8px;
}

.login-btn:hover {
  background: linear-gradient(90deg, #1765cc 0%, #1565c0 100%);
}

.login-links {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  font-size: 14px;
  color: #606266;
}

.link-item {
  color: #1a73e8;
  cursor: pointer;
}

.link-item:hover {
  text-decoration: underline;
}

.link-divider {
  margin: 0 12px;
  color: #dcdfe6;
}

.account-tip {
  text-align: center;
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
