<template>
  <div class="rooms">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">客房管理</span>
          <el-button type="primary" @click="openCreate">新增客房</el-button>
        </div>
      </template>

      <el-empty v-if="!loading && !rooms.length" description="暂无客房，点击右上角新增" />

      <el-row :gutter="16" v-loading="loading">
        <el-col :xs="24" :sm="12" :md="8" v-for="room in rooms" :key="room.id">
          <div class="room-card" :class="'status-' + room.status">
            <div class="room-cover">
              <img :src="room.image_url || defaultRoomImg" alt="房型图片" />
              <el-tag class="status-tag" size="small" :color="statusColor(room.status)" effect="dark">
                {{ statusText(room.status) }}
              </el-tag>
            </div>
            <div class="room-body">
              <div class="room-name">{{ room.room_type }}</div>
              <div class="room-meta">{{ room.bed_info || '床型待补充' }} ｜ 可住 {{ room.max_guest }} 人</div>
              <div class="room-bottom">
                <span class="price">¥{{ formatMoney(room.room_price) }}/晚</span>
                <span class="stock">库存 {{ room.stock }}</span>
              </div>
              <div class="room-actions">
                <el-select :model-value="room.status" size="small" @change="(v) => changeStatus(room, v)">
                  <el-option label="空闲" value="free" />
                  <el-option label="入住" value="occupied" />
                  <el-option label="打扫" value="cleaning" />
                  <el-option label="维修" value="maintenance" />
                </el-select>
                <div class="btns">
                  <el-button size="small" @click="openEdit(room)">编辑</el-button>
                  <el-button size="small" type="danger" @click="removeRoom(room)">删除</el-button>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑客房' : '新增客房'" width="560px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="房型" prop="room_type">
          <el-input v-model="form.room_type" placeholder="如：标准大床房" />
        </el-form-item>
        <el-form-item label="房型图片">
          <el-input v-model="form.image_url" placeholder="图片链接，或选择本地图片" clearable />
          <el-upload
            class="upload-room"
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :on-change="onImageChange"
          >
            <el-button size="small">本地选择图片</el-button>
          </el-upload>
          <img v-if="form.image_url" :src="form.image_url" class="image-preview" alt="预览" />
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

const defaultRoomImg =
  'https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=800&q=80'

const rooms = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({
  room_type: '',
  image_url: '',
  room_price: 268,
  bed_info: '',
  max_guest: 2,
  stock: 10
})
const rules = { room_type: [{ required: true, message: '请输入房型', trigger: 'blur' }] }

const statusText = (s) =>
  ({ free: '空闲', occupied: '入住', cleaning: '打扫', maintenance: '维修' }[s] || s)
const statusColor = (s) =>
  ({ free: '#67c23a', occupied: '#e6a23c', cleaning: '#409eff', maintenance: '#909399' }[s] || '#909399')
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
  Object.assign(form, {
    room_type: '',
    image_url: '',
    room_price: 268,
    bed_info: '',
    max_guest: 2,
    stock: 10
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
    room_type: row.room_type,
    image_url: row.image_url || '',
    room_price: Number(row.room_price) || 0,
    bed_info: row.bed_info || '',
    max_guest: row.max_guest || 1,
    stock: row.stock ?? 0
  })
  dialogVisible.value = true
}

const onImageChange = (file) => {
  const raw = file?.raw
  if (!raw) return
  if (!raw.type?.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  if (raw.size > 2 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 2MB')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    form.image_url = String(reader.result || '')
  }
  reader.readAsDataURL(raw)
}

const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = { ...form, image_url: form.image_url || null }
    if (editingId.value) await updateRoom(editingId.value, payload)
    else await createRoom(payload)
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
.room-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.room-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}
.room-card.status-free { border-top: 3px solid #67c23a; }
.room-card.status-occupied { border-top: 3px solid #e6a23c; }
.room-card.status-cleaning { border-top: 3px solid #409eff; }
.room-card.status-maintenance { border-top: 3px solid #909399; }
.room-cover {
  position: relative;
  height: 160px;
  overflow: hidden;
  background: #f5f7fa;
}
.room-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.status-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  border: none;
}
.room-body { padding: 12px 14px 14px; }
.room-name { font-size: 16px; font-weight: 600; color: #303133; }
.room-meta { color: #909399; font-size: 13px; margin-top: 6px; }
.room-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}
.price { color: #f56c6c; font-weight: 700; }
.stock { color: #606266; font-size: 13px; }
.room-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}
.btns { display: flex; gap: 6px; }
.upload-room { margin-top: 8px; }
.image-preview {
  margin-top: 8px;
  width: 100%;
  max-height: 150px;
  object-fit: cover;
  border-radius: 6px;
}
</style>
