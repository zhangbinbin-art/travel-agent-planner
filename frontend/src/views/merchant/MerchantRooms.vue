<template>
  <div class="rooms">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">客房管理</span>
          <el-button type="primary" @click="openCreate">新增客房</el-button>
        </div>
      </template>
      <el-table :data="rooms" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="room_type" label="房型" min-width="140" />
        <el-table-column prop="bed_info" label="床型" min-width="140" />
        <el-table-column label="房价" width="110">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.room_price) }}</span></template>
        </el-table-column>
        <el-table-column prop="max_guest" label="可住" width="70" />
        <el-table-column prop="stock" label="库存" width="70" />
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-select :model-value="row.status" size="small" @change="(v) => changeStatus(row, v)">
              <el-option label="空闲" value="free" />
              <el-option label="入住" value="occupied" />
              <el-option label="打扫" value="cleaning" />
              <el-option label="维修" value="maintenance" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="removeRoom(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑客房' : '新增客房'" width="520px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="房型" prop="room_type">
          <el-input v-model="form.room_type" placeholder="如：标准大床房" />
        </el-form-item>
        <el-form-item label="房价" prop="room_price">
          <el-input-number v-model="form.room_price" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="床型">
          <el-input v-model="form.bed_info" placeholder="如：1.8m大床" />
        </el-form-item>
        <el-form-item label="可住人数">
          <el-input-number v-model="form.max_guest" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="库存">
          <el-input-number v-model="form.stock" :min="0" :max="999" />
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
import { reactive, ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRooms, createRoom, updateRoom, updateRoomStatus, deleteRoom } from '@/api/hotel'

const rooms = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({ room_type: '', room_price: 268, bed_info: '', max_guest: 2, stock: 10 })
const rules = { room_type: [{ required: true, message: '请输入房型', trigger: 'blur' }] }

const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const err = (e, f) => e?.response?.data?.detail || f

const fetchRooms = async () => {
  loading.value = true
  try {
    const res = await getRooms()
    rooms.value = res.data || []
  } catch (e) {
    ElMessage.error(err(e, '获取客房失败'))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, { room_type: '', room_price: 268, bed_info: '', max_guest: 2, stock: 10 })
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
    room_type: row.room_type,
    room_price: Number(row.room_price) || 0,
    bed_info: row.bed_info || '',
    max_guest: row.max_guest || 1,
    stock: row.stock ?? 0
  })
  dialogVisible.value = true
}

const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) await updateRoom(editingId.value, { ...form })
    else await createRoom({ ...form })
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await fetchRooms()
  } catch (e) {
    ElMessage.error(err(e, '保存失败'))
  } finally {
    submitting.value = false
  }
}

const changeStatus = async (row, status) => {
  try {
    await updateRoomStatus(row.id, status)
    ElMessage.success('状态已更新')
    await fetchRooms()
  } catch (e) {
    ElMessage.error(err(e, '操作失败'))
  }
}

const removeRoom = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该客房吗？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteRoom(row.id)
    ElMessage.success('删除成功')
    await fetchRooms()
  } catch (e) {
    ElMessage.error(err(e, '删除失败'))
  }
}

onMounted(fetchRooms)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; }
.price { color: #f56c6c; font-weight: 600; }
</style>
