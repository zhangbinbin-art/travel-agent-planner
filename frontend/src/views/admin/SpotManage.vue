<template>
  <div class="spot-manage">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">景点管理</span>
          <div class="header-actions">
            <el-input
              v-model="keyword"
              placeholder="按名称/城市搜索"
              clearable
              class="search-input"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            />
            <el-button size="small" @click="handleSearch">查询</el-button>
            <el-button type="primary" size="small" @click="openCreate">新增景点</el-button>
          </div>
        </div>
      </template>

      <el-table :data="spots" v-loading="loading" empty-text="暂无景点" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="city" label="城市" width="110" />
        <el-table-column prop="theme" label="主题" width="120" />
        <el-table-column label="评分" width="90">
          <template #default="{ row }">{{ formatScore(row.score) }}</template>
        </el-table-column>
        <el-table-column label="门票" width="100">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.price) }}</span></template>
        </el-table-column>
        <el-table-column label="坐标" min-width="190">
          <template #default="{ row }">
            <span v-if="hasCoords(row)">{{ Number(row.lng).toFixed(6) }}, {{ Number(row.lat).toFixed(6) }}</span>
            <el-tag v-else size="small" type="info">未设置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="removeSpot(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50]"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑景点' : '新增景点'"
      width="600px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="景点名称" prop="name">
          <el-input v-model="form.name" maxlength="100" placeholder="例如：杭州西湖" />
        </el-form-item>
        <el-form-item label="城市">
          <el-input v-model="form.city" placeholder="例如：杭州" />
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="form.province" placeholder="例如：浙江省" />
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="form.theme" placeholder="例如：自然风光" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="评分">
          <el-input-number v-model="form.score" :min="0" :max="5" :step="0.1" :precision="1" />
        </el-form-item>
        <el-form-item label="门票价">
          <el-input-number v-model="form.price" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="封面图">
          <el-input v-model="form.cover" placeholder="图片链接" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="经纬度">
          <div class="coord-row">
            <el-input v-model="form.lng" placeholder="经度，如 120.153576" />
            <el-input v-model="form.lat" placeholder="纬度，如 30.287459" />
            <el-button :loading="geoLoading" @click="fetchCoords">按名称获取</el-button>
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
import { reactive, ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSpotList, createSpot, updateSpot, deleteSpot } from '@/api/spot'
import { geoCode } from '@/api/map'

const spots = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const geoLoading = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  city: '',
  province: '',
  theme: '',
  tags: '',
  description: '',
  score: 0,
  price: 0,
  cover: '',
  lng: '',
  lat: ''
})

const rules = {
  name: [{ required: true, message: '请输入景点名称', trigger: 'blur' }]
}

const err = (e, fallback) => e?.response?.data?.detail || fallback
const hasCoords = (row) => row?.lng != null && row?.lat != null && row.lng !== '' && row.lat !== ''
const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))
const formatScore = (v) => {
  const n = Number(v)
  return Number.isNaN(n) ? '-' : n.toFixed(1)
}

const fetchSpots = async () => {
  loading.value = true
  try {
    const res = await getSpotList({
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    spots.value = res.data?.items || []
    total.value = Number(res.data?.total) || 0
  } catch (e) {
    ElMessage.error(err(e, '获取景点列表失败'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  fetchSpots()
}

const handlePageChange = (val) => {
  page.value = val
  fetchSpots()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  page.value = 1
  fetchSpots()
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    city: '',
    province: '',
    theme: '',
    tags: '',
    description: '',
    score: 0,
    price: 0,
    cover: '',
    lng: '',
    lat: ''
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
    city: row.city || '',
    province: row.province || '',
    theme: row.theme || '',
    tags: row.tags || '',
    description: row.description || '',
    score: Number(row.score) || 0,
    price: Number(row.price) || 0,
    cover: row.cover || '',
    lng: row.lng == null ? '' : String(row.lng),
    lat: row.lat == null ? '' : String(row.lat)
  })
  dialogVisible.value = true
}

// 按景点名称一键获取经纬度（后端转发高德 Web 服务地理编码）
const fetchCoords = async () => {
  const name = (form.name || '').trim()
  if (!name) {
    ElMessage.warning('请先填写景点名称')
    return
  }
  geoLoading.value = true
  try {
    const res = await geoCode(name, (form.city || '').trim() || undefined)
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
      name: form.name.trim(),
      city: form.city.trim() || null,
      province: form.province.trim() || null,
      theme: form.theme.trim() || null,
      tags: form.tags.trim() || null,
      description: form.description || null,
      score: Number(form.score) || 0,
      price: Number(form.price) || 0,
      cover: form.cover.trim() || null,
      lng: form.lng === '' || form.lng === null ? null : Number(form.lng),
      lat: form.lat === '' || form.lat === null ? null : Number(form.lat)
    }
    if (editingId.value) await updateSpot(editingId.value, payload)
    else await createSpot(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await fetchSpots()
  } catch (e) {
    ElMessage.error(err(e, '保存失败'))
  } finally {
    submitting.value = false
  }
}

const removeSpot = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该景点吗？', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteSpot(row.id)
    ElMessage.success('删除成功')
    await fetchSpots()
  } catch (e) {
    ElMessage.error(err(e, '删除失败'))
  }
}

onMounted(fetchSpots)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.search-input {
  width: 200px;
}
.card-title {
  font-weight: 600;
}
.price {
  color: #f56c6c;
  font-weight: 600;
}
.coord-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
