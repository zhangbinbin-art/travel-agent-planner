export const HOTEL_TYPES = ['连锁酒店', '商务酒店', '民宿', '电竞酒店', '其他酒店']

export const FEATURE_TAGS = [
  '免费停车',
  '早餐',
  '健身房',
  '洗衣服务',
  '江景房',
  '茶室',
  '露台',
  '接送',
  '会议室',
  '电竞',
  '烧烤'
]

export function inferHotelType(name) {
  const n = name || ''
  if (n.includes('民宿')) return '民宿'
  if (n.includes('电竞')) return '电竞酒店'
  if (n.includes('星期八')) return '连锁酒店'
  if (n.includes('西瓜')) return '商务酒店'
  return '其他酒店'
}

export function parseFacilities(hotel) {
  const raw = hotel?.facilities
  if (!raw) return []
  return String(raw)
    .split(/[,，;；]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

export function matchFeatures(hotel, features) {
  if (!features || !features.length) return true
  const list = parseFacilities(hotel)
  return features.every((f) => list.some((item) => item.includes(f)))
}
