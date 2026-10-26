<template>
  <div class="login">
    <el-card class="login-card">
      <template #header>登录</template>
      <el-form label-width="80px" :model="form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin">登录</el-button>
          <el-button text @click="$router.push('/register')">去注册</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { setAuth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const form = reactive({
  username: '',
  password: ''
})

// 只允许跳转本站内部路由，防止 ?redirect=https://evil.com 之类的开放重定向
const resolveRedirect = () => {
  const raw = route.query.redirect
  // 重复 query 参数会解析成数组，非字符串一律视为非法
  if (typeof raw !== 'string') return '/'
  const target = raw.trim()
  if (!target || !target.startsWith('/')) return '/'
  // 协议相对地址（//evil.com）与反斜杠（浏览器会当成 //）都不是站内路径
  if (target.startsWith('//') || target.includes('\\')) return '/'

  let url
  try {
    url = new URL(target, window.location.origin)
  } catch (e) {
    return '/'
  }
  // 同源白名单：只有本站路由才允许跳转
  if (url.origin !== window.location.origin) return '/'
  // 避免登录后再次跳回登录页造成循环
  if (url.pathname === '/login') return '/'
  return url.pathname + url.search + url.hash
}

const handleLogin = async () => {
  try {
    const res = await api.post('/api/v1/user/login', form)
    setAuth(res.data.access_token, form.username)
    ElMessage.success('登录成功')
    router.push(resolveRedirect())
  } catch (e) {
    if (e?.response?.status === 401) {
      ElMessage.error('账号或密码错误')
    } else {
      ElMessage.error(e?.response?.data?.detail || '登录失败，请稍后重试')
    }
  }
}
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f7f8fa;
}
.login-card {
  width: 420px;
}
</style>
