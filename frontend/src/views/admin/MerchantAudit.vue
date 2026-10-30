<template>
  <div class="merchant-audit">
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMerchantList, auditMerchant } from '@/api/hotel'

const merchants = ref([])
const loading = ref(false)
const auditFilter = ref('')

const statusText = (s) =>
  ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s)
const statusType = (s) =>
  ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')

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

onMounted(fetchList)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
</style>
