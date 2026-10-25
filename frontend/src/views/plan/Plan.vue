<template>
  <div class="plan">
    <el-card>
      <template #header>智能路线规划</template>
      <el-form :model="form" label-width="100px">
        <el-form-item label="选择景点">
          <el-checkbox-group v-model="form.spots">
            <el-checkbox label="西湖景区" />
            <el-checkbox label="故宫博物院" />
            <el-checkbox label="外滩" />
            <el-checkbox label="灵隐寺" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="游玩天数">
          <el-input-number v-model="form.days" :min="1" :max="7" />
        </el-form-item>
        <el-form-item label="游玩时长">
          <el-input-number v-model="form.hours" :min="2" :max="12" />
        </el-form-item>
        <el-form-item label="偏好权重">
          <el-slider v-model="form.weight" show-input :min="0" :max="100" />
          <div class="hint">预留偏好权重设置（个性化）</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary">生成路线（预览）</el-button>
        </el-form-item>
      </el-form>
      <el-divider>路线预览</el-divider>
      <el-empty description="生成路线后展示路线表（骨架）" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
const form = reactive({
  spots: [],
  days: 1,
  hours: 4,
  weight: 50
})
</script>

<style scoped>
.hint {
  color: #909399;
  font-size: 13px;
  margin-top: 6px;
}
</style>
