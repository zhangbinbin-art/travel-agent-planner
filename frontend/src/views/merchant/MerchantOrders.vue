<template>
  <div class="orders">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">预定订单</span>
          <el-radio-group v-model="statusFilter" size="small" @change="fetchOrders">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending_pay">待支付</el-radio-button>
            <el-radio-button value="paid">已支付</el-radio-button>
            <el-radio-button value="checked_in">入住中</el-radio-button>
            <el-radio-button value="checked_out">已退房</el-radio-button>
            <el-radio-button value="cancelled">已取消</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <el-table :data="orders" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="订单号" width="80" />
        <el-table-column prop="username" label="客人" width="110" />
        <el-table-column prop="hotel_name" label="酒店" min-width="150" />
        <el-table-column prop="room_type" label="房型" min-width="120" />
        <el-table-column label="入住/离店" min-width="190">
          <template #default="{ row }">{{ row.check_in }} ~ {{ row.check_out }}</template>
        </el-table-column>
        <el-table-column prop="days" label="天数" width="70" />
        <el-table-column label="金额" width="110">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.total_price) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.order_status)" size="small">{{ statusText(row.order_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button v-if="row.order_status === 'paid'" size="small" type="success" @click="setStatus(row, 'checked_in')">办理入住</el-button>
            <el-button v-if="row.order_status === 'checked_in'" size="small" @click="setStatus(row, 'checked_out')">退房</el-button>
            <el-button v-if="['pending_pay', 'paid'].includes(row.order_status)" size="small" type="danger" @click="setStatus(row, 'cancelled')">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMerchantOrders, updateMerchantOrderStatus } from '@/api/hotel'

const route = useRoute()
const orders = ref([])
const loading = ref(false)
// 支持从仪表盘带 ?status= 进来，自动激活对应筛选
const allowedStatus = ['pending_pay', 'paid', 'checked_in', 'checked_out', 'cancelled']
const normalizeStatus = (value) => (allowedStatus.includes(String(value)) ? String(value) : '')
const statusFilter = ref(normalizeStatus(route.query.status))

const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const statusText = (s) =>
  ({ pending_pay: '待支付', paid: '已支付', checked_in: '入住中', checked_out: '已退房', cancelled: '已取消' }[s] || s)
const statusType = (s) =>
  ({ pending_pay: 'warning', paid: 'success', checked_in: 'primary', checked_out: 'info', cancelled: 'danger' }[s] || 'info')

const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await getMerchantOrders({ order_status: statusFilter.value || undefined })
    orders.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取订单失败')
  } finally {
    loading.value = false
  }
}

const setStatus = async (row, status) => {
  try {
    const label = status === 'checked_in' ? '办理入住' : status === 'checked_out' ? '退房' : '取消订单'
    await ElMessageBox.confirm(`确定${label}吗？`, '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await updateMerchantOrderStatus(row.id, status)
    ElMessage.success('操作成功')
    await fetchOrders()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

watch(
  () => route.query.status,
  (val) => {
    statusFilter.value = normalizeStatus(val)
    fetchOrders()
  }
)

onMounted(fetchOrders)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.card-title { font-weight: 600; }
.price { color: #f56c6c; font-weight: 600; }
</style>
