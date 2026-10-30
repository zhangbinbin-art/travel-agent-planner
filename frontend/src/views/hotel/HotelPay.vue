<template>
  <div class="pay-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="card-title">酒店预定支付</span>
          <el-tag v-if="order" :type="statusType(order.order_status)" size="small">
            {{ statusText(order.order_status) }}
          </el-tag>
        </div>
      </template>

      <el-empty v-if="!loading && !order" description="订单不存在" />

      <template v-else-if="order">
        <div v-if="!paid" class="pay-body">
          <div class="order-info">
            <div class="info-row"><span class="label">订单号</span><span>{{ order.id }}</span></div>
            <div class="info-row"><span class="label">酒店</span><span>{{ order.hotel_name }}</span></div>
            <div class="info-row"><span class="label">房型</span><span>{{ order.room_type || '-' }}</span></div>
            <div class="info-row"><span class="label">入住 / 离店</span><span>{{ order.check_in }} ~ {{ order.check_out }}</span></div>
            <div class="info-row"><span class="label">入住人数</span><span>{{ order.people_count }} 人</span></div>
            <div class="info-row"><span class="label">应付金额</span><span class="amount">¥{{ formatMoney(order.total_price) }}</span></div>
          </div>

          <el-divider content-position="left">选择支付方式</el-divider>
          <el-radio-group v-model="channel" class="channels">
            <el-radio-button value="wechat">微信支付</el-radio-button>
            <el-radio-button value="alipay">支付宝</el-radio-button>
            <el-radio-button value="card">银行卡支付</el-radio-button>
          </el-radio-group>

          <div v-if="order.order_status === 'pending_pay'" class="pay-actions">
            <el-button type="primary" :loading="paying" @click="confirmPay">确认支付</el-button>
            <el-button @click="cancelPay">取消支付</el-button>
          </div>
          <el-alert
            v-else
            type="warning"
            :closable="false"
            :title="'当前订单状态：' + statusText(order.order_status) + '，无法支付'"
          />
        </div>

        <div v-else class="pay-success">
          <el-result icon="success" title="支付成功" :sub-title="'订单号：' + order.id">
            <template #extra>
              <el-button type="primary" @click="$router.push('/user/my-booking')">查看我的预约</el-button>
              <el-button @click="$router.push('/plan')">返回行程规划</el-button>
            </template>
          </el-result>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHotelOrder, payHotelOrder, cancelHotelOrder } from '@/api/hotel'

const route = useRoute()
const router = useRouter()
const order = ref(null)
const loading = ref(false)
const paying = ref(false)
const channel = ref('wechat')
const paid = ref(false)

const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const statusText = (s) =>
  ({ pending_pay: '待支付', paid: '已支付', checked_in: '入住中', checked_out: '已退房', cancelled: '已取消' }[s] || s)
const statusType = (s) =>
  ({ pending_pay: 'warning', paid: 'success', checked_in: 'primary', checked_out: 'info', cancelled: 'danger' }[s] || 'info')

const fetchOrder = async () => {
  const id = Number(route.params.orderId)
  if (!Number.isFinite(id) || id <= 0) return
  loading.value = true
  try {
    const res = await getHotelOrder(id)
    order.value = res.data || null
    paid.value = order.value?.order_status === 'paid'
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取订单失败')
  } finally {
    loading.value = false
  }
}

const confirmPay = async () => {
  paying.value = true
  try {
    const res = await payHotelOrder(order.value.id, channel.value)
    order.value = res.data
    paid.value = true
    ElMessage.success('支付成功')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '支付失败')
  } finally {
    paying.value = false
  }
}

const cancelPay = async () => {
  try {
    await ElMessageBox.confirm('取消支付后订单将保留为待支付，30 分钟内未支付将自动取消，确定取消吗？', '提示', {
      type: 'warning'
    })
  } catch (e) {
    return
  }
  try {
    await cancelHotelOrder(order.value.id)
    ElMessage.info('已取消支付，订单已关闭')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '取消失败')
  }
  router.push('/plan')
}

onMounted(fetchOrder)
</script>

<style scoped>
.pay-page {
  max-width: 760px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.order-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}
.info-row {
  display: flex;
  gap: 12px;
  color: #606266;
}
.label {
  width: 100px;
  color: #909399;
}
.amount {
  color: #f56c6c;
  font-weight: 700;
  font-size: 18px;
}
.channels {
  margin-bottom: 16px;
}
.pay-actions {
  display: flex;
  gap: 12px;
}
.pay-success {
  padding: 20px 0;
}
</style>
