<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">个性化旅行规划平台</span>
    </div>
    <div class="header-right">
      <template v-if="!auth.token">
        <el-button type="primary" text @click="$router.push('/login')">登录</el-button>
        <el-button text @click="$router.push('/register')">注册</el-button>
      </template>
      <template v-else>
        <span>欢迎，{{ auth.username || '用户' }}（{{ roleText }}）</span>
        <el-button text type="danger" @click="handleLogout">退出登录</el-button>
      </template>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from '@/utils/auth'

const router = useRouter()

const roleText = computed(() => {
  if (auth.role === 'admin') return '管理员'
  if (auth.role === 'user') return '普通用户'
  return '游客'
})

const handleLogout = () => {
  clearAuth()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<style scoped>
.app-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
.logo {
  font-weight: 600;
  font-size: 18px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
