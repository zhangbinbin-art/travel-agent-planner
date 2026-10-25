<template>
  <div class="spot-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="card-title">景点列表</span>
          <el-button v-if="auth.role === 'admin'" type="primary" @click="openCreate">新增景点</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="filters" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索景点名称或城市" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-row :gutter="16">
        <el-col v-for="spot in spots" :key="spot.id" :span="6" class="spot-col">
          <div class="spot-wrap">
            <SpotCard :spot="spot" />
            <div v-if="auth.role === 'admin'" class="admin-actions">
              <el-button size="small" @click.stop="openEdit(spot)">编辑</el-button>
              <el-button size="small" type="danger" @click.stop="handleDelete(spot)">删除</el-button>
            </div>
          </div>
        </el-col>
      </el-row>
      <el-pagination
        class="pager"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="handlePageChange"
      />

      <el-dialog
        v-model="dialogVisible"
        :title="dialogMode === 'edit' ? '编辑景点' : '新增景点'"
        width="520px"
        @closed="resetForm"
      >
        <el-form ref="formRef" :model="form" :rules="rules" label-width="72px">
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" maxlength="100" placeholder="请输入景点名称" />
          </el-form-item>
          <el-form-item label="城市" prop="city">
            <el-input v-model="form.city" placeholder="请输入所在城市" />
          </el-form-item>
          <el-form-item label="标签" prop="tags">
            <el-input v-model="form.tags" placeholder="多个标签用逗号分隔" />
          </el-form-item>
          <el-form-item label="简介" prop="description">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入景点简介" />
          </el-form-item>
          <el-form-item label="评分" prop="score">
            <el-input-number v-model="form.score" :min="0" :max="5" :step="0.1" :precision="1" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">确定</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSpotList, createSpot, updateSpot, deleteSpot } from '@/api/spot'
import { auth } from '@/utils/auth'
import SpotCard from '@/components/SpotCard.vue'

const filters = reactive({ keyword: '' })
const spots = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)

const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({ name: '', city: '', tags: '', description: '', score: 0 })

const rules = {
  name: [{ required: true, message: '请输入景点名称', trigger: 'blur' }]
}

const extractError = (e, fallback) => {
  if (e?.response?.status === 403) return '无权限操作'
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

const resetForm = () => {
  Object.assign(form, { name: '', city: '', tags: '', description: '', score: 0 })
  editingId.value = null
  formRef.value?.clearValidate()
}

const openCreate = () => {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

const openEdit = (spot) => {
  dialogMode.value = 'edit'
  editingId.value = spot.id
  Object.assign(form, {
    name: spot.name || '',
    city: spot.city || '',
    tags: Array.isArray(spot.tags) ? spot.tags.join(',') : (spot.tags || ''),
    description: spot.description || spot.desc || '',
    score: typeof spot.score === 'number' ? spot.score : Number(spot.score) || 0
  })
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

const submitForm = async () => {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const payload = {
    name: form.name.trim(),
    city: form.city.trim(),
    tags: form.tags.trim(),
    description: form.description.trim(),
    score: Number.isFinite(Number(form.score)) ? Number(form.score) : 0
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'edit') {
      await updateSpot(editingId.value, payload)
    } else {
      await createSpot(payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    resetForm()
    await fetchList()
  } catch (e) {
    ElMessage.error(extractError(e, '保存失败'))
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (spot) => {
  try {
    await ElMessageBox.confirm('确定删除该景点吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteSpot(spot.id)
    ElMessage.success('删除成功')
    await fetchList()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

const fetchList = async () => {
  const res = await getSpotList({
    keyword: filters.keyword || undefined,
    page: page.value,
    page_size: pageSize.value
  })
  spots.value = res.data.items || []
  total.value = res.data.total || 0
}

const handleSearch = () => {
  page.value = 1
  fetchList()
}

const reset = () => {
  filters.keyword = ''
  page.value = 1
  fetchList()
}

const handlePageChange = (p) => {
  page.value = p
  fetchList()
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.card-header { display: flex; align-items: center; justify-content: space-between; }
.card-title { font-weight: 600; }
.spot-col { margin-bottom: 16px; }
.spot-wrap { display: flex; flex-direction: column; height: 100%; }
.spot-wrap :deep(.el-card) { flex: 1; }
.admin-actions { display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end; }
.spot-title { font-weight: 600; }
.spot-desc { color: #606266; font-size: 13px; margin: 6px 0; }
.spot-tags { display: flex; gap: 6px; }
.spot-score { margin-top: 8px; color: #f59e0b; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
