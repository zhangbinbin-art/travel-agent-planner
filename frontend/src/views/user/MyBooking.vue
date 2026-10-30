<template>
  <div class="my-booking">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">单独预订酒店</span>
          <span class="card-sub">提交后进入模拟支付，支付成功同步商户后台</span>
        </div>
      </template>
      <el-form label-width="90px">
        <el-form-item label="选择酒店">
          <HotelPicker v-model="selectedHotelId" :allow-custom="false" @change="onHotelChange" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :xs="24" :md="6">
            <el-form-item label="入住日期">
              <el-date-picker v-model="startDate" type="date" value-format="YYYY-MM-DD" placeholder="入住日期" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item label="离店日期">
              <el-date-picker v-model="endDate" type="date" value-format="YYYY-MM-DD" placeholder="离店日期" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="5">
            <el-form-item label="入住人数">
              <el-input-number v-model="guestCount" :min="1" :max="10" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="success" :disabled="!selectedHotelId" :loading="submitting" @click="submitBooking">
            提交预定并支付
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">我的酒店预约</span>
          <span class="count">共 {{ orders.length }} 条</span>
        </div>
      </template>

      <el-empty v-if="!loading && !orders.length" description="暂无酒店预约记录" />

      <div v-loading="loading" class="booking-cards">
        <el-card v-for="item in orders" :key="item.id" shadow="hover" class="booking-card">
          <div class="booking-top">
            <div class="hotel-name">{{ item.hotel_name || '酒店已删除' }}</div>
            <el-tag :type="statusType(item.order_status)" size="small">{{ statusText(item.order_status) }}</el-tag>
          </div>
          <div class="booking-line"><span class="label">订单号</span><span>{{ item.id }}</span></div>
          <div class="booking-line"><span class="label">房型</span><span>{{ item.room_type || '-' }}</span></div>
          <div class="booking-line"><span class="label">入住 / 离店</span><span>{{ item.check_in }} ~ {{ item.check_out }}</span></div>
          <div class="booking-line"><span class="label">入住天数</span><span>{{ item.days }} 天（{{ item.people_count || 1 }} 人）</span></div>
          <div class="booking-line"><span class="label">总价格</span><span class="price">¥{{ formatMoney(item.total_price) }}</span></div>
          <div class="booking-foot">
            <el-button
              v-if="item.order_status === 'pending_pay'"
              size="small"
              type="primary"
              @click="$router.push('/pay/' + item.id)"
            >
              去支付
            </el-button>
            <span v-else class="muted">{{ item.pay_channel ? '支付方式：' + payText(item.pay_channel) : '' }}</span>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyOrders, createHotelOrder } from '@/api/hotel'
import HotelPicker from '@/components/hotel/HotelPicker.vue'

const router = useRouter()
const orders = ref([])
const loading = ref(false)
const submitting = ref(false)
const selectedHotelId = ref('')
const selectedHotel = ref(null)
const startDate = ref('')
const endDate = ref('')
const guestCount = ref(1)

const statusText = (s) =>
  ({ pending_pay: '待支付', paid: '已支付', checked_in: '入住中', checked_out: '已退房', cancelled: '已取消' }[s] || s)
const statusType = (s) =>
  ({ pending_pay: 'warning', paid: 'success', checked_in: 'primary', checked_out: 'info', cancelled: 'danger' }[s] || 'info')
const payText = (c) => ({ wechat: '微信支付', alipay: '支付宝', card: '银行卡' }[c] || c)
const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))

const onHotelChange = (hotel) => {
  selectedHotel.value = hotel || null
}

const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await getMyOrders()
    orders.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取预约记录失败')
  } finally {
    loading.value = false
  }
}

const submitBooking = async () => {
  if (!selectedHotelId.value) {
    ElMessage.warning('请先选择酒店')
    return
  }
  if (!startDate.value || !endDate.value) {
    ElMessage.warning('请选择入住和离店日期')
    return
  }
  if (endDate.value <= startDate.value) {
    ElMessage.warning('离店日期必须晚于入住日期')
    return
  }
  submitting.value = true
  try {
    const res = await createHotelOrder({
      hotel_id: selectedHotelId.value,
      check_in: startDate.value,
      check_out: endDate.value,
      people_count: guestCount.value
    })
    router.push(`/pay/${res.data.id}`)
  } catch (e) {
    const detail = String(e?.response?.data?.detail || '')
    if (e?.response?.status === 403 && (detail.includes('实名') || detail.includes('REAL_NAME_REQUIRED'))) {
      try {
        await ElMessageBox.confirm('您还未完成实名认证，请前往个人中心完成实名后再预定酒店', '实名认证提示', {
          confirmButtonText: '去实名',
          cancelButtonText: '暂不',
          type: 'warning'
        })
        router.push({ path: '/user', query: { tab: 'realname' } })
      } catch (err) {
        // ignore
      }
    } else {
      ElMessage.error(detail || '提交预约失败')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.my-booking { display: flex; flex-direction: column; gap: 16px; }
.card-header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.card-title { font-weight: 600; }
.card-sub { color: #909399; font-size: 12px; }
.count { color: #909399; font-size: 13px; }
.booking-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.booking-card { border-radius: 8px; }
.booking-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.hotel-name { font-weight: 600; font-size: 16px; color: #303133; }
.booking-line { display: flex; justify-content: space-between; gap: 12px; color: #606266; font-size: 14px; margin-bottom: 8px; }
.label { color: #909399; }
.price { color: #f56c6c; font-weight: 600; }
.booking-foot { margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
.muted { color: #909399; font-size: 13px; }
</style>
