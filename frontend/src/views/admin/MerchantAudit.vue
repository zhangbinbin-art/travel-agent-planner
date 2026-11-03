<template>
  <div class="merchant-audit">
    <!-- ============ 酒店资料 / 资质审核 ============ -->
    <el-card shadow="never" class="audit-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">酒店资料 & 资质审核</span>
          <div class="header-actions">
            <el-input
              v-model="keyword"
              placeholder="手机号 / 酒店名称"
              clearable
              class="kw-input"
              @keyup.enter="fetchHotelAudits"
              @clear="fetchHotelAudits"
            />
            <el-button size="small" @click="fetchHotelAudits">查询</el-button>
            <el-button size="small" @click="fetchHotelAudits">刷新</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="auditStatus" @tab-change="fetchHotelAudits">
        <el-tab-pane label="待审核" name="pending" />
        <el-tab-pane label="已通过" name="approved" />
        <el-tab-pane label="已驳回" name="rejected" />
      </el-tabs>

      <div v-loading="hotelLoading" class="audit-list">
        <article v-for="item in hotelAudits" :key="item.kind + '-' + item.id" class="audit-item">
          <div class="audit-head">
            <div class="audit-title">
              <el-tag size="small" :type="item.kind === 'profile' ? 'primary' : 'warning'">
                {{ item.kind === 'profile' ? '酒店资料' : '酒店资质' }}
              </el-tag>
              <strong class="hotel-name">{{ item.hotel_name || '未填写酒店名称' }}</strong>
            </div>
            <el-tag size="small" :type="statusType(item.status)">{{ statusText(item.status) }}</el-tag>
          </div>

          <div class="audit-meta">
            <span>商户：{{ item.username || '-' }}</span>
            <span>手机号：{{ item.phone || '-' }}</span>
            <span>提交时间：{{ formatTime(item.submit_time) }}</span>
          </div>

          <div v-if="item.kind === 'profile'" class="audit-body">
            <p>地址：{{ item.payload?.address || '-' }}</p>
            <p>电话：{{ item.payload?.phone || '-' }}</p>
            <p>标签：{{ (item.payload?.tags || []).join('、') || '-' }}</p>
            <p>简介：{{ item.payload?.intro || '-' }}</p>
            <div class="img-row">
              <el-image
                v-for="(url, idx) in item.payload?.imgs || []"
                :key="idx"
                :src="url"
                :preview-src-list="item.payload?.imgs"
                :initial-index="idx"
                fit="cover"
                class="thumb"
              />
            </div>
          </div>
          <div v-else class="audit-body">
            <p>酒店全称：{{ item.payload?.hotel_full_name || '-' }}</p>
            <p>统一社会信用代码：{{ item.payload?.credit_code || '-' }}</p>
            <p>法人：{{ item.payload?.legal_name || '-' }} / {{ item.payload?.legal_phone || '-' }}</p>
            <div class="img-row">
              <el-image
                v-if="item.payload?.license_img"
                :src="item.payload.license_img"
                :preview-src-list="[item.payload.license_img]"
                fit="cover"
                class="thumb"
              />
              <el-image
                v-for="(url, idx) in item.payload?.id_card_imgs || []"
                :key="'id' + idx"
                :src="url"
                :preview-src-list="item.payload?.id_card_imgs"
                :initial-index="idx"
                fit="cover"
                class="thumb"
              />
            </div>
          </div>

          <p v-if="item.audit_msg" class="reject-msg">驳回原因：{{ item.audit_msg }}</p>

          <div v-if="item.status === 'pending'" class="audit-actions">
            <el-button size="small" type="success" @click="handleApprove(item)">通过</el-button>
            <el-button size="small" type="danger" @click="handleReject(item)">驳回</el-button>
          </div>
        </article>

        <EmptyState v-if="!hotelLoading && !hotelAudits.length" description="暂无待审核记录" />
      </div>
    </el-card>

    <!-- ============ 商家账号审核（原有逻辑保留） ============ -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">商家账号审核</span>
          <el-radio-group v-model="auditFilter" size="small" @change="fetchList">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待审核</el-radio-button>
            <el-radio-button value="approved">已通过</el-radio-button>
            <el-radio-button value="rejected">已驳回</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="merchants" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="商家账号" width="140" />
        <el-table-column prop="shop_name" label="店铺名称" min-width="160" />
        <el-table-column label="审核状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.audit_status)" size="small">
              {{ statusText(row.audit_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              type="success"
              :disabled="row.audit_status === 'approved'"
              @click="handleAudit(row, 'approved')"
            >
              通过
            </el-button>
            <el-button
              size="small"
              type="danger"
              :disabled="row.audit_status === 'rejected'"
              @click="handleAudit(row, 'rejected')"
            >
              驳回
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { auditMerchant, approveHotelAudit, getHotelAudits, getMerchantList, rejectHotelAudit } from '@/api/hotel'
import EmptyState from '@/components/EmptyState.vue'

const merchants = ref([])
const loading = ref(false)
const auditFilter = ref('')

const hotelAudits = ref([])
const hotelLoading = ref(false)
const auditStatus = ref('pending')
const keyword = ref('')

const statusText = (s) => ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s)
const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const fetchHotelAudits = async () => {
  hotelLoading.value = true
  try {
    const res = await getHotelAudits({ status: auditStatus.value, keyword: keyword.value.trim() })
    hotelAudits.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取审核列表失败')
  } finally {
    hotelLoading.value = false
  }
}

const handleApprove = async (item) => {
  try {
    await approveHotelAudit(item.kind, item.id)
    ElMessage.success('已通过审核')
    await fetchHotelAudits()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const handleReject = async (item) => {
  try {
    const { value } = await ElMessageBox.prompt('请填写驳回原因（会推送给商家）', '驳回审核', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '如：营业执照模糊、地址不准确、图片不符合要求',
      inputValidator: (val) => (val && val.trim() ? true : '请填写驳回原因')
    })
    await rejectHotelAudit(item.kind, item.id, value.trim())
    ElMessage.success('已驳回')
    await fetchHotelAudits()
  } catch (e) {
    /* 取消 */
  }
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getMerchantList({ audit_status: auditFilter.value || undefined })
    merchants.value = res.data?.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取商家列表失败')
  } finally {
    loading.value = false
  }
}

const handleAudit = async (row, status) => {
  try {
    await auditMerchant(row.id, status)
    ElMessage.success(status === 'approved' ? '已通过审核' : '已驳回')
    await fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

onMounted(() => {
  fetchHotelAudits()
  fetchList()
})
</script>

<style scoped>
.audit-card {
  margin-bottom: 18px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.kw-input {
  width: 200px;
}
.card-title {
  font-weight: 800;
}
.audit-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.audit-item {
  padding: 14px 16px;
  border: 2px solid rgba(34, 34, 34, 0.14);
  border-radius: 10px;
  background: #fff;
}
.audit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.audit-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.hotel-name {
  font-size: 15px;
  color: #222;
}
.audit-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 8px 0;
  font-size: 12.5px;
  color: #7b8794;
}
.audit-body p {
  margin: 4px 0;
  font-size: 13px;
  color: #3d4753;
}
.img-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.thumb {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  border: 1px solid rgba(34, 34, 34, 0.16);
}
.reject-msg {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: #f56c6c;
}
.audit-actions {
  margin-top: 10px;
}
</style>
