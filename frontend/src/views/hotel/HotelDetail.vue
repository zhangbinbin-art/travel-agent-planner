<template>
  <div class="hotel-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ hotel?.name || '酒店详情' }}</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>

      <el-empty v-if="!loading && !hotel" description="酒店不存在或已下架" />

      <div v-else-if="hotel" class="detail-body">
        <img
          v-if="hotel.cover_img"
          :src="hotel.cover_img"
          class="cover"
          alt="酒店封面"
        />
        <div class="info-row">
          <span class="label">地址</span>
          <span>{{ hotel.address || '暂无' }}</span>
        </div>
        <div class="info-row">
          <span class="label">单价</span>
          <span class="price">¥{{ formatMoney(hotel.price_per_day) }}/天</span>
        </div>
        <div class="info-row">
          <span class="label">评分</span>
          <span>环境 {{ hotel.env_score || '-' }} ｜ 服务 {{ hotel.service_score || '-' }}</span>
        </div>
        <div class="info-row">
          <span class="label">联系电话</span>
          <span>{{ hotel.phone || '暂无' }}</span>
        </div>
        <div class="info-row">
          <span class="label">简介</span>
          <span>{{ hotel.description || '暂无简介' }}</span>
        </div>
        <div class="info-row">
          <span class="label">入住规则</span>
          <span>{{ hotel.checkin_rule || '入住 14:00 后，退房 12:00 前' }}</span>
        </div>
        <div v-if="album.length" class="album">
          <div class="album-title">酒店相册</div>
          <div class="album-grid">
            <el-image
              v-for="(url, idx) in album"
              :key="idx"
              :src="url"
              :preview-src-list="album"
              :initial-index="idx"
              fit="cover"
              class="album-item"
            />
          </div>
        </div>
        <div class="booking-bar">
          <el-button type="primary" size="large" class="booking-btn" @click="openBooking">
            预定酒店
          </el-button>
        </div>
        <div class="info-row">
          <span class="label">配套设施</span>
          <span>
            <el-tag v-for="f in facilities" :key="f" size="small" class="facility-tag">{{ f }}</el-tag>
            <span v-if="!facilities.length">暂无</span>
          </span>
        </div>
      </div>
    </el-card>

    <!-- 预定酒店弹窗：提交后创建订单并跳转支付页 -->
    <el-dialog v-model="bookingVisible" title="预定酒店" width="440px">
      <el-form label-width="90px">
        <el-form-item label="入住日期">
          <el-date-picker v-model="checkIn" type="date" value-format="YYYY-MM-DD" placeholder="选择入住日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="离店日期">
          <el-date-picker v-model="checkOut" type="date" value-format="YYYY-MM-DD" placeholder="选择离店日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="入住人数">
          <el-input-number v-model="guestCount" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="预计费用">
          <span class="booking-estimate">¥{{ estimateTotal }}</span>
          <span class="booking-note">（{{ nights }} 晚 × ¥{{ formatMoney(hotel?.price_per_day) }}）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bookingVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitBooking">确认预定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createHotelOrder, getOnShelfHotels } from '@/api/hotel'
import { parseFacilities } from '@/utils/hotel'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const hotel = ref(null)
const loading = ref(false)

const facilities = computed(() => parseFacilities(hotel.value))

// 商家提交并审核通过的相册（hotels.imgs 存 JSON 数组字符串）
const album = computed(() => {
  const raw = hotel.value?.imgs
  if (!raw) return []
  try {
    const list = JSON.parse(raw)
    return Array.isArray(list) ? list.filter(Boolean) : []
  } catch (e) {
    return []
  }
})

const formatMoney = (val) => {
  const num = Number(val)
  return Number.isNaN(num) ? '0.00' : num.toFixed(2)
}

const fetchHotel = async () => {
  const id = Number(route.params.id)
  if (!Number.isFinite(id) || id <= 0) {
    console.warn('[HotelDetail] 无效的酒店 id，跳过加载:', route.params.id)
    return
  }
  loading.value = true
  try {
    const res = await getOnShelfHotels()
    const list = res.data?.items || []
    hotel.value = list.find((h) => Number(h.id) === id) || null
    if (!hotel.value) {
      console.warn('[HotelDetail] 未找到酒店 id:', id)
    }
  } catch (e) {
    console.warn('[HotelDetail] 获取酒店信息失败:', e?.message)
  } finally {
    loading.value = false
  }
}

// ===== 预定酒店 =====
const bookingVisible = ref(false)
const submitting = ref(false)
const checkIn = ref('')
const checkOut = ref('')
const guestCount = ref(1)

const nights = computed(() => {
  if (!checkIn.value || !checkOut.value) return 0
  const a = new Date(checkIn.value).getTime()
  const b = new Date(checkOut.value).getTime()
  if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return 0
  return Math.round((b - a) / 86400000)
})

const estimateTotal = computed(() => {
  const price = Number(hotel.value?.price_per_day || 0)
  return (nights.value > 0 ? nights.value * price : price).toFixed(2)
})

const openBooking = () => {
  if (!auth.token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  bookingVisible.value = true
}

const submitBooking = async () => {
  if (!hotel.value?.id) return
  if (!checkIn.value || !checkOut.value) {
    ElMessage.warning('请选择入住和离店日期')
    return
  }
  if (nights.value <= 0) {
    ElMessage.warning('离店日期必须晚于入住日期')
    return
  }
  submitting.value = true
  try {
    const res = await createHotelOrder({
      hotel_id: hotel.value.id,
      check_in: checkIn.value,
      check_out: checkOut.value,
      people_count: guestCount.value
    })
    const orderId = res.data?.id
    ElMessage.success('预定成功，请完成支付')
    bookingVisible.value = false
    if (orderId) router.push(`/pay/${orderId}`)
  } catch (e) {
    const detail = e?.response?.data?.detail || '预定失败，请稍后重试'
    ElMessage.error(String(detail).replace('REAL_NAME_REQUIRED: ', ''))
  } finally {
    submitting.value = false
  }
}

onMounted(fetchHotel)
</script>

<style scoped>
.album {
  margin-top: 16px;
}
.album-title {
  font-size: 14px;
  font-weight: 700;
  color: #222;
  margin-bottom: 8px;
}
.album-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.album-item {
  width: 100%;
  height: 96px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(34, 34, 34, 0.12);
}

.hotel-detail-page {
  max-width: 900px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
}
.cover {
  width: 100%;
  max-height: 320px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 16px;
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.info-row {
  display: flex;
  gap: 12px;
  color: #606266;
  line-height: 1.7;
}
.label {
  width: 80px;
  flex-shrink: 0;
  color: #909399;
}
.price {
  color: #f56c6c;
  font-weight: 600;
}
.facility-tag {
  margin: 0 6px 6px 0;
}

.booking-bar {
  display: flex;
  justify-content: flex-end;
  padding: 4px 0 8px;
}
.booking-btn {
  background: #ff7a45;
  border-color: #ff7a45;
  border-radius: 10px;
}
.booking-estimate {
  color: #f56c6c;
  font-weight: 600;
  font-size: 16px;
}
.booking-note {
  margin-left: 8px;
  color: #9aa3b2;
  font-size: 12px;
}

</style>
