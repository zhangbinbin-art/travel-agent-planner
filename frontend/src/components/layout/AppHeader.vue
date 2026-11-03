<template>
  <header class="tr-header">
    <div class="tr-header-bar">
      <!-- 左：logo + 平台名 -->
      <div class="tr-brand" @click="go('/')">
        <span class="tr-logo">TR</span>
        <span class="tr-brand-text">旅游规划平台</span>
      </div>

      <!-- 中：导航 -->
      <nav class="tr-nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          class="tr-nav-item"
          :class="{ 'is-active': isActive(item) }"
          @click="handleNav(item)"
        >
          {{ item.label }}
        </button>
      </nav>

      <!-- 右：搜索 + 管理员入口 + 登录态 -->
      <div class="tr-header-right">
        <div class="tr-search">
          <el-input
            v-model="searchKeyword"
            class="tr-search-input"
            placeholder="搜索游记"
            clearable
            @keyup.enter="handleSearch"
            @clear="searchKeyword = ''"
          />
          <el-button type="primary" class="tr-search-btn" @click="handleSearch">搜索</el-button>
        </div>

        <el-dropdown v-if="auth.role === 'admin'" trigger="click" @command="go">
          <el-button class="tr-admin-btn">
            管理员后台
            <el-icon class="tr-caret"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/admin/post-review">内容审核</el-dropdown-item>
              <el-dropdown-item command="/admin/merchant">商家审核</el-dropdown-item>
              <el-dropdown-item command="/admin/spot">景点管理</el-dropdown-item>
              <el-dropdown-item command="/admin/data">平台总览</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <template v-if="auth.token">
          <span class="tr-user">
            <el-icon class="tr-user-icon"><UserFilled /></el-icon>
            {{ auth.username || '用户' }}
          </span>
          <el-button class="tr-logout-btn" @click="handleLogout">退出登录</el-button>
        </template>
        <template v-else>
          <el-button type="primary" @click="go('/login')">登录</el-button>
          <el-button @click="go('/register')">注册</el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, UserFilled } from '@element-plus/icons-vue'
import { auth, clearAuth } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const searchKeyword = ref('')

const navItems = [
  { key: 'home', label: '首页', path: '/' },
  { key: 'spot', label: '旅游景点', path: '/spot' },
  { key: 'plan', label: 'AI路线规划助手', path: '/plan' },
  { key: 'post', label: '旅游攻略', path: '/strategy' },
  { key: 'user', label: '个人中心', path: '/user' }
]

const isActive = (item) => {
  if (item.key === 'home') return route.path === '/' && !route.hash
  if (item.key === 'spot') return route.path === '/spot'
  if (item.key === 'post') return route.path.startsWith('/post') || route.path === '/strategy'
  if (item.key === 'user') return route.path.startsWith('/user')
  return route.path === item.path
}

const go = (path) => router.push(path)

const handleNav = (item) => {
  if (item.hash) {
    router.push({ path: item.path, hash: item.hash })
    return
  }
  router.push(item.path)
}

const handleSearch = () => {
  const keyword = searchKeyword.value.trim()
  router.push({ path: '/post-list', query: keyword ? { keyword } : {} })
}

const handleLogout = () => {
  clearAuth()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<style scoped>
.tr-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 12px 20px 0;
  background: transparent;
}

.tr-header-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 10px 18px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 18px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
}

.tr-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 0;
}

.tr-logo {
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
  letter-spacing: 0.4px;
}

.tr-brand-text {
  font-size: 16px;
  font-weight: 800;
  color: #222;
  white-space: nowrap;
}

.tr-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
  min-width: 0;
  overflow: hidden;
}

.tr-nav-item {
  padding: 8px 12px;
  border: 2px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #3d4753;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.tr-nav-item:hover {
  background: #eef6ff;
  color: #222;
}

.tr-nav-item.is-active {
  background: #fff1e6;
  border-color: #222;
  color: #222;
}

.tr-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.tr-search {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tr-search-input {
  width: 168px;
}

.tr-search-btn {
  height: 34px;
}

.tr-admin-btn {
  height: 34px;
}

.tr-caret {
  margin-left: 4px;
  font-size: 12px;
}

.tr-user {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #3d4753;
  white-space: nowrap;
}

.tr-user-icon {
  font-size: 15px;
  color: #ff7a2f;
}

.tr-logout-btn {
  height: 34px;
}

@media (max-width: 1100px) {
  .tr-nav {
    justify-content: flex-start;
  }
  .tr-search-input {
    width: 130px;
  }
}

@media (max-width: 900px) {
  .tr-header-bar {
    flex-wrap: wrap;
  }
  .tr-nav {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
