<template>
  <div class="hotel-picker">
    <HotelFilter v-model="filters" :disabled="disabled" />

    <el-select
      :model-value="modelValue"
      :placeholder="selectPlaceholder"
      clearable
      :disabled="disabled"
      :filterable="!generatedMode"
      :remote="!generatedMode"
      :remote-method="remoteSearch"
      :loading="searching"
      class="hotel-select"
      @update:model-value="onSelect"
    >
      <el-option-group v-if="allowCustom && !generatedMode" label="自定义">
        <el-option label="自定义食宿单价" value="" />
      </el-option-group>
      <el-option-group :label="generatedMode ? '行程配套酒店' : '平台酒店'" :disabled="disabled">
        <el-option
          v-for="h in visibleHotels"
          :key="h.id"
          :value="h.id"
          :label="h.name + '｜¥' + formatMoney(h.price_per_day) + '/天'"
        >
          <div class="hotel-option">
            <span class="ho-name">{{ h.name }}</span>
            <span class="ho-price">¥{{ formatMoney(h.price_per_day) }}/天</span>
            <span class="ho-score">
              环境 {{ h.env_score || '-' }} · 服务 {{ h.service_score || '-' }}
            </span>
            <el-button link type="primary" size="small" @click.stop="openDetail(h)">详情</el-button>
          </div>
        </el-option>
      </el-option-group>
    </el-select>

    <div v-if="generatedMode" class="mode-tip">{{ modeHint }}</div>
    <div v-if="!visibleHotels.length" class="empty-tip">{{ emptyText }}</div>

    <HotelDetailDialog v-model="dialogVisible" :hotel="detailHotel" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getOnShelfHotels } from '@/api/hotel'
import { inferHotelType, matchFeatures } from '@/utils/hotel'
import HotelFilter from './HotelFilter.vue'
import HotelDetailDialog from './HotelDetailDialog.vue'

const props = defineProps({
  modelValue: { type: [Number, String], default: '' },
  // 目标城市（plan 智能规划）：填写后才请求该城市酒店
  city: { type: String, default: '' },
  // 是否要求先填写城市（为 true 时城市为空则整体禁用）
  requireCity: { type: Boolean, default: false },
  // undefined = 不限制城市（单独预订）；数组 = 城市白名单（兼容旧用法）
  cityList: { type: Array, default: undefined },
  allowCustom: { type: Boolean, default: true },
  // 父组件递增该值可重置筛选条件（用于“重置”按钮）
  resetSignal: { type: Number, default: 0 },
  // 父组件一次性下发筛选条件（用于 keep-alive/sessionStorage 回退恢复）
  filterSeed: { type: Object, default: null },
  // 是否已生成路线：true 时只用本次行程返回的 hotel_markers，禁止自由搜索
  generated: { type: Boolean, default: false },
  // 后端 route.hotel_markers：[{ id, name, price, cover, description, address }]
  hotelMarkers: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue', 'change', 'filters-change'])

const hotels = ref([])
const dialogVisible = ref(false)
const detailHotel = ref(null)
const defaultFilters = () => ({
  types: [],
  price: [0, 2000],
  minEnv: 0,
  minService: 0,
  features: []
})
// 注意：必须用 ref；用 reactive + v-model 会在赋值时替换对象，导致筛选控件失效
const filters = ref(defaultFilters())

const disabled = computed(() => {
  if (props.requireCity) return !props.city
  if (props.cityList !== undefined) return !props.cityList.length
  return false
})

const searching = ref(false)
const searchKeyword = ref('')

// 已生成路线：把后端 hotel_markers 映射成下拉选项（价格字段名对齐平台酒店）
const markerHotels = computed(() =>
  (props.hotelMarkers || []).map((h) => ({
    id: h.id,
    name: h.name,
    price_per_day: h.price,
    cover_img: h.cover,
    description: h.description,
    address: h.address,
    _fromMarker: true
  }))
)

// 生成态下只按「类型 + 价格」过滤（marker 没有环境/服务分）
const generatedHotels = computed(() => {
  const f = filters.value
  const [minP, maxP] = f.price || [0, 2000]
  return markerHotels.value.filter((h) => {
    if (f.types?.length && !f.types.includes(inferHotelType(h.name))) return false
    const price = Number(h.price_per_day) || 0
    if (minP > 0 && price < minP) return false
    if (maxP < 2000 && price > maxP) return false
    return true
  })
})

// 已生成路线且接口确实返回了配套酒店时才锁定；若该目的地没有配套酒店，
// 退回“可搜索平台酒店”，否则用户永远选不到酒店、提交预约按钮一直是灰的
const generatedMode = computed(() => props.generated && markerHotels.value.length > 0)

const visibleHotels = computed(() => (generatedMode.value ? generatedHotels.value : hotels.value))

const selectPlaceholder = computed(() =>
  generatedMode.value ? '选择本次行程配套酒店' : '可输入酒店名称搜索酒店'
)

const modeHint = computed(() =>
  generatedMode.value
    ? '当前行程配套周边酒店，不可搜索其他酒店'
    : '可输入酒店名称搜索酒店'
)

const emptyText = computed(() => {
  if (disabled.value) return '请先填写目标地区，再筛选酒店'
  if (!hotels.value.length) return '当前城市无匹配酒店，请调整筛选条件'
  return ''
})

const formatMoney = (val) => {
  const num = Number(val)
  return Number.isNaN(num) ? '0.00' : num.toFixed(2)
}

// 仅按城市请求（目标城市隔离），其余筛选在前端二次过滤
const buildParams = () => {
  const params = {}
  if (props.city) {
    params.city = props.city
  } else if (props.cityList !== undefined) {
    params.city_list = (props.cityList || []).join(',')
  }
  return params
}

const applyFilters = (list) => {
  const f = filters.value
  const [minP, maxP] = f.price || [0, 2000]
  return list.filter((h) => {
    if (f.types?.length && !f.types.includes(inferHotelType(h.name))) return false
    const price = Number(h.price_per_day) || 0
    if (minP > 0 && price < minP) return false
    if (maxP < 2000 && price > maxP) return false
    if (f.minEnv > 0 && (Number(h.env_score) || 0) < f.minEnv) return false
    if (f.minService > 0 && (Number(h.service_score) || 0) < f.minService) return false
    if (!matchFeatures(h, f.features)) return false
    return true
  })
}

const sourcePool = ref([])

const clearSelectionIfInvalid = () => {
  if (props.modelValue === '' || props.modelValue === null || props.modelValue === undefined) return
  if (!hotels.value.some((h) => h.id === props.modelValue)) {
    emit('update:modelValue', '')
    emit('change', null)
  }
}

const fetchHotels = async () => {
  // 生成态且有配套酒店：选项完全来自行程返回的 hotel_markers，不请求酒店接口
  if (generatedMode.value) {
    hotels.value = []
    sourcePool.value = []
    return
  }
  if (disabled.value) {
    hotels.value = []
    sourcePool.value = []
    clearSelectionIfInvalid()
    return
  }
  try {
    const res = await getOnShelfHotels(buildParams())
    sourcePool.value = res.data?.items || []
    hotels.value = applyFilters(sourcePool.value)
    clearSelectionIfInvalid()
  } catch (e) {
    sourcePool.value = []
    hotels.value = []
    clearSelectionIfInvalid()
    ElMessage.error(e?.response?.data?.detail || '获取酒店列表失败')
  }
}

// 未生成路线时的远程搜索：按名称过滤（后端 list 无 keyword 参数，前端过滤）
const remoteSearch = async (keyword) => {
  if (generatedMode.value) return
  searchKeyword.value = keyword || ''
  searching.value = true
  try {
    const res = await getOnShelfHotels({})
    const pool = res.data?.items || []
    sourcePool.value = pool
    const kw = searchKeyword.value.trim().toLowerCase()
    const base = kw ? pool.filter((h) => String(h.name || '').toLowerCase().includes(kw)) : pool
    hotels.value = applyFilters(base)
  } catch (e) {
    sourcePool.value = []
    hotels.value = []
  } finally {
    searching.value = false
  }
}

const onSelect = (val) => {
  emit('update:modelValue', val)
  const hotel = visibleHotels.value.find((h) => h.id === val) || null
  emit('change', hotel)
}

const openDetail = (hotel) => {
  detailHotel.value = hotel
  dialogVisible.value = true
}

// 生成态切换：进入生成态校验已选酒店是否在配套列表内，退出生成态重新拉取
watch(
  [() => props.generated, () => props.hotelMarkers.length],
  () => {
    if (generatedMode.value) {
      const ids = markerHotels.value.map((h) => h.id)
      if (props.modelValue !== '' && !ids.includes(props.modelValue)) {
        emit('update:modelValue', '')
        emit('change', null)
      }
    } else {
      fetchHotels()
    }
  }
)
watch(() => props.city, () => fetchHotels())
watch(() => props.cityList, () => fetchHotels(), { deep: true })
watch(
  () => props.resetSignal,
  () => {
    filters.value = defaultFilters()
    emit('filters-change', defaultFilters())
    emit('update:modelValue', '')
    emit('change', null)
  }
)
watch(
  () => props.filterSeed,
  (seed) => {
    if (!seed) return
    filters.value = {
      types: [...(seed.types || [])],
      price: [...(seed.price || [0, 2000])],
      minEnv: seed.minEnv || 0,
      minService: seed.minService || 0,
      features: [...(seed.features || [])]
    }
  }
)
// 城市酒店池不变，筛选条件变化只做前端二次过滤
watch(
  filters,
  () => {
    emit('filters-change', JSON.parse(JSON.stringify(filters.value)))
    hotels.value = applyFilters(sourcePool.value)
    // 已选酒店被筛掉时清空选择
    if (props.modelValue !== '' && !hotels.value.some((h) => h.id === props.modelValue)) {
      emit('update:modelValue', '')
      emit('change', null)
    }
  },
  { deep: true }
)
onMounted(fetchHotels)
</script>

<style scoped>
.hotel-picker {
  width: 100%;
}
.hotel-select {
  width: 100%;
}
.hotel-option {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ho-name {
  font-weight: 500;
}
.ho-price {
  color: #f56c6c;
  font-size: 13px;
}
.ho-score {
  color: #909399;
  font-size: 12px;
}
.empty-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
.mode-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #7b8794;
}
</style>
