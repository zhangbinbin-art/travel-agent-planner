import api from './index'

// 地点名称 -> 经纬度（后端转发高德 Web 服务地理编码）
export function geoCode(locationName, city) {
  return api.post('/api/v1/map/geo-code', { location_name: locationName, city })
}
