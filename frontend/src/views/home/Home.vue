<template>
  <div class="home">
    <!-- ========== 主视觉 Banner ========== -->
    <section class="hero">
      <el-carousel
        ref="bannerRef"
        class="hero-carousel"
        height="60vh"
        :interval="5200"
        indicator-position="none"
        arrow="hover"
        @change="onBannerChange"
      >
        <el-carousel-item v-for="item in bannerSpots" :key="item.key">
          <div class="hero-slide" @click="goDetail(item.id)">
            <img class="hero-img" :src="item.cover" :alt="item.name || '风景'" @error="onImgError" />
            <div class="hero-mask"></div>
            <div class="hero-info">
              <span class="hero-city">{{ item.city || '精选目的地' }}</span>
              <h1 class="hero-name">{{ item.name }}</h1>
              <div class="hero-meta">
                <span class="tr-score">{{ item.scoreText }} 分</span>
                <span v-if="item.price" class="hero-price">¥{{ item.price }} 起</span>
              </div>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>

      <div class="hero-dots">
        <button
          v-for="(dot, idx) in bannerSpots"
          :key="dot.key"
          type="button"
          class="hero-dot"
          :class="{ 'is-active': idx === bannerIndex }"
          :aria-label="'切换到第 ' + (idx + 1) + ' 张'"
          @click.stop="switchBanner(idx)"
        ></button>
      </div>
    </section>

    <!-- ========== 猜你喜欢 ========== -->
    <section class="section">
      <header class="section-head">
        <div class="section-heading">
          <span class="tr-section-sub">Recommended</span>
          <h2 class="tr-section-title">猜你喜欢</h2>
        </div>
        <el-button round class="more-btn" @click="router.push('/spot')">查看全部景点</el-button>
      </header>

      <div v-if="recommendSpots.length" class="spot-grid">
        <article
          v-for="spot in recommendSpots"
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
      <EmptyState v-else description="暂无推荐景点" hint="稍后再来看看吧" />
    </section>

    <!-- ========== 最新攻略 ========== -->
    <section class="section">
      <header class="section-head">
        <div class="section-heading">
          <span class="tr-section-sub">New Travel Notes</span>
          <h2 class="tr-section-title">最新攻略</h2>
        </div>
        <el-button round class="more-btn" @click="router.push('/strategy')">查看全部攻略</el-button>
      </header>

      <div v-if="latestPosts.length" class="post-grid">
        <article
          v-for="post in latestPosts"
          :key="post.id"
          class="post-card"
          @click="router.push(`/post-detail/${post.id}`)"
        >
          <div class="post-cover">
            <img :src="post.cover || defaultImg" :alt="post.title" loading="lazy" @error="onImgError" />
          </div>
          <div class="post-body">
            <h3 class="post-title">{{ post.title }}</h3>
            <p class="post-excerpt">{{ excerpt(post.content) }}</p>
            <div class="post-meta">
              <span class="post-author">
                <span class="author-dot"></span>
                {{ post.author?.username || '匿名用户' }}
              </span>
              <span class="post-date">{{ formatDate(post.created_at) }}</span>
            </div>
            <div class="post-stats">
              <span>点赞 {{ Number(post.like_count) || 0 }}</span>
              <span>收藏 {{ Number(post.favorite_count) || 0 }}</span>
            </div>
          </div>
        </article>
      </div>
      <EmptyState v-else description="暂无攻略" hint="登录后可查看最新游记" />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { getPostList } from '@/api/post'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()

const defaultImg =
  'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80'

const bannerRef = ref(null)
const bannerIndex = ref(0)
const hotSpots = ref([])
const allSpots = ref([])
const latestPosts = ref([])

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

const excerpt = (content) => {
  const text = String(content || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!text) return '作者还没有填写简介'
  return text.length > 56 ? `${text.slice(0, 56)}…` : text
}

const formatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// Banner：单独拉一批景点，按评分降序取前 5，作为首页主视觉（不复用下方卡片列表）
const fetchBanners = async () => {
  try {
    const res = await api.get('/api/v1/spot/list', { params: { page: 1, page_size: 30 } })
    const items = res.data?.items || []
    const sorted = items
      .slice()
      .sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0))
    const scenic = sorted.filter(
      (spot) => spot.cover && !/学院|大学|学校/.test(String(spot.name || ''))
    )
    hotSpots.value = (scenic.length >= 3 ? scenic : sorted)
      .slice(0, 5)
      .map((spot) => ({
        ...spot,
        key: `banner-${spot.id}`,
        scoreText: scoreText(spot.score),
        cover: spot.cover || defaultImg
      }))
  } catch (e) {
    hotSpots.value = []
  }
}

// 猜你喜欢：高分优先的个性化推荐，排除 Banner 已展示的景点
const fetchRecommend = async () => {
  try {
    const res = await api.get('/api/v1/spot/list', { params: { page: 1, page_size: 50 } })
    const items = res.data?.items || []
    allSpots.value = items
  } catch (e) {
    allSpots.value = []
  }
}

const fetchLatestPosts = async () => {
  try {
    const res = await getPostList({ page: 1, page_size: 6, sort: 'latest' })
    latestPosts.value = res.data?.items || []
  } catch (e) {
    latestPosts.value = []
  }
}

const bannerSpots = computed(() => hotSpots.value)

const recommendSpots = computed(() => {
  const bannerIds = new Set(bannerSpots.value.map((s) => s.id))
  const sorted = allSpots.value
    .slice()
    .sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0))
  const pool = sorted.filter((s) => !bannerIds.has(s.id))
  return (pool.length >= 4 ? pool : sorted).slice(0, 8)
})

const onBannerChange = (index) => {
  bannerIndex.value = index
}

const switchBanner = (index) => {
  bannerRef.value?.setActiveItem(index)
}

const goDetail = (id) => {
  if (!id) return
  router.push(`/spot-detail/${id}`)
}

onMounted(() => {
  fetchBanners()
  fetchRecommend()
  fetchLatestPosts()
})
</script>

<style scoped>
.home {
  max-width: 1320px;
  margin: 0 auto;
  padding-bottom: 24px;
}

/* ================= Banner ================= */
.hero {
  position: relative;
  margin-bottom: 28px;
}

.hero-carousel {
  border: 2px solid #222;
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 5px 5px 0 rgba(34, 34, 34, 0.12);
  background: #dceeff;
}

.hero-slide {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0) 35%,
    rgba(0, 0, 0, 0.18) 60%,
    rgba(0, 0, 0, 0.62) 100%
  );
}

.hero-info {
  position: absolute;
  left: 32px;
  bottom: 34px;
  max-width: 60%;
  color: #fff;
}

.hero-city {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #222;
  font-size: 12px;
  font-weight: 700;
}

.hero-name {
  margin: 12px 0 10px;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0.6px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hero-price {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.5);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.hero-dots {
  position: absolute;
  right: 30px;
  bottom: 24px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hero-dot {
  width: 9px;
  height: 9px;
  padding: 0;
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 999px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.hero-dot.is-active {
  width: 24px;
  background: #ff7a2f;
  border-color: #fff;
}

/* ================= 区块标题 ================= */
.section {
  margin-bottom: 34px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-heading .tr-section-title {
  margin: 0;
}

.more-btn {
  height: 34px;
  padding: 0 16px;
  font-weight: 700;
  color: #2b6cb0;
  border: 2px solid #2b6cb0;
  background: #eaf4ff;
}

.more-btn:hover {
  background: #d8ebff;
  border-color: #2b6cb0;
  color: #2b6cb0;
}

/* ================= 景点卡片 ================= */
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
  overflow: hidden;
  border-bottom: 2px solid #222;
  background: #f2f8ff;
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
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  font-size: 12.5px;
  line-height: 1.6;
  color: #6b7785;
  min-height: 40px;
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

/* ================= 攻略卡片 ================= */
.post-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

.post-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 2px solid #222;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 3px 3px 0 rgba(34, 34, 34, 0.1);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.post-card:hover {
  transform: translateY(-4px);
  box-shadow: 5px 7px 0 rgba(34, 34, 34, 0.16);
}

.post-cover {
  height: 172px;
  border-bottom: 2px solid #222;
  background: #f2f8ff;
  overflow: hidden;
}

.post-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.post-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px 16px;
}

.post-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #222;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-excerpt {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #6b7785;
  min-height: 40px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #7b8794;
}

.post-author {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #3d4753;
}

.author-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff7a2f;
  border: 1px solid #222;
}

.post-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #7b8794;
}

@media (max-width: 900px) {
  .hero-name {
    font-size: 24px;
  }
  .hero-info {
    left: 18px;
    bottom: 52px;
    max-width: 78%;
  }
  .hero-dots {
    right: 16px;
    bottom: 16px;
  }
  .section-head {
    align-items: center;
  }
}
</style>
