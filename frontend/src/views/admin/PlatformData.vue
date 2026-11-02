<template>
  <div class="platform-data">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">平台总览</span>
          <div class="header-actions">
            <el-radio-group v-model="tab" size="small">
              <el-radio-button value="hotel">全部酒店</el-radio-button>
              <el-radio-button value="order">全部预订单</el-radio-button>
            </el-radio-group>
            <el-button v-if="tab === 'hotel'" type="primary" size="small" @click="openCreate">新增酒店</el-button>
          </div>
        </div>
      </template>

      <el-table v-if="tab === 'hotel'" :data="hotels" v-loading="hotelLoading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="酒店名称" min-width="190" />
        <el-table-column prop="address" label="地址" min-width="210" />
        <el-table-column label="坐标" min-width="180">
          <template #default="{ row }">
            <span v-if="row.lng != null && row.lat != null">{{ Number(row.lng).toFixed(6) }}, {{ Number(row.lat).toFixed(6) }}</span>
            <el-tag v-else size="small" type="info">未设置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.price_per_day) }}</span></template>
        </el-table-column>
        <el-table-column label="评分" width="140">
          <template #default="{ row }">环境 {{ row.env_score || '-' }} / 服务 {{ row.service_score || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="95">
          <template #default="{ row }">
            <el-tag :type="row.status === 'on_shelf' ? 'success' : 'info'" size="small">
              {{ row.status === 'on_shelf' ? '已上架' : '已下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" :type="row.status === 'on_shelf' ? 'warning' : 'success'" @click="toggleStatus(row)">
              {{ row.status === 'on_shelf' ? '下架' : '上架' }}
            </el-button>
            <el-button size="small" type="danger" @click="removeHotel(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-table v-else :data="orders" v-loading="orderLoading" style="width: 100%">
        <el-table-column prop="id" label="订单号" width="80" />
        <el-table-column prop="username" label="客人" width="110" />
        <el-table-column prop="hotel_name" label="酒店" min-width="170" />
        <el-table-column prop="room_type" label="房型" min-width="110" />
        <el-table-column label="入住/离店" min-width="190">
          <template #default="{ row }">{{ row.check_in }} ~ {{ row.check_out }}</template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.total_price) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="orderType(row.order_status)">{{ orderText(row.order_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付" width="100">
          <template #default="{ row }">{{ payText(row.pay_channel) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑酒店' : '新增酒店'" width="560px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="酒店名称" prop="name">
          <el-input v-model="form.name" maxlength="150" />
        </el-form-item>
        <el-form-item label="详细地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="经纬度">
          <div class="coord-row">
            <el-input v-model="form.lng" placeholder="经度，如 120.153576" />
            <el-input v-model="form.lat" placeholder="纬度，如 30.287459" />
            <el-button :loading="geoLoading" @click="fetchCoords">按名称获取</el-button>
          </div>
        </el-form-item>
        <el-form-item label="单日单价">
          <el-input-number v-model="form.price_per_day" :min="0" :step="50" />
        </el-form-item>
        <el-form-item label="封面图">
          <el-input v-model="form.cover_img" placeholder="图片链接" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="设施">
          <el-input v-model="form.facilities" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="评分">
          <div class="score-row">
            <span>环境</span>
            <el-input-number v-model="form.env_score" :min="0" :max="5" :step="0.1" :precision="1" />
            <span>服务</span>
            <el-input-number v-model="form.service_score" :min="0" :max="5" :step="0.1" :precision="1" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminHotels,
  adminCreateHotel,
  adminUpdateHotel,
  adminHotelStatus,
  adminDeleteHotel,
  getAdminOrders
} from '@/api/hotel'
import { geoCode } from '@/api/map'

const tab = ref('hotel')
const hotels = ref([])
const orders = ref([])
const hotelLoading = ref(false)
const orderLoading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const geoLoading = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({
  name: '', address: '', lng: '', lat: '', price_per_day: 300, cover_img: '', description: '',
  facilities: '', env_score: 0, service_score: 0
})
const rules = { name: [{ required: true, message: '请输入酒店名称', trigger: 'blur' }] }

const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const orderText = (s) =>
  ({ pending_pay: '待支付', paid: '已支付', checked_in: '入住中', checked_out: '已退房', cancelled: '已取消' }[s] || s)
const orderType = (s) =>
  ({ pending_pay: 'warning', paid: 'success', checked_in: 'primary', checked_out: 'info', cancelled: 'danger' }[s] || 'info')
const payText = (c) => ({ wechat: '微信', alipay: '支付宝', card: '银行卡', offline: '线下' }[c] || '-')
const err = (e, f) => e?.response?.data?.detail || f

const fetchHotels = async () => {
  hotelLoading.value = true
  try {
    const res = await getAdminHotels()
    hotels.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(err(e, '获取酒店失败'))
  } finally {
    hotelLoading.value = false
  }
}

const fetchOrders = async () => {
  orderLoading.value = true
  try {
    const res = await getAdminOrders()
    orders.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(err(e, '获取订单失败'))
  } finally {
    orderLoading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    name: '', address: '', lng: '', lat: '', price_per_day: 300, cover_img: '', description: '',
    facilities: '', env_score: 0, service_score: 0
  })
  editingId.value = null
  formRef.value?.clearValidate()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    address: row.address || '',
    lng: row.lng == null ? '' : String(row.lng),
    lat: row.lat == null ? '' : String(row.lat),
    price_per_day: Number(row.price_per_day) || 0,
    cover_img: row.cover_img || '',
    description: row.description || '',
    facilities: row.facilities || '',
    env_score: Number(row.env_score) || 0,
    service_score: Number(row.service_score) || 0
  })
  dialogVisible.value = true
}

// 按酒店名称一键获取经纬度（后端转发高德地理编码）
const fetchCoords = async () => {
  const name = (form.name || '').trim()
  if (!name) {
    ElMessage.warning('请先填写酒店名称')
    return
  }
  geoLoading.value = true
  try {
    const res = await geoCode(name)
    const data = res.data || {}
    form.lng = String(data.lng)
    form.lat = String(data.lat)
    ElMessage.success('已获取坐标：' + data.lng + ', ' + data.lat)
  } catch (e) {
    ElMessage.error(err(e, '获取坐标失败'))
  } finally {
    geoLoading.value = false
  }
}

const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = {
      ...form,
      name: form.name.trim(),
      lng: form.lng === '' || form.lng === null ? null : Number(form.lng),
      lat: form.lat === '' || form.lat === null ? null : Number(form.lat)
    }
    if (editingId.value) await adminUpdateHotel(editingId.value, payload)
    else await adminCreateHotel(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await fetchHotels()
  } catch (e) {
    ElMessage.error(err(e, '保存失败'))
  } finally {
    submitting.value = false
  }
}

const toggleStatus = async (row) => {
  const next = row.status === 'on_shelf' ? 'off_shelf' : 'on_shelf'
  try {
    await adminHotelStatus(row.id, next)
    ElMessage.success(next === 'on_shelf' ? '已上架' : '已下架')
    await fetchHotels()
  } catch (e) {
    ElMessage.error(err(e, '操作失败'))
  }
}

const removeHotel = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该酒店吗？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await adminDeleteHotel(row.id)
    ElMessage.success('删除成功')
    await fetchHotels()
  } catch (e) {
    ElMessage.error(err(e, '删除失败'))
  }
}

watch(tab, (val) => {
  if (val === 'hotel') fetchHotels()
  else fetchOrders()
})

onMounted(fetchHotels)
</script>

<style scoped>
.card-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 10px; align-items: center; }
.card-title { font-weight: 600; }
.price { color: #f56c6c; font-weight: 600; }
.score-row { display: flex; align-items: center; gap: 8px; color: #606266; }
.coord-row { display: flex; align-items: center; gap: 8px; width: 100%; }
</style>
