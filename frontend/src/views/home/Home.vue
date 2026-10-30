<template>
  <div class="home-fliggy">
    <div class="home-layout">
      <main class="main-content">
        <!-- 轮播图 -->
        <el-carousel height="240px" class="banner" indicator-position="outside">
          <el-carousel-item v-for="(img, idx) in banners" :key="idx">
            <img :src="img" class="banner-img" alt="风景" />
          </el-carousel-item>
        </el-carousel>

        <!-- 通栏筛选区（Banner 下方） -->
        <section class="filter-section">
          <div class="filter-section-head">
            <span class="filter-section-title">筛选</span>
          </div>

          <div class="filter-row">
            <span class="filter-row-label">热门目的地</span>
            <div class="filter-row-content">
              <el-tag
                v-for="item in hotDest"
                :key="item"
                :type="activeDest === item ? 'primary' : 'info'"
                :effect="activeDest === item ? 'dark' : 'plain'"
                class="filter-tag"
                @click="setDest(item)"
              >
                {{ item }}
              </el-tag>
              <el-tag
                v-if="activeDest && !hotDest.includes(activeDest)"
                type="primary"
                effect="dark"
                class="filter-tag"
                @click="setDest(activeDest)"
              >
                {{ activeDest }} ×
              </el-tag>
              <el-button link type="primary" size="small" @click="openCityDialog">
                查看全部地区
              </el-button>
            </div>
          </div>

          <div class="filter-row">
            <span class="filter-row-label">旅游主题</span>
            <div class="filter-row-content">
              <el-tag
                v-for="item in themes"
                :key="item"
                :type="activeThemes.includes(item) ? 'primary' : 'info'"
                :effect="activeThemes.includes(item) ? 'dark' : 'plain'"
                class="filter-tag"
                @click="toggleTheme(item)"
              >
                {{ item }}
              </el-tag>
            </div>
          </div>

          <div class="filter-row">
            <span class="filter-row-label">热门景点</span>
            <div class="filter-row-content">
              <el-tag
                v-for="item in hotSpotTags"
                :key="item"
                :type="activeSpotName === item ? 'primary' : 'info'"
                :effect="activeSpotName === item ? 'dark' : 'plain'"
                class="filter-tag"
                @click="setHotTag(item)"
              >
                {{ item }}
              </el-tag>
            </div>
          </div>

          <div class="filter-section-actions">
            <el-button type="primary" @click="handleRecommend">推荐发现</el-button>
          </div>
        </section>

        <!-- Tab 切换 -->
        <div class="tab-bar">
          <div
            class="tab-item"
            :class="{ active: activeTab === 'recommend' }"
            @click="activeTab = 'recommend'"
          >
            推荐发现
          </div>
          <div
            class="tab-item"
            :class="{ active: activeTab === 'all' }"
            @click="activeTab = 'all'"
          >
            全部景点检索
          </div>
        </div>

        <section class="spot-section">
          <div class="section-header">
            <div class="section-title">
              {{ activeTab === 'recommend' ? '推荐景点' : '全部景点' }}
              <span class="section-hint">
                {{ activeTab === 'recommend' ? '发现值得一去的好地方' : '支持关键词与标签组合检索' }}
              </span>
            </div>
            <div class="section-actions">
              <el-button
                v-if="activeTab === 'recommend'"
                type="primary"
                plain
                size="small"
                @click="activeTab = 'all'"
              >
                查看全部景点
              </el-button>
            </div>
          </div>

          <!-- 推荐发现 -->
          <div v-if="activeTab === 'recommend'" class="spot-body">
            <!-- 热度排行榜 -->
            <aside class="rank-panel">
              <div class="rank-header">景点热度排行榜</div>
              <div v-for="(s, i) in rankList" :key="s.id" class="rank-item">
                <span class="rank-num" :class="{ top: i < 3 }">{{ i + 1 }}</span>
                <div class="rank-info">
                  <div class="rank-name" @click="goDetail(s.id)">{{ s.name }}</div>
                  <div class="rank-price">¥{{ s.price || 0 }}起</div>
                </div>
              </div>
            </aside>

            <!-- 推荐卡片 -->
            <div class="spot-grid">
              <el-card
                v-for="s in displayList"
                :key="s.id"
                shadow="hover"
                class="spot-card"
                @click="goDetail(s.id)"
              >
                <div class="spot-img-wrap">
                  <img :src="s.cover || defaultImg" class="spot-img" alt="景点" />
                </div>
                <div class="spot-info">
                  <div class="spot-name">{{ s.name }}</div>
                  <div class="spot-city">{{ s.city }}</div>
                  <div class="spot-bottom">
                    <span class="spot-score">{{ s.score || '4.8' }}分</span>
                    <span class="spot-price">¥{{ s.price || 0 }}起</span>
                  </div>
                </div>
              </el-card>
              <el-empty v-if="!displayList.length" description="暂未找到符合条件的景点" class="empty-full" />
            </div>
          </div>

          <!-- 全部景点检索 -->
          <div v-else class="search-panel">
            <el-form :inline="true" class="search-form" @submit.prevent>
              <el-form-item>
                <el-input
                  v-model="keyword"
                  placeholder="搜索景点名称或城市"
                  clearable
                  style="width: 260px"
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleSearch">搜索</el-button>
                <el-button @click="resetFilters">重置</el-button>
              </el-form-item>
            </el-form>

            <div class="spot-grid full-grid">
              <el-card
                v-for="s in allGridList"
                :key="s.id"
                shadow="hover"
                class="spot-card"
                @click="goDetail(s.id)"
              >
                <div class="spot-img-wrap">
                  <img :src="s.cover || defaultImg" class="spot-img" alt="景点" />
                </div>
                <div class="spot-info">
                  <div class="spot-name">{{ s.name }}</div>
                  <div class="spot-city">{{ s.city }}</div>
                  <div class="spot-bottom">
                    <span class="spot-score">{{ s.score || '4.8' }}分</span>
                    <span class="spot-price">¥{{ s.price || 0 }}起</span>
                  </div>
                </div>
              </el-card>
            </div>
            <el-empty v-if="!allGridList.length" description="暂未找到符合条件的景点" />
          </div>
        </section>
      </main>
    </div>

    <el-dialog v-model="cityDialogVisible" title="选择目的地" width="520px" append-to-body>
      <el-input v-model="cityKeyword" placeholder="搜索城市" clearable class="city-search" />
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()

const hotDest = ['北京', '上海', '杭州', '广州', '桂林', '厦门']
const themes = ['自然风景', '历史古迹', '城市观光', '主题乐园']
const hotSpotTags = ['西湖景区', '故宫博物院', '外滩']

const cityDialogVisible = ref(false)
const cityKeyword = ref('')

const activeTab = ref('recommend')
const activeDest = ref('')
const activeThemes = ref([])
const activeSpotName = ref('')
const keyword = ref('')
const appliedKeyword = ref('')

const banners = [
  'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1600&q=80',
  'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1600&q=80',
  'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1600&q=80'
]
const defaultImg = 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80'

const allSpots = ref([])

const fetchSpots = async () => {
  try {
    const params = { page: 1, page_size: 100 }
    if (appliedKeyword.value) params.keyword = appliedKeyword.value
    const res = await api.get('/api/v1/spot/list', { params })
    allSpots.value = res.data?.items || res.data?.list || []
  } catch (e) {
    allSpots.value = []
  }
}

onMounted(fetchSpots)

// 全部城市（从景点接口数据去重），供“查看全部地区”弹窗使用
const cityOptions = computed(() => {
  const set = new Set()
  allSpots.value.forEach((s) => {
    if (s.city) set.add(s.city)
  })
  return Array.from(set)
})

const filteredCities = computed(() => {
  const list = [...cityOptions.value].sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'))
  const kw = cityKeyword.value.trim().toLowerCase()
  if (!kw) return list
  return list.filter((c) => String(c).toLowerCase().includes(kw))
})

const openCityDialog = () => {
  cityKeyword.value = ''
  cityDialogVisible.value = true
}

const pickCity = (city) => {
  setDest(city)
  cityDialogVisible.value = false
}

const filteredSpots = computed(() => {
  let list = allSpots.value.slice()
  if (activeDest.value) {
    list = list.filter((s) => s.city === activeDest.value || s.city?.includes(activeDest.value))
  }
  if (activeThemes.value.length) {
    list = list.filter((s) =>
      activeThemes.value.some(
        (theme) =>
          s.theme === theme ||
          (s.tags || '').includes(theme) ||
          s.description?.includes(theme)
      )
    )
  }
  if (activeSpotName.value) {
    list = list.filter((s) => (s.name || '').includes(activeSpotName.value))
  }
  if (appliedKeyword.value) {
    const kw = appliedKeyword.value.toLowerCase()
    list = list.filter(
      (s) =>
        (s.name || '').toLowerCase().includes(kw) || (s.city || '').toLowerCase().includes(kw)
    )
  }
  return list
})

const displayList = computed(() => filteredSpots.value.slice(0, 8))
const rankList = computed(() => filteredSpots.value.slice(0, 6))
const allGridList = computed(() => filteredSpots.value)

const setDest = (item) => {
  activeDest.value = activeDest.value === item ? '' : item
}
const toggleTheme = (item) => {
  const idx = activeThemes.value.indexOf(item)
  if (idx >= 0) activeThemes.value.splice(idx, 1)
  else activeThemes.value.push(item)
}
const setHotTag = (item) => {
  activeSpotName.value = activeSpotName.value === item ? '' : item
}
const handleRecommend = () => {
  activeTab.value = 'recommend'
  fetchSpots()
}
const handleSearch = () => {
  appliedKeyword.value = keyword.value.trim()
  fetchSpots()
}
const resetFilters = () => {
  keyword.value = ''
  appliedKeyword.value = ''
  activeDest.value = ''
  activeThemes.value = []
  activeSpotName.value = ''
  fetchSpots()
}

const goDetail = (id) => {
  router.push(`/spot-detail/${id}`)
}
</script>

<style scoped>
.home-fliggy {
  width: 100%;
}
.home-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.main-content {
  flex: 1;
  min-width: 0;
}
.banner {
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}
.filter-section {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 16px;
}
.filter-section-head {
  margin-bottom: 8px;
}
.filter-section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px dashed #f0f0f0;
}
.filter-row:first-of-type {
  border-top: none;
}
.filter-row-label {
  width: 84px;
  flex-shrink: 0;
  color: #606266;
  font-weight: 600;
  font-size: 14px;
  line-height: 24px;
}
.filter-row-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.filter-tag {
  cursor: pointer;
  border-radius: 4px;
}
.filter-section-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
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
}
.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.spot-section {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  padding: 16px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.section-hint {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
  margin-left: 10px;
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 6px;
}
.tab-item {
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
  transition: all 0.2s;
}
.tab-item:hover {
  color: #409eff;
}
.tab-item.active {
  background: #409eff;
  color: #fff;
  font-weight: 600;
}
.search-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.search-form {
  margin-bottom: 4px;
}
.full-grid {
  width: 100%;
}
.empty-full {
  grid-column: 1 / -1;
  width: 100%;
}
.province-tabs {
  display: flex;
  gap: 8px;
}
.province-tag {
  cursor: pointer;
}
.spot-body {
  display: flex;
  gap: 16px;
}
.rank-panel {
  width: 260px;
  flex-shrink: 0;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}
.rank-header {
  background: linear-gradient(90deg, #f7f9ff 0%, #fff 100%);
  padding: 10px 12px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
}
.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #f7f7f7;
}
.rank-item:last-child {
  border-bottom: none;
}
.rank-num {
  width: 20px;
  text-align: center;
  color: #909399;
  font-weight: 600;
}
.rank-num.top {
  color: #f56c6c;
}
.rank-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.rank-name {
  cursor: pointer;
  color: #303133;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-name:hover {
  color: #409eff;
}
.rank-price {
  color: #f56c6c;
  font-weight: 600;
  font-size: 13px;
}
.spot-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.spot-card {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
}
.spot-card :deep(.el-card__body) {
  padding: 0;
}
.spot-img-wrap {
  width: 100%;
  height: 120px;
  overflow: hidden;
}
.spot-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.spot-info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.spot-name {
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spot-city {
  color: #909399;
  font-size: 13px;
}
.spot-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.spot-score {
  color: #67c23a;
  font-size: 13px;
}
.spot-price {
  color: #f56c6c;
  font-weight: 600;
}
@media (max-width: 1200px) {
  .spot-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 992px) {
  .home-layout {
    flex-direction: column;
  }
  .spot-body {
    flex-direction: column;
  }
  .rank-panel {
    width: 100%;
  }
}
</style>
