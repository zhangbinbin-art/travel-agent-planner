import { createRouter, createWebHistory } from 'vue-router'
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
      { path: 'user', name: 'UserCenter', component: () => import('@/views/user/UserCenter.vue') },
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

export default router
