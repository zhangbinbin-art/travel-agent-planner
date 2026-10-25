<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">个性化旅行规划平台</span>
    </div>
    <div class="header-right">
      <el-button v-if="user.role === 'guest'" type="primary" text @click="$router.push('/login')">登录</el-button>
      <el-button v-if="user.role === 'guest'" text @click="$router.push('/register')">注册</el-button>
      <span v-else>欢迎，{{ user.username || '用户' }}（{{ roleText }}）</span>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { mockUser } from '@/api/mock'

const user = mockUser
const roleText = computed(() => {
  if (user.role === 'admin') return '管理员'
  if (user.role === 'user') return '普通用户'
  return '游客'
})
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
