<template>
  <div class="merchant-layout">
    <header class="merchant-header">
      <div class="brand">
        <span class="brand-logo">TR</span>
        <span class="brand-text">商家中心</span>
      </div>
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
  background: #e8f4ff;
}
.merchant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 20px 0;
  padding: 10px 18px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 18px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
  color: #222;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #222;
}
.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #ff7a2f;
  border: 2px solid #222;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}
.brand-text {
  color: #222;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.welcome {
  color: #5a6472;
  font-size: 14px;
}
.merchant-body {
  display: flex;
  flex: 1;
}
.merchant-sidebar {
  width: 208px;
  margin: 16px 0 16px 20px;
  padding: 8px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 16px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
  align-self: flex-start;
}
.merchant-main {
  flex: 1;
  padding: 16px 20px 24px;
  min-width: 0;
}
</style>
