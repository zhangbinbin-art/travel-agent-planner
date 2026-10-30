import api from '@/api'

// 商家后台接口（需 merchant + approved）
export const getDashboard = () => api.get('/api/v1/merchant/dashboard')
export const getMyHotels = () => api.get('/api/v1/merchant/hotel')
export const createHotel = (data) => api.post('/api/v1/merchant/hotel', data)
export const updateHotel = (id, data) => api.put(`/api/v1/merchant/hotel/${id}`, data)
export const updateHotelStatus = (id, status) =>
  api.put(`/api/v1/merchant/hotel/${id}/status`, { status })
export const deleteHotel = (id) => api.delete(`/api/v1/merchant/hotel/${id}`)
export const getMerchantBookings = (params) => api.get('/api/v1/merchant/booking', { params })
export const updateBookingStatus = (id, status) =>
  api.put(`/api/v1/merchant/booking/${id}/status`, { status })

// 游客侧接口
export const getOnShelfHotels = () => api.get('/api/v1/hotel/list')
export const createHotelBooking = (data) => api.post('/api/v1/hotel/booking', data)
export const getMyBookings = () => api.get('/api/v1/hotel/my-booking')

// 管理员商家审核
export const getMerchantList = (params) => api.get('/api/v1/admin/merchant', { params })
export const auditMerchant = (uid, auditStatus) =>
  api.put(`/api/v1/admin/merchant/${uid}/audit`, { audit_status: auditStatus })

// 管理员平台总览
export const getAdminHotels = () => api.get('/api/v1/admin/hotel')
export const getAdminBookings = (params) => api.get('/api/v1/admin/booking', { params })
