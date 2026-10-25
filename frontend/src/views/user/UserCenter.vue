<template>
  <div class="user-center">
    <el-card>
      <template #header>个人中心</template>
      <el-tabs v-model="active">
        <el-tab-pane label="我的收藏" name="collect">
          <el-empty description="暂无收藏（骨架）" />
        </el-tab-pane>
        <el-tab-pane label="我的行程" name="trip">
          <el-empty description="暂无行程（骨架）" />
        </el-tab-pane>
        <el-tab-pane label="我的帖子" name="post">
          <el-empty description="暂无帖子（骨架）" />
        </el-tab-pane>
        <el-tab-pane label="我的评论" name="comment">
          <el-empty description="暂无评论（骨架）" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const active = ref('collect')
</script>
