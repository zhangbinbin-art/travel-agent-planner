<template>
  <aside class="filter-side" :class="{ collapsed: !open }">
    <div class="filter-clip">
      <div class="filter-panel" :class="{ closed: !open }">
        <el-card shadow="never" class="filter-card">
          <div class="filter-header">
            <span class="filter-header-title">筛选</span>
            <el-button link type="primary" size="small" @click="$emit('toggle')">
              收起筛选
            </el-button>
          </div>

          <div class="filter-block">
            <div class="filter-title">热门目的地</div>
            <div class="tag-group">
              <el-tag
                v-for="item in hotDest"
                :key="item"
                :type="activeDest === item ? 'primary' : 'info'"
                effect="plain"
                class="filter-tag"
                @click="$emit('select-dest', item)"
              >
                {{ item }}
              </el-tag>
            </div>
            <div v-if="activeDest && !hotDest.includes(activeDest)" class="selected-dest">
              已选城市：
              <el-tag
                type="primary"
                effect="dark"
                size="small"
                class="filter-tag"
                @click="$emit('select-dest', activeDest)"
              >
                {{ activeDest }} ×
              </el-tag>
            </div>
            <div class="all-region-row">
              <el-button link type="primary" size="small" @click="openCityDialog">
                查看全部地区
              </el-button>
            </div>
          </div>

          <el-divider />
          <div class="filter-block">
            <div class="filter-title">旅游主题</div>
            <div class="tag-group">
              <el-tag
                v-for="item in themes"
                :key="item"
                :type="activeThemes.includes(item) ? 'primary' : 'info'"
                effect="plain"
                class="filter-tag"
                @click="$emit('toggle-theme', item)"
              >
                {{ item }}
              </el-tag>
            </div>
          </div>

          <el-divider />
          <div class="filter-block">
            <div class="filter-title">热门景点</div>
            <div class="tag-group">
              <el-tag
                v-for="item in hotSpotTags"
                :key="item"
                :type="activeSpot === item ? 'primary' : 'info'"
                effect="plain"
                class="filter-tag"
                @click="$emit('select-hot', item)"
              >
                {{ item }}
              </el-tag>
            </div>
          </div>

          <el-button type="primary" class="recommend-btn" @click="$emit('recommend')">
            推荐发现
          </el-button>
        </el-card>
      </div>
    </div>

    <button v-show="!open" class="filter-fab" type="button" @click="$emit('toggle')">
      展开筛选
    </button>

    <el-dialog v-model="cityDialogVisible" title="选择目的地" width="520px" append-to-body>
      <el-input
        v-model="cityKeyword"
        placeholder="搜索城市"
        clearable
        class="city-search"
      />
      <div class="city-list">
        <el-tag
          v-for="city in filteredCities"
          :key="city"
          :type="activeDest === city ? 'primary' : 'info'"
          :effect="activeDest === city ? 'dark' : 'plain'"
          class="city-tag"
          @click="pickCity(city)"
        >
          {{ city }}
        </el-tag>
      </div>
      <el-empty v-if="!filteredCities.length" description="没有匹配的城市" :image-size="80" />
    </el-dialog>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: true },
  activeDest: { type: String, default: '' },
  activeThemes: { type: Array, default: () => [] },
  activeSpot: { type: String, default: '' },
  cities: { type: Array, default: () => [] }
})

const emit = defineEmits(['toggle', 'select-dest', 'toggle-theme', 'select-hot', 'recommend'])

const hotDest = ['北京', '上海', '杭州', '广州', '桂林', '厦门']
const themes = ['自然风景', '历史古迹', '城市观光', '主题乐园']
const hotSpotTags = ['西湖景区', '故宫博物院', '外滩']

const cityDialogVisible = ref(false)
const cityKeyword = ref('')

const filteredCities = computed(() => {
  const list = [...(props.cities || [])].sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'))
  const kw = cityKeyword.value.trim().toLowerCase()
  if (!kw) return list
  return list.filter((c) => String(c).toLowerCase().includes(kw))
})

const openCityDialog = () => {
  cityKeyword.value = ''
  cityDialogVisible.value = true
}

const pickCity = (city) => {
  cityDialogVisible.value = false
  emit('select-dest', city)
}
</script>

<style scoped>
.filter-side {
  position: sticky;
  top: 0;
  align-self: flex-start;
  width: 240px;
  flex-shrink: 0;
  transition: width 0.3s ease;
}
.filter-side.collapsed {
  width: 0;
}
.filter-clip {
  width: 100%;
  overflow: hidden;
}
.filter-panel {
  width: 240px;
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.filter-panel.closed {
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
}
.filter-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.filter-header-title {
  font-weight: 600;
  color: #303133;
}
.filter-block {
  padding: 8px 0;
}
.filter-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: #303133;
}
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-tag {
  cursor: pointer;
  border-radius: 4px;
}
.selected-dest {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}
.all-region-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}
.recommend-btn {
  width: 100%;
  margin-top: 14px;
}
.filter-fab {
  position: absolute;
  left: 0;
  top: 12px;
  z-index: 10;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
  padding: 12px 6px;
  border: 1px solid #dcdfe6;
  border-left: none;
  border-radius: 0 6px 6px 0;
  background: #fff;
  color: #409eff;
  font-size: 13px;
  cursor: pointer;
  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.08);
  transition: background 0.2s, color 0.2s;
}
.filter-fab:hover {
  background: #409eff;
  color: #fff;
}
.city-search {
  margin-bottom: 12px;
}
.city-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 300px;
  overflow: auto;
}
.city-tag {
  cursor: pointer;
  border-radius: 4px;
}
</style>
