import api from './index'

export const generateTrip = (data) => api.post('/api/v1/trip/generate', data)
export const saveTrip = (data) => api.post('/api/v1/trip/save', data)
export const getMyTrips = (params) => api.get('/api/v1/trip/my', { params })
export const getTripDetail = (id) => api.get(`/api/v1/trip/${id}`)
export const deleteTrip = (id) => api.delete(`/api/v1/trip/${id}`)
