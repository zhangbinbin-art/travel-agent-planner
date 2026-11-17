<template>
  <div ref="containerRef" class="route-leaflet"></div>
</template>

<script setup>
/**
 * 路线地图（Leaflet）：不依赖高德 JS SDK / Key。
 * - 瓦片默认走高德栅格瓦片（无需 Key），可通过 VITE_MAP_TILE_URL 替换为天地图/OSM；
 * - 路线直接使用后端返回的 lng/lat 画折线，不需要驾车 API；
 * - 景点橙色编号点、酒店蓝色点，点击弹窗展示名称。
 */
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  spots: { type: Array, default: () => [] },
  hotels: { type: Array, default: () => [] }
})

const containerRef = ref(null)
let map = null
let layerGroup = null
let observer = null

// 默认高德栅格瓦片（无需 Key）；有天地图/OSM 可直接改环境变量
const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ||
  'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'
const TILE_SUBDOMAINS = (import.meta.env.VITE_MAP_TILE_SUBDOMAINS || '1,2,3,4').split(',')
const TILE_ATTR = import.meta.env.VITE_MAP_TILE_ATTR || '© 高德地图'

const spotIcon = (badge, isStart) =>
  L.divIcon({
    className: 'route-marker',
    html: `<span class="route-marker-pin spot">${isStart ? '起' : badge}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 26]
  })

const hotelIcon = () =>
  L.divIcon({
    className: 'route-marker',
    html: '<span class="route-marker-pin hotel">宿</span>',
    iconSize: [26, 26],
    iconAnchor: [13, 26]
  })

const render = () => {
  if (!map) return
  if (layerGroup) {
    layerGroup.clearLayers()
  } else {
    layerGroup = L.layerGroup().addTo(map)
  }

  const points = (props.spots || []).filter((p) => Number.isFinite(p.lng) && Number.isFinite(p.lat))
  const hotels = (props.hotels || []).filter((p) => Number.isFinite(p.lng) && Number.isFinite(p.lat))

  // 路线折线（按景点顺序）
  if (points.length > 1) {
    L.polyline(
      points.map((p) => [p.lat, p.lng]),
      { color: '#ff7a45', weight: 4, opacity: 0.85 }
    ).addTo(layerGroup)
  }

  points.forEach((p) => {
    L.marker([p.lat, p.lng], { icon: spotIcon(p.badge, p.isStart) })
      .bindPopup(`<b>${p.isStart ? '起点 · ' : `第${p.badge}站 · `}${p.name}</b>`)
      .addTo(layerGroup)
  })

  hotels.forEach((h) => {
    L.marker([h.lat, h.lng], { icon: hotelIcon() })
      .bindPopup(`<b>酒店 · ${h.name}</b>`)
      .addTo(layerGroup)
  })

  const all = [...points, ...hotels]
  if (all.length) {
    map.fitBounds(all.map((p) => [p.lat, p.lng]), { padding: [30, 30], maxZoom: 14 })
  }
}

const init = () => {
  if (!containerRef.value || map) return
  map = L.map(containerRef.value, {
    zoomControl: true,
    attributionControl: true,
    scrollWheelZoom: true
  }).setView([23.13, 113.26], 11)

  L.tileLayer(TILE_URL, {
    subdomains: TILE_SUBDOMAINS,
    attribution: TILE_ATTR,
    maxZoom: 18
  }).addTo(map)

  render()

  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => {
      if (map) map.invalidateSize()
    })
    observer.observe(containerRef.value)
  }
}

onMounted(async () => {
  await nextTick()
  init()
})

watch(
  () => [props.spots, props.hotels],
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style scoped>
.route-leaflet {
  width: 100%;
  height: 360px;
  border-radius: 10px;
  border: 1px solid #f3e6dc;
  overflow: hidden;
  background: #f8fafc;
}

:deep(.route-marker-pin) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50% 50% 50% 4px;
  transform: rotate(-45deg);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
}

:deep(.route-marker-pin > *) {
  transform: rotate(45deg);
}

:deep(.route-marker-pin.spot) {
  background: #ff7a45;
}

:deep(.route-marker-pin.hotel) {
  background: #2f9cff;
}
</style>
