<template>
  <div class="bills">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">账单收银</span>
          <div class="settle-row">
            <el-input-number v-model="settleOrderId" :min="1" placeholder="订单号" size="small" />
            <el-button type="primary" size="small" :loading="settling" @click="doSettle">收款核销</el-button>
          </div>
        </div>
      </template>
      <el-table :data="bills" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="账单号" width="90" />
        <el-table-column prop="order_id" label="订单号" width="90" />
        <el-table-column prop="hotel_name" label="酒店" min-width="160" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="支付方式" width="120">
          <template #default="{ row }">{{ payText(row.pay_channel) }}</template>
        </el-table-column>
        <el-table-column label="支付时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.pay_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBills, settleBill } from '@/api/hotel'

const bills = ref([])
const loading = ref(false)
const settling = ref(false)
const settleOrderId = ref(null)

const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')
const payText = (c) => ({ wechat: '微信支付', alipay: '支付宝', card: '银行卡', offline: '线下收款' }[c] || c || '-')

const fetchBills = async () => {
  loading.value = true
  try {
    const res = await getBills()
    bills.value = res.data || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取账单失败')
  } finally {
    loading.value = false
  }
}

const doSettle = async () => {
  if (!settleOrderId.value) {
    ElMessage.warning('请输入订单号')
    return
  }
  settling.value = true
  try {
    await settleBill(settleOrderId.value)
    ElMessage.success('收款核销成功')
    settleOrderId.value = null
    await fetchBills()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '核销失败')
  } finally {
    settling.value = false
  }
}

onMounted(fetchBills)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.card-title { font-weight: 600; }
.price { color: #f56c6c; font-weight: 600; }
.settle-row { display: flex; gap: 8px; align-items: center; }
</style>
