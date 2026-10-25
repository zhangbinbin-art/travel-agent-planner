<template>
  <div class="spot-detail">
    <el-card>
      <template #header>景点详情（ID：{{ $route.params.id }}）</template>
      <el-descriptions title="基本信息" :column="2" border>
        <el-descriptions-item label="景点名称">{{ spot.name }}</el-descriptions-item>
        <el-descriptions-item label="城市">{{ spot.city }}</el-descriptions-item>
        <el-descriptions-item label="评分">{{ spot.score }} 分</el-descriptions-item>
        <el-descriptions-item label="标签">{{ spot.tags.join('、') }}</el-descriptions-item>
        <el-descriptions-item label="简介" :span="2">{{ spot.desc }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>评论情感占比（预留）</el-divider>
      <div id="emotion-chart" class="emotion-chart"></div>
      <el-divider>评论列表</el-divider>
      <el-table :data="comments" style="width: 100%">
        <el-table-column prop="user" label="用户" width="120" />
        <el-table-column prop="content" label="评论内容" />
        <el-table-column prop="score" label="评分" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { mockSpots, mockComments } from '@/api/mock'
const spot = mockSpots.find(s => s.id == 1) || mockSpots[0]
const comments = mockComments
</script>

<style scoped>
.emotion-chart {
  width: 100%;
  height: 320px;
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}
.emotion-chart::after {
  content: 'ECharts 情感占比饼图预留位置（jieba + SnowNLP）';
}
</style>
