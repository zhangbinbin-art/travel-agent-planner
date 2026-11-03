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
    <div v-if="!verified && bannerText" class="verify-banner" :class="{ 'is-error': hasRejected }">
      {{ bannerText }}
    </div>
    <div class="merchant-body">
      <aside class="merchant-sidebar">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/merchant/dashboard">仪表盘</el-menu-item>
          <el-menu-item index="/merchant/hotel-info">酒店详情</el-menu-item>
          <el-menu-item index="/merchant/rooms" :disabled="!verified">客房管理</el-menu-item>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from '@/utils/auth'
import { getHotelStatus } from '@/api/hotel'

const router = useRouter()
const hotelStatus = ref({ verified: false, profile_status: null, cert_status: null, profile_msg: '', cert_msg: '' })

const verified = computed(() => !!hotelStatus.value.verified)
const hasRejected = computed(
  () => hotelStatus.value.profile_status === 'rejected' || hotelStatus.value.cert_status === 'rejected'
)
// 动态顶部提示：未提交 / 待审核 / 驳回 / 全部通过（通过后不显示）
const bannerText = computed(() => {
  const p = hotelStatus.value.profile_status
  const c = hotelStatus.value.cert_status
  if (!p && !c) return '请前往酒店详情页完善酒店资料并提交审核'
  if (p === 'rejected') return `审核已驳回：${hotelStatus.value.profile_msg || '酒店资料不符合要求'}，请修改后重新提交`
  if (c === 'rejected') return `审核已驳回：${hotelStatus.value.cert_msg || '酒店资质不符合要求'}，请修改后重新提交`
  if (p === 'pending' && (!c || c === 'draft')) return '酒店资料待审核，请补充酒店资质认证'
  if (c === 'pending' && (!p || p === 'draft')) return '酒店资质待审核，请补充酒店资料'
  return '酒店资料与资质认证审核通过后才会在客户端展示'
})

const loadStatus = async () => {
  if (!auth.token) return
  try {
    const res = await getHotelStatus()
    hotelStatus.value = res.data || hotelStatus.value
  } catch (e) {
    hotelStatus.value = { verified: false, profile_status: null, cert_status: null, profile_msg: '', cert_msg: '' }
  }
}

let statusTimer = null
onMounted(() => {
  loadStatus()
  // 管理员审核后无需手动刷新，30s 自动同步顶部提示
  statusTimer = window.setInterval(loadStatus, 30000)
})
onBeforeUnmount(() => {
  if (statusTimer) window.clearInterval(statusTimer)
})

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
.verify-banner {
  max-width: 1100px;
  margin: 12px 20px 0;
  padding: 10px 16px;
  border: 2px solid #f0c37a;
  border-radius: 10px;
  background: #fff8ea;
  color: #a1650c;
  font-size: 13px;
  font-weight: 600;
}
.verify-banner.is-error {
  border-color: #f3a7a7;
  background: #fff1f1;
  color: #c0392b;
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
