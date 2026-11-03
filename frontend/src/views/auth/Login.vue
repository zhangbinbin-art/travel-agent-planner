<template>
  <div class="login-page">
    <!-- 淡色山水露营插画背景（纯内联 SVG，无外部图片资源） -->
    <svg
      class="login-scene"
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <circle cx="1130" cy="180" r="86" fill="#ffe1b8" />
      <ellipse cx="1130" cy="180" r="118" fill="#ffeccc" opacity="0.55" />
      <g fill="#ffffff" opacity="0.85">
        <ellipse cx="250" cy="170" rx="78" ry="30" />
        <ellipse cx="310" cy="158" rx="58" ry="24" />
        <ellipse cx="860" cy="140" rx="66" ry="26" />
        <ellipse cx="912" cy="132" rx="48" ry="20" />
      </g>
      <path d="M0 660 L190 470 L330 610 L470 430 L640 660 Z" fill="#bfe0ff" opacity="0.75" />
      <path d="M420 660 L610 500 L760 640 L920 470 L1120 660 Z" fill="#a9d4ff" opacity="0.6" />
      <path d="M900 680 L1080 540 L1230 660 L1340 560 L1440 660 L1440 900 L900 900 Z" fill="#cbe6ff" opacity="0.7" />
      <path d="M0 700 C240 640 420 740 660 700 C900 660 1080 740 1440 690 L1440 900 L0 900 Z" fill="#d7ecff" />
      <path d="M0 780 C260 730 480 800 740 760 C980 724 1180 790 1440 752 L1440 900 L0 900 Z" fill="#c3e2ff" opacity="0.85" />
      <g opacity="0.9">
        <path d="M300 742 L350 660 L400 742 Z" fill="#ffd2a8" />
        <path d="M350 742 L350 660" stroke="#e9a86f" stroke-width="4" />
        <circle cx="350" cy="648" r="6" fill="#ffb073" />
      </g>
      <g fill="#9ecdf6" opacity="0.8">
        <path d="M180 760 l16 -42 l16 42 z" />
        <path d="M206 762 l12 -30 l12 30 z" />
        <path d="M1000 748 l18 -46 l18 46 z" />
        <path d="M1030 752 l13 -32 l13 32 z" />
      </g>
      <g fill="#8fc4f2" opacity="0.55">
        <circle cx="560" cy="700" r="5" />
        <circle cx="600" cy="686" r="4" />
        <circle cx="640" cy="702" r="5" />
        <circle cx="700" cy="690" r="4" />
      </g>
    </svg>

    <section class="login-card">
      <header class="login-brand">
        <span class="brand-logo">TR</span>
        <div class="brand-text">
          <h1 class="brand-name">旅游规划平台</h1>
          <span class="brand-en">Travel Route</span>
        </div>
      </header>

      <p class="login-welcome">欢迎回来 · Welcome Back</p>

      <el-form :model="form" class="login-form" @submit.prevent>
        <el-form-item class="form-item">
          <el-input v-model="form.username" placeholder="账号" clearable size="large">
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
        <el-form-item class="form-item form-item--submit">
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
        <span class="link-muted">还没有账号？</span>
        <span class="link-item" @click="$router.push('/register')">立即注册</span>
      </div>

      <div class="account-tip">
        <div>普通用户：favtest1 / abc123</div>
        <div>商家：shop01 / 123456</div>
        <div>管理员：admin / admin123</div>
      </div>
    </section>
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
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px 20px;
  background: linear-gradient(180deg, #eef7ff 0%, #e8f4ff 45%, #dceeff 100%);
  overflow: hidden;
}

.login-scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.55;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 34px 32px 26px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 24px;
  box-shadow: 6px 6px 0 rgba(34, 34, 34, 0.14);
}

.login-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #ff7a2f;
  border: 2px solid #222;
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 rgba(34, 34, 34, 0.16);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-name {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #222;
}

.brand-en {
  font-size: 12px;
  letter-spacing: 1.6px;
  color: #7b8794;
}

.login-welcome {
  margin: 22px 0;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #5a6472;
  letter-spacing: 0.6px;
}

.login-form :deep(.el-input__wrapper) {
  padding: 4px 12px;
}

.form-item {
  margin-bottom: 18px;
}

.form-item--submit {
  margin-top: 6px;
  margin-bottom: 16px;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  font-weight: 700;
  border-radius: 12px;
  letter-spacing: 4px;
}

.login-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #7b8794;
}

.link-muted {
  color: #7b8794;
}

.link-item {
  color: #ff7a2f;
  font-weight: 700;
  cursor: pointer;
}

.link-item:hover {
  text-decoration: underline;
}

.account-tip {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px dashed rgba(34, 34, 34, 0.16);
  text-align: center;
  font-size: 12px;
  line-height: 1.9;
  color: #93a0af;
}
</style>
