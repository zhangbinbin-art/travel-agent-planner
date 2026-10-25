<template>
  <el-card shadow="hover" class="spot-card" @click="goDetail">
    <div class="spot-title">{{ spot.name }}</div>
    <div class="spot-city">{{ spot.city }}</div>
    <div class="spot-desc">{{ spot.description || spot.desc }}</div>
    <div class="spot-tags" v-if="spot.tags">
      <el-tag v-for="t in tagList" :key="t" size="small">{{ t }}</el-tag>
    </div>
    <div class="spot-score">{{ spot.score }} 分</div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  spot: {
    type: Object,
    required: true
  }
})

const router = useRouter()
const goDetail = () => {
  router.push(`/spot-detail/${props.spot.id}`)
}

const tagList = computed(() => {
  if (Array.isArray(props.spot.tags)) return props.spot.tags
  if (typeof props.spot.tags === 'string') {
    return props.spot.tags.split(/[,，;；]/).filter(Boolean)
  }
  return []
})
</script>

<style scoped>
.spot-card {
  cursor: pointer;
  height: 100%;
}
.spot-title {
  font-weight: 600;
  font-size: 16px;
}
.spot-city {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}
.spot-desc {
  color: #606266;
  font-size: 13px;
  margin: 6px 0;
  min-height: 40px;
}
.spot-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.spot-score {
  margin-top: 8px;
  color: #f59e0b;
}
</style>
