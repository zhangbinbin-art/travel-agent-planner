import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', name: 'Home', component: () => import('@/views/home/Home.vue') },
      { path: 'spot-list', name: 'SpotList', component: () => import('@/views/spot/SpotList.vue') },
      { path: 'spot-detail/:id', name: 'SpotDetail', component: () => import('@/views/spot/SpotDetail.vue') },
      { path: 'post-list', name: 'PostList', component: () => import('@/views/post/PostList.vue') },
      { path: 'post-detail/:id', name: 'PostDetail', component: () => import('@/views/post/PostDetail.vue') },
      { path: 'post-edit', name: 'PostCreate', component: () => import('@/views/post/PostEdit.vue') },
      { path: 'post-edit/:id', name: 'PostEdit', component: () => import('@/views/post/PostEdit.vue') },
      { path: 'user', name: 'UserCenter', component: () => import('@/views/user/UserCenter.vue') },
      { path: 'user/my-plan', name: 'MyPlan', component: () => import('@/views/user/MyPlan.vue') },
      { path: 'plan', name: 'Plan', component: () => import('@/views/plan/Plan.vue') },
      { path: 'admin', name: 'AdminIndex', component: () => import('@/views/admin/AdminIndex.vue') }
    ]
  },
  { path: '/login', name: 'Login', component: () => import('@/views/auth/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('@/views/auth/Register.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const needAuth =
    to.path === '/post-edit' ||
    to.path.startsWith('/post-edit/') ||
    to.path === '/user/my-plan' ||
    to.path.startsWith('/user/my-plan')
  if (needAuth && !localStorage.getItem('token')) {
    ElMessage.warning('请先登录')
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
