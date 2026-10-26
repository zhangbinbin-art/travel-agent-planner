<template>
  <aside class="app-sidebar">
    <el-menu :default-active="$route.path" router>
      <el-menu-item index="/">首页</el-menu-item>
      <el-menu-item index="/spot-list">景点列表</el-menu-item>
      <el-menu-item index="/post-list">游记列表</el-menu-item>
      <el-menu-item index="/plan">智能路线规划</el-menu-item>
      <el-menu-item v-if="auth.token" index="/user">个人中心</el-menu-item>
      <el-menu-item v-if="auth.token" index="/user/my-plan">我的路线</el-menu-item>
      <el-menu-item v-if="auth.role === 'admin'" index="/admin">管理员后台</el-menu-item>
      <el-menu-item v-if="!auth.token" index="/login">登录</el-menu-item>
      <el-menu-item v-if="!auth.token" index="/register">注册</el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup>
import { auth } from '@/utils/auth'
</script>

<style scoped>
.app-sidebar {
  width: 220px;
  background: #fff;
  border-right: 1px solid #ebeef5;
  min-height: calc(100vh - 60px);
}
</style>
