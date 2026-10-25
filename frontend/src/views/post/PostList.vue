<template>
  <div class="post-list">
    <el-card>
      <template #header>游记帖子列表</template>
      <el-form :inline="true">
        <el-form-item label="排序">
          <el-select v-model="sort" placeholder="请选择">
            <el-option label="最新" value="latest" />
            <el-option label="热度" value="hot" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary">应用</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="posts" style="width: 100%">
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="author" label="作者" width="140" />
        <el-table-column prop="heat" label="热度" width="120" />
      </el-table>
      <el-pagination class="pager" background layout="prev, pager, next" :total="posts.length" />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { mockHotPosts } from '@/api/mock'
const sort = ref('hot')
const posts = mockHotPosts
</script>

<style scoped>
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
