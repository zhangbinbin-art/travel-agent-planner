import api from './index'

export function addFavorite(spot_id) {
  return api.post('/api/v1/favorite', null, { params: { spot_id } })
}

export function removeFavorite(spot_id) {
  return api.delete('/api/v1/favorite', { params: { spot_id } })
}

export function getMyFavorites(params) {
  return api.get('/api/v1/favorite/my', { params })
}

export function toggleFavorite(spot_id) {
  return api.post(`/api/v1/favorite/spot/${spot_id}/favorite`)
}

export function getMyFavoriteSpots() {
  return api.get('/api/v1/favorite/my-favorite-spots')
}
