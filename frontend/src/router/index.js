import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'
import { clearAuth } from '@/utils/auth'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', name: 'Home', component: () => import('@/views/home/Home.vue') },
      { path: 'spot-detail/:id', name: 'SpotDetail', meta: { keepAlive: false }, component: () => import('@/views/spot/SpotDetail.vue') },
      { path: 'spot', name: 'SpotList', component: () => import('@/views/spot/SpotList.vue') },
      { path: 'hotel-detail/:id', name: 'HotelDetail', meta: { keepAlive: false }, component: () => import('@/views/hotel/HotelDetail.vue') },
      { path: 'pay/:orderId', name: 'HotelPay', meta: { keepAlive: false }, component: () => import('@/views/hotel/HotelPay.vue') },
      { path: 'post-list', name: 'PostList', component: () => import('@/views/post/PostList.vue') },
      { path: 'strategy', name: 'Strategy', redirect: '/post-list' },
      { path: 'post-detail/:id', name: 'PostDetail', component: () => import('@/views/post/PostDetail.vue') },
      { path: 'post-edit', name: 'PostCreate', component: () => import('@/views/post/PostEdit.vue') },
      { path: 'post-edit/:id', name: 'PostEdit', component: () => import('@/views/post/PostEdit.vue') },
      { path: 'user', name: 'UserCenter', component: () => import('@/views/user/UserCenter.vue') },
      { path: 'user/my-plan', name: 'MyPlan', component: () => import('@/views/user/MyPlan.vue') },
      { path: 'user/my-favorite', name: 'MyFavorite', component: () => import('@/views/user/MyFavorite.vue') },
      { path: 'user/my-booking', name: 'MyBooking', component: () => import('@/views/user/MyBooking.vue') },
      { path: 'user/my-like-post', name: 'MyLikePost', component: () => import('@/views/user/MyLikePost.vue') },
      { path: 'user/my-follow', name: 'MyFollow', component: () => import('@/views/user/MyFollow.vue') },
      { path: 'user/my-fans', name: 'MyFans', component: () => import('@/views/user/MyFans.vue') },
      { path: 'user/:userId', name: 'UserProfile', component: () => import('@/views/user/UserProfile.vue') },
      { path: 'plan', name: 'Plan', meta: { keepAlive: true }, component: () => import('@/views/plan/Plan.vue') },

    ]
  },
  {
    // 管理员独立后台（不使用客户端顶部导航）
    path: '/admin',
    component: () => import('@/components/layout/AdminLayout.vue'),
    children: [
      { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/AdminDashboard.vue') },
      { path: 'spot', name: 'AdminSpotManage', component: () => import('@/views/admin/SpotManage.vue') },
      { path: 'post-audit', name: 'AdminPostAudit', component: () => import('@/views/admin/PostReview.vue') },
      { path: 'comment-audit', name: 'AdminCommentAudit', component: () => import('@/views/admin/CommentReview.vue') },
      { path: 'merchant-audit', name: 'AdminMerchantAudit', component: () => import('@/views/admin/MerchantAudit.vue') },
      { path: 'data', name: 'AdminPlatformData', component: () => import('@/views/admin/PlatformData.vue') }
    ]
  },
  {
    path: '/merchant',
    component: () => import('@/components/layout/MerchantLayout.vue'),
    children: [
      { path: '', redirect: '/merchant/dashboard' },
      { path: 'hotel-info', name: 'MerchantHotelInfo', component: () => import('@/views/merchant/HotelInfo.vue') },
      { path: 'dashboard', name: 'MerchantDashboard', component: () => import('@/views/merchant/MerchantDashboard.vue') },
      { path: 'rooms', name: 'MerchantRooms', component: () => import('@/views/merchant/MerchantRooms.vue') },
      { path: 'orders', name: 'MerchantOrders', component: () => import('@/views/merchant/MerchantOrders.vue') },
      { path: 'guests', name: 'MerchantGuests', component: () => import('@/views/merchant/MerchantGuests.vue') },
      { path: 'bills', name: 'MerchantBills', component: () => import('@/views/merchant/MerchantBills.vue') },
      { path: 'report', name: 'MerchantReport', component: () => import('@/views/merchant/MerchantReport.vue') }
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
  const token = localStorage.getItem('token')
  const publicPaths = ['/login', '/register']

  if (!token) {
    if (publicPaths.includes(to.path)) {
      return true
    }
    ElMessage.warning('请先登录')
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (token && publicPaths.includes(to.path)) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const role = payload.role
      if (role === 'admin') return '/admin'
      if (role === 'merchant') {
        const auditStatus = localStorage.getItem('audit_status')
        if (auditStatus !== 'approved') {
          ElMessage.warning('商家账号待审核，请等待管理员审核通过后再登录')
          clearAuth()
          return true
        }
        return '/merchant/dashboard'
      }
      return '/'
    } catch (e) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      ElMessage.warning('请先登录')
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const role = payload.role
      if (to.path.startsWith('/admin') && role !== 'admin') {
        return '/'
      }
      if (to.path.startsWith('/merchant')) {
        if (role !== 'merchant') return '/'
        const auditStatus = localStorage.getItem('audit_status')
        if (auditStatus !== 'approved') {
          ElMessage.warning('商家账号待审核，暂无法进入商家后台')
          clearAuth()
          return '/login'
        }
      }
    } catch (e) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      ElMessage.warning('请先登录')
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router
