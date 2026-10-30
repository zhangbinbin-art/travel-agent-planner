<template>
  <div class="hotel-filter">
    <div class="filter-row">
      <span class="filter-label">酒店类型</span>
      <el-checkbox-group v-model="types" size="small" class="filter-tags" :disabled="disabled">
        <el-checkbox-button v-for="t in HOTEL_TYPES" :key="t" :value="t">{{ t }}</el-checkbox-button>
      </el-checkbox-group>
    </div>
    <div class="filter-row">
      <span class="filter-label">价格区间</span>
      <div class="price-slider">
        <el-slider v-model="price" range :min="0" :max="2000" :step="50" :disabled="disabled" />
        <span class="price-text">¥{{ price[0] }} - ¥{{ price[1] }}</span>
      </div>
    </div>
    <div class="filter-row">
      <span class="filter-label">最低评分</span>
      <div class="score-inputs">
        <span>环境</span>
        <el-input-number v-model="minEnv" :min="0" :max="5" :step="0.1" :precision="1" size="small" :disabled="disabled" />
        <span>服务</span>
        <el-input-number v-model="minService" :min="0" :max="5" :step="0.1" :precision="1" size="small" :disabled="disabled" />
      </div>
    </div>
    <div class="filter-row">
      <span class="filter-label">特色标签</span>
      <el-checkbox-group v-model="features" size="small" class="filter-tags" :disabled="disabled">
        <el-checkbox-button v-for="f in FEATURE_TAGS" :key="f" :value="f">{{ f }}</el-checkbox-button>
      </el-checkbox-group>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { HOTEL_TYPES, FEATURE_TAGS } from '@/utils/hotel'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ types: [], price: [0, 2000], minEnv: 0, minService: 0, features: [] })
  },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const update = (patch) => {
  emit('update:modelValue', { ...props.modelValue, ...patch })
}

const types = computed({
  get: () => props.modelValue.types || [],
  set: (v) => update({ types: v })
})
const price = computed({
  get: () => props.modelValue.price || [0, 2000],
  set: (v) => update({ price: v })
})
const minEnv = computed({
  get: () => props.modelValue.minEnv || 0,
  set: (v) => update({ minEnv: v || 0 })
})
const minService = computed({
  get: () => props.modelValue.minService || 0,
  set: (v) => update({ minService: v || 0 })
})
const features = computed({
  get: () => props.modelValue.features || [],
  set: (v) => update({ features: v })
})
</script>

<style scoped>
.hotel-filter {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 12px;
}
.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.filter-label {
  width: 70px;
  flex-shrink: 0;
  color: #606266;
  font-size: 13px;
  line-height: 24px;
}
.filter-tags {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.price-slider {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}
.price-text {
  color: #f56c6c;
  font-size: 12px;
  white-space: nowrap;
}
.score-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}
</style>
