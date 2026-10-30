<template>
  <div class="guests">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">客人登记</span>
          <el-button type="primary" @click="dialogVisible = true">入住登记</el-button>
        </div>
      </template>
      <el-table :data="guests" v-loading="loading" style="width: 100%">
        <el-table-column prop="order_id" label="订单号" width="90" />
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column prop="id_card" label="身份证号" min-width="190" />
        <el-table-column prop="room_type" label="房型" min-width="130" />
        <el-table-column label="入住时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.checkin_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="入住登记" width="480px">
      <el-form label-width="90px">
        <el-form-item label="订单号">
          <el-input-number v-model="form.order_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" placeholder="留空则使用订单实名信息" />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="form.id_card" placeholder="留空则使用订单实名信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确认登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getGuests, checkinGuest } from '@/api/hotel'

const guests = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({ order_id: null, real_name: '', id_card: '' })

const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '')

const fetchGuests = async () => {
  loading.value = true
  try {
    const res = await getGuests()
    guests.value = res.data || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取客人记录失败')
  } finally {
    loading.value = false
  }
}

const submit = async () => {
  if (!form.order_id) {
    ElMessage.warning('请输入订单号')
    return
  }
  submitting.value = true
  try {
    await checkinGuest({
      order_id: form.order_id,
      real_name: form.real_name || undefined,
      id_card: form.id_card || undefined
    })
    ElMessage.success('登记成功')
    dialogVisible.value = false
    form.order_id = null
    form.real_name = ''
    form.id_card = ''
    await fetchGuests()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '登记失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchGuests)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; }
</style>
