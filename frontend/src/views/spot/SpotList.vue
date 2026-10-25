<template>
  <div class="spot-list">
    <el-card>
      <template #header>景点列表</template>
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
        <el-col v-for="spot in spots" :key="spot.id" :span="6">
          <SpotCard :spot="spot" />
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
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { getSpotList } from '@/api/spot'
import SpotCard from '@/components/SpotCard.vue'

const filters = reactive({ keyword: '' })
const spots = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)

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
.spot-title { font-weight: 600; }
.spot-desc { color: #606266; font-size: 13px; margin: 6px 0; }
.spot-tags { display: flex; gap: 6px; }
.spot-score { margin-top: 8px; color: #f59e0b; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
