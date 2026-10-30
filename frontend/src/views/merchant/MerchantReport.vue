<template>
  <div class="report">
    <el-row :gutter="16">
      <el-col :xs="12" :md="6">
        <el-card shadow="hover" class="stat"><div class="label">总订单</div><div class="value">{{ report.order_total || 0 }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="hover" class="stat"><div class="label">已支付/已入住</div><div class="value">{{ report.paid_total || 0 }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="hover" class="stat"><div class="label">营收</div><div class="value price">¥{{ formatMoney(report.revenue) }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="hover" class="stat"><div class="label">入住率</div><div class="value">{{ report.occupancy_rate || 0 }}%</div></el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="daily-card">
      <template #header><span class="card-title">每日营收明细</span></template>
      <el-table :data="report.daily || []" style="width: 100%">
        <el-table-column prop="date" label="日期" width="160" />
        <el-table-column prop="orders" label="订单数" width="120" />
        <el-table-column label="营收">
          <template #default="{ row }"><span class="price">¥{{ formatMoney(row.revenue) }}</span></template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!(report.daily || []).length" description="暂无营收记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getReport } from '@/api/hotel'

const report = ref({})
const formatMoney = (v) => (Number.isNaN(Number(v)) ? '0.00' : Number(v).toFixed(2))

const fetchReport = async () => {
  try {
    const res = await getReport()
    report.value = res.data || {}
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取报表失败')
  }
}

onMounted(fetchReport)
</script>

<style scoped>
.stat { text-align: center; margin-bottom: 16px; }
.label { color: #909399; font-size: 14px; }
.value { font-size: 28px; font-weight: 700; margin-top: 8px; color: #303133; }
.price { color: #f56c6c; }
.card-title { font-weight: 600; }
.daily-card { margin-top: 8px; }
</style>
