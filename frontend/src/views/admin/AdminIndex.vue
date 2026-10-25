<template>
  <div class="admin">
    <el-card>
      <template #header>管理员后台</template>
      <el-tabs v-model="active">
        <el-tab-pane label="用户管理" name="user">用户列表（骨架）</el-tab-pane>
        <el-tab-pane label="景点管理" name="spot">景点增删改查（骨架）</el-tab-pane>
        <el-tab-pane label="游记审核" name="post">游记审核（骨架）</el-tab-pane>
        <el-tab-pane label="评论管理" name="comment">评论管理（骨架）</el-tab-pane>
        <el-tab-pane label="数据统计" name="stats">
          <div id="admin-stats" class="stats-chart"></div>
          <div class="hint">预留 ECharts 数据统计图表</div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const active = ref('user')
</script>

<style scoped>
.stats-chart {
  width: 100%;
  height: 320px;
  background: #fafafa;
  border: 1px dashed #dcdfe6;
}
.hint {
  color: #909399;
  font-size: 13px;
  margin-top: 6px;
}
</style>
