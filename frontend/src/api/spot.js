import api from './index'

export function getSpotList(params) {
  return api.get('/api/v1/spot/list', { params })
}

export function getSpotDetail(id) {
  return api.get(`/api/v1/spot/${id}`)
}

export function createSpot(data) {
  return api.post('/api/v1/spot', data)
}

export function updateSpot(id, data) {
  return api.put(`/api/v1/spot/${id}`, data)
}

export function deleteSpot(id) {
  return api.delete(`/api/v1/spot/${id}`)
}
