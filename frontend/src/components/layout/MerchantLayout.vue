<template>
  <div class="merchant-layout">
    <header class="merchant-header">
      <div class="brand">酒店商家后台</div>
      <div class="header-right">
        <span class="welcome">欢迎，{{ auth.username || '商家' }}</span>
        <el-button text type="danger" @click="handleLogout">退出登录</el-button>
      </div>
    </header>
    <div class="merchant-body">
      <aside class="merchant-sidebar">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/merchant/dashboard">仪表盘</el-menu-item>
          <el-menu-item index="/merchant/rooms">客房管理</el-menu-item>
          <el-menu-item index="/merchant/orders">预定订单</el-menu-item>
          <el-menu-item index="/merchant/guests">客人登记</el-menu-item>
          <el-menu-item index="/merchant/bills">账单收银</el-menu-item>
          <el-menu-item index="/merchant/report">财务报表</el-menu-item>
        </el-menu>
      </aside>
      <main class="merchant-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from '@/utils/auth'

const router = useRouter()

const handleLogout = () => {
  clearAuth()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.merchant-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
}
.merchant-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #1f2d3d;
  color: #fff;
}
.brand {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.welcome {
  color: #cfd8e3;
  font-size: 14px;
}
.merchant-body {
  display: flex;
  flex: 1;
}
.merchant-sidebar {
  width: 200px;
  background: #fff;
  border-right: 1px solid #ebeef5;
}
.merchant-main {
  flex: 1;
  padding: 20px;
  min-width: 0;
}
</style>
