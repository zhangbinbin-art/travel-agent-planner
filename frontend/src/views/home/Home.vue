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
                link
                type="primary"
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

// 检索框关键词优先：清空关键词后，顶部标签才重新参与筛选
const filteredSpots = computed(() => {
  const list = allSpots.value.slice()
  const kw = appliedKeyword.value.trim().toLowerCase()

  // ① 有检索关键词时，只按关键词过滤，顶部标签筛选不参与
  if (kw) {
    return list.filter(
      (s) =>
        (s.name || '').toLowerCase().includes(kw) || (s.city || '').toLowerCase().includes(kw)
    )
  }

  // ② 检索框为空时，才使用顶部标签组合筛选
  let result = list
  if (activeDest.value) {
    result = result.filter(
      (s) => s.city === activeDest.value || s.city?.includes(activeDest.value)
    )
  }
  if (activeThemes.value.length) {
    result = result.filter((s) =>
      activeThemes.value.some(
        (theme) =>
          s.theme === theme ||
          (s.tags || '').includes(theme) ||
          s.description?.includes(theme)
      )
    )
  }
  if (activeSpotName.value) {
    result = result.filter((s) => (s.name || '').includes(activeSpotName.value))
  }
  return result
})

const displayList = computed(() => filteredSpots.value.slice(0, 8))
const rankList = computed(() => filteredSpots.value.slice(0, 6))
const allGridList = computed(() => filteredSpots.value)

// 清空检索框（点击顶部标签时调用，保证标签筛选立即生效）
// 返回是否清掉了已生效的检索词——若清掉了，需要重新拉取未过滤的全量列表
const clearKeyword = () => {
  const hadKeyword = !!appliedKeyword.value
  keyword.value = ''
  appliedKeyword.value = ''
  return hadKeyword
}

const setDest = (item) => {
  if (clearKeyword()) fetchSpots()
  activeDest.value = activeDest.value === item ? '' : item
}
const toggleTheme = (item) => {
  if (clearKeyword()) fetchSpots()
  const idx = activeThemes.value.indexOf(item)
  if (idx >= 0) activeThemes.value.splice(idx, 1)
  else activeThemes.value.push(item)
}
const setHotTag = (item) => {
  if (clearKeyword()) fetchSpots()
  activeSpotName.value = activeSpotName.value === item ? '' : item
}
const handleSearch = () => {
  const kw = keyword.value.trim()
  appliedKeyword.value = kw
  // 检索关键词优先级最高：一旦检索，清空顶部所有标签选中状态
  if (kw) {
    activeDest.value = ''
    activeThemes.value = []
    activeSpotName.value = ''
  }
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
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
}
/* 轻量化筛选条：三组标签横向紧凑排布，放不下自动换行 */
.filter-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 18px;
  background: #fff;
  border: none;
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.03);
  margin-bottom: 10px;
}
.filter-section-head {
  margin: 0;
}
.filter-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}
.filter-row {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
  border: none;
}
/* 分组标题加重、与标签拉开视觉层级 */
.filter-row-label {
  color: #2c3e50;
  font-weight: 600;
  font-size: 14px;
  line-height: 26px;
  white-space: nowrap;
  margin-right: 2px;
  padding-right: 6px;
}
.filter-row-content {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
/* 标签统一为浅色胶囊，选中态（el-tag--dark）为蓝色实底 */
.filter-tag.el-tag {
  height: auto;
  padding: 4px 10px;
  line-height: 1.4;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.filter-tag.el-tag:not(.el-tag--dark) {
  --el-tag-bg-color: #fff;
  --el-tag-border-color: #e4e7ed;
  --el-tag-text-color: #606266;
  background-color: #fff;
  border-color: #e4e7ed;
  color: #606266;
}
.filter-tag.el-tag:not(.el-tag--dark):hover {
  --el-tag-bg-color: #fff;
  --el-tag-border-color: #409eff;
  --el-tag-text-color: #409eff;
  background-color: #fff;
  border-color: #409eff;
  color: #409eff;
}
.filter-tag.el-tag.el-tag--dark,
.filter-tag.el-tag.el-tag--dark:hover {
  --el-tag-bg-color: #409eff;
  --el-tag-border-color: #409eff;
  --el-tag-text-color: #fff;
  background-color: #409eff;
  border-color: #409eff;
  color: #fff;
}
.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.spot-section {
  background: #fff;
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  padding: 18px 20px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #2c3e50;
}
.section-hint {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
  margin-left: 10px;
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.section-actions :deep(.el-button.is-link) {
  color: #409eff;
  font-size: 14px;
  height: auto;
  padding: 4px 2px;
}
.section-actions :deep(.el-button.is-link:hover) {
  color: #409eff;
  text-decoration: underline;
}
.tab-bar {
  display: inline-flex;
  gap: 4px;
  margin: 0 0 18px;
  padding: 4px;
  background: #f7f8fa;
  border: none;
  border-radius: 10px;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: auto;
  vertical-align: top;
}
.tab-item {
  flex-shrink: 0;
  padding: 6px 18px;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  background: #fff;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  line-height: 1.4;
  transition: all 0.2s ease;
}
.tab-item:hover {
  border-color: #409eff;
  color: #409eff;
}
.tab-item.active {
  background: #409eff;
  border-color: #409eff;
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
.spot-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.rank-panel {
  width: 260px;
  flex-shrink: 0;
  border: none;
  border-radius: 12px;
  background: #f7f8fa;
  padding: 8px;
  overflow: hidden;
}
.rank-header {
  background: #eef3fb;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: 700;
  color: #2c3e50;
}
.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  transition: background 0.2s ease;
}
.rank-item:hover {
  background: #eef3fb;
}
.rank-num {
  width: 20px;
  text-align: center;
  color: #909399;
  font-size: 13px;
  font-weight: 600;
}
.rank-num.top {
  color: #f56c6c;
}
.rank-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.rank-name {
  flex: 1;
  min-width: 0;
  cursor: pointer;
  color: #2c3e50;
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
  white-space: nowrap;
}
.spot-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.spot-card.el-card {
  cursor: pointer;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.spot-card.el-card.is-hover-shadow:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.spot-card :deep(.el-card__body) {
  padding: 0;
}
.spot-img-wrap {
  width: 100%;
  height: 120px;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
  background: #f7f8fa;
}
.spot-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.spot-info {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.spot-name {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  line-height: 20px;
  min-height: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spot-city {
  color: #909399;
  font-size: 13px;
  line-height: 18px;
  min-height: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spot-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 22px;
}
.spot-score {
  color: #67c23a;
  font-size: 13px;
}
.spot-price {
  color: #f56c6c;
  font-weight: 700;
  font-size: 15px;
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
@media (max-width: 768px) {
  .spot-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .spot-grid {
    grid-template-columns: 1fr;
  }
}
</style>
