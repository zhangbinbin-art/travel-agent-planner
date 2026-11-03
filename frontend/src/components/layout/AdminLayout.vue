<template>
  <div class="admin-layout">
    <header class="admin-header">
      <div class="brand">
        <span class="brand-logo">TR</span>
        <span class="brand-text">旅游规划平台 · 管理员后台</span>
      </div>
      <div class="header-right">
        <span class="welcome">管理员：{{ auth.username || 'admin' }}</span>
        <el-button class="logout-btn" @click="handleLogout">退出登录</el-button>
      </div>
    </header>

    <div class="admin-body">
      <aside class="admin-sidebar">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/admin">平台总览</el-menu-item>
          <el-menu-item index="/admin/spot">景点管理</el-menu-item>
          <el-sub-menu index="content">
            <template #title>内容审核</template>
            <el-menu-item index="/admin/post-audit">游记审核</el-menu-item>
            <el-menu-item index="/admin/comment-audit">评论审核</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/admin/data">平台数据</el-menu-item>
          <el-sub-menu index="merchant">
            <template #title>商家审核</template>
            <el-menu-item index="/admin/merchant-audit?tab=profile">酒店资料审核</el-menu-item>
            <el-menu-item index="/admin/merchant-audit?tab=cert">酒店资质审核</el-menu-item>
            <el-menu-item index="/admin/merchant-audit?tab=account">商家账号审核</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </aside>

      <main class="admin-main">
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
.admin-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #e8f4ff;
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 20px 0;
  padding: 10px 18px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 18px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
  flex-wrap: wrap;
  gap: 8px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
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
  font-size: 16px;
  font-weight: 800;
  color: #222;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.welcome {
  font-size: 13px;
  color: #5a6472;
  font-weight: 600;
}
.logout-btn {
  height: 34px;
}
.admin-body {
  display: flex;
  flex: 1;
  min-width: 0;
}
.admin-sidebar {
  width: 208px;
  margin: 16px 0 16px 20px;
  padding: 8px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 16px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
  align-self: flex-start;
  flex-shrink: 0;
}
.admin-main {
  flex: 1;
  padding: 16px 20px 24px;
  min-width: 0;
}
</style>
