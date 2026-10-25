<template>
  <div class="spot-list">
    <el-card>
      <template #header>景点列表</template>
      <el-form :inline="true" :model="filters">
        <el-form-item label="城市">
          <el-select v-model="filters.city" placeholder="全部" clearable>
            <el-option label="杭州" value="杭州" />
            <el-option label="北京" value="北京" />
            <el-option label="上海" value="上海" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="filters.tag" placeholder="全部" clearable>
            <el-option label="自然风光" value="自然风光" />
            <el-option label="历史文化" value="历史文化" />
            <el-option label="城市观光" value="城市观光" />
          </el-select>
        </el-form-item>
        <el-form-item label="评分">
          <el-select v-model="filters.score" placeholder="全部" clearable>
            <el-option label="4.9分以上" value="4.9" />
            <el-option label="4.8分以上" value="4.8" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary">筛选</el-button>
        </el-form-item>
      </el-form>
      <el-row :gutter="16">
        <el-col v-for="spot in spots" :key="spot.id" :span="6">
          <el-card shadow="hover" @click="$router.push(`/spot-detail/${spot.id}`)">
            <div class="spot-title">{{ spot.name }}</div>
            <div class="spot-desc">{{ spot.desc }}</div>
            <div class="spot-tags">
              <el-tag v-for="t in spot.tags" :key="t" size="small">{{ t }}</el-tag>
            </div>
            <div class="spot-score">{{ spot.score }} 分</div>
          </el-card>
        </el-col>
      </el-row>
      <el-pagination class="pager" background layout="prev, pager, next" :total="spots.length" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { mockSpots } from '@/api/mock'
const filters = reactive({ city: '', tag: '', score: '' })
const spots = mockSpots
</script>

<style scoped>
.spot-title { font-weight: 600; }
.spot-desc { color: #606266; font-size: 13px; margin: 6px 0; }
.spot-tags { display: flex; gap: 6px; }
.spot-score { margin-top: 8px; color: #f59e0b; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
