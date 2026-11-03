<template>
  <div class="spot-page">
    <section class="filter-card">
      <div class="filter-head">
        <div class="filter-heading">
          <span class="tr-section-sub">Explore</span>
          <h1 class="tr-section-title">旅游景点</h1>
        </div>
        <div class="filter-search">
          <el-input
            v-model="keyword"
            placeholder="搜索景点名称 / 城市"
            clearable
            @keyup.enter="applyKeyword"
            @clear="applyKeyword"
          />
          <el-button type="primary" @click="applyKeyword">搜索</el-button>
        </div>
      </div>

      <div class="filter-row">
        <span class="filter-label">热门目的地</span>
        <div class="chip-wrap">
          <button
            v-for="city in cityOptions"
            :key="city"
            type="button"
            class="chip"
            :class="{ 'is-active': activeCity === city }"
            @click="toggleCity(city)"
          >
            {{ city }}
          </button>
        </div>
      </div>

      <div class="filter-row">
        <span class="filter-label">旅游主题</span>
        <div class="chip-wrap">
          <button
            v-for="theme in themeOptions"
            :key="theme"
            type="button"
            class="chip"
            :class="{ 'is-active': activeThemes.includes(theme) }"
            @click="toggleTheme(theme)"
          >
            {{ theme }}
          </button>
        </div>
      </div>

      <div class="filter-foot">
        <span class="filter-count">共 {{ filteredSpots.length }} 个景点</span>
        <el-button v-if="hasFilter" text @click="resetAll">清空筛选</el-button>
      </div>
    </section>

    <section class="list-wrap">
      <div v-if="pagedSpots.length" class="spot-grid">
        <article
          v-for="spot in pagedSpots"
          :key="spot.id"
          class="spot-card"
          @click="goDetail(spot.id)"
        >
          <div class="spot-cover">
            <img :src="spot.cover || defaultImg" :alt="spot.name" loading="lazy" @error="onImgError" />
          </div>
          <div class="spot-body">
            <span class="tr-pill spot-city">{{ spot.city || '热门目的地' }}</span>
            <h3 class="spot-name">{{ spot.name }}</h3>
            <p class="spot-desc">{{ spotDesc(spot) }}</p>
            <div class="spot-foot">
              <span class="tr-score">{{ scoreText(spot.score) }} 分</span>
              <span class="spot-price">¥{{ Number(spot.price) || 0 }} 起</span>
            </div>
          </div>
        </article>
      </div>
      <EmptyState v-else description="没有找到符合条件的景点" hint="试试更换城市或主题" />

      <div v-if="filteredSpots.length > pageSize" class="pager">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="filteredSpots.length"
          :page-size="pageSize"
          :current-page="page"
          @current-change="handlePageChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getSpotList } from '@/api/spot'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()

const defaultImg =
  'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80'

const spots = ref([])
const loading = ref(false)
const keyword = ref('')
const appliedKeyword = ref('')
const activeCity = ref('')
const activeThemes = ref([])
const page = ref(1)
const pageSize = 12

const themeOptions = ['自然风景', '历史古迹', '城市观光', '主题乐园', '美食探店', '徒步登山']

const cityOptions = computed(() => {
  const set = new Set()
  spots.value.forEach((spot) => {
    const city = String(spot.city || '').trim()
    if (city) set.add(city)
  })
  return Array.from(set).slice(0, 8)
})

// 图片加载失败时回退到默认图，避免出现浏览器破图
const onImgError = (event) => {
  const img = event?.target
  if (!img || img.dataset.fallbackApplied) return
  img.dataset.fallbackApplied = '1'
  img.src = defaultImg
}

const scoreText = (score) => {
  const num = Number(score)
  return Number.isFinite(num) && num > 0 ? num.toFixed(1) : '4.8'
}

const spotDesc = (spot) => {
  const text = String(spot?.description || '').replace(/\s+/g, ' ').trim()
  if (!text) return `${spot?.province || ''}${spot?.city || ''}热门景点`.trim() || '值得一去的热门景点'
  return text.length > 42 ? `${text.slice(0, 42)}…` : text
}

const filteredSpots = computed(() => {
  const kw = appliedKeyword.value.trim().toLowerCase()
  return spots.value.filter((spot) => {
    if (kw) {
      const name = String(spot.name || '').toLowerCase()
      const city = String(spot.city || '').toLowerCase()
      if (!name.includes(kw) && !city.includes(kw)) return false
    }
    if (activeCity.value && String(spot.city || '') !== activeCity.value) return false
    if (activeThemes.value.length) {
      const haystack = `${spot.theme || ''} ${spot.tags || ''} ${spot.description || ''}`
      if (!activeThemes.value.some((theme) => haystack.includes(theme))) return false
    }
    return true
  })
})

const pagedSpots = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredSpots.value.slice(start, start + pageSize)
})

const hasFilter = computed(
  () => !!appliedKeyword.value || !!activeCity.value || activeThemes.value.length > 0
)

const fetchSpots = async () => {
  loading.value = true
  try {
    const res = await getSpotList({ page: 1, page_size: 100 })
    spots.value = res.data?.items || []
  } catch (e) {
    spots.value = []
  } finally {
    loading.value = false
  }
}

const applyKeyword = () => {
  appliedKeyword.value = keyword.value.trim()
  page.value = 1
}

const toggleCity = (city) => {
  activeCity.value = activeCity.value === city ? '' : city
  page.value = 1
}

const toggleTheme = (theme) => {
  const idx = activeThemes.value.indexOf(theme)
  if (idx >= 0) activeThemes.value.splice(idx, 1)
  else activeThemes.value.push(theme)
  page.value = 1
}

const handlePageChange = (val) => {
  page.value = val
}

const resetAll = () => {
  keyword.value = ''
  appliedKeyword.value = ''
  activeCity.value = ''
  activeThemes.value = []
  page.value = 1
}

const goDetail = (id) => {
  if (!id) return
  router.push(`/spot-detail/${id}`)
}

onMounted(fetchSpots)
</script>

<style scoped>
.spot-page {
  max-width: 1320px;
  margin: 0 auto;
  padding-bottom: 24px;
}

.filter-card {
  margin-bottom: 22px;
  padding: 20px 22px 16px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 18px;
  box-shadow: 4px 4px 0 rgba(34, 34, 34, 0.1);
}

.filter-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.filter-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-heading .tr-section-title {
  margin: 0;
}

.filter-search {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-search :deep(.el-input) {
  width: 240px;
}

.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 8px 0;
  border-top: 1px dashed rgba(34, 34, 34, 0.12);
}

.filter-label {
  flex-shrink: 0;
  width: 84px;
  padding-top: 5px;
  font-size: 13px;
  font-weight: 700;
  color: #5a6472;
}

.chip-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 5px 14px;
  border: 2px solid rgba(34, 34, 34, 0.14);
  border-radius: 999px;
  background: #fff;
  color: #3d4753;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.chip:hover {
  background: #eef6ff;
  border-color: #222;
}

.chip.is-active {
  background: #fff1e6;
  border-color: #222;
  color: #f06818;
}

.filter-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px dashed rgba(34, 34, 34, 0.12);
  font-size: 13px;
  color: #7b8794;
}

.spot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 18px;
}

.spot-card {
  background: #fff;
  border: 2px solid #222;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 3px 3px 0 rgba(34, 34, 34, 0.1);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.spot-card:hover {
  transform: translateY(-4px);
  box-shadow: 5px 7px 0 rgba(34, 34, 34, 0.16);
}

.spot-cover {
  height: 158px;
  border-bottom: 2px solid #222;
  background: #f2f8ff;
  overflow: hidden;
}

.spot-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.25s ease;
}

.spot-card:hover .spot-cover img {
  transform: scale(1.04);
}

.spot-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px 14px;
}

.spot-city {
  align-self: flex-start;
}

.spot-name {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #222;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spot-desc {
  margin: 0;
  min-height: 40px;
  font-size: 12.5px;
  line-height: 1.6;
  color: #6b7785;
}

.spot-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.spot-price {
  font-size: 13px;
  font-weight: 700;
  color: #ff7a2f;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 22px;
}
</style>
