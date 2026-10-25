<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>热门景点</template>
          <el-row :gutter="12">
            <el-col v-for="spot in hotSpots" :key="spot.id" :span="8">
              <el-card shadow="hover" @click="$router.push(`/spot-detail/${spot.id}`)">
                <div class="spot-name">{{ spot.name }}</div>
                <div class="spot-meta">{{ spot.city }} | {{ spot.tags.join('、') }} | {{ spot.score }}分</div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>高热游记</template>
          <el-table :data="hotPosts" style="width: 100%">
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="author" label="作者" width="120" />
            <el-table-column prop="heat" label="热度" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { mockHotSpots, mockHotPosts } from '@/api/mock'
const hotSpots = mockHotSpots
const hotPosts = mockHotPosts
</script>

<style scoped>
.spot-name { font-weight: 600; }
.spot-meta { color: #909399; font-size: 13px; margin-top: 6px; }
</style>
