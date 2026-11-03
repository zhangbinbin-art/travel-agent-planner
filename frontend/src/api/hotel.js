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
export const getOnShelfHotels = (params) => api.get('/api/v1/hotel/list', { params })
export const createHotelBooking = (data) => api.post('/api/v1/hotel/booking', data)
export const getMyBookings = () => api.get('/api/v1/hotel/my-booking')

// 管理员商家审核
export const getMerchantList = (params) => api.get('/api/v1/admin/merchant', { params })
export const auditMerchant = (uid, auditStatus) =>
  api.put(`/api/v1/admin/merchant/${uid}/audit`, { audit_status: auditStatus })

// 管理员平台总览
export const getAdminHotels = () => api.get('/api/v1/admin/hotel')
export const getAdminBookings = (params) => api.get('/api/v1/admin/booking', { params })

// v0.11 实名 / 酒店订单 / 支付
export const submitRealName = (data) => api.post('/api/v1/user/real-name', data)
export const getProfile = () => api.get('/api/v1/user/profile')
export const createHotelOrder = (data) => api.post('/api/v1/hotel/order', data)
export const getMyOrders = () => api.get('/api/v1/hotel/my-order')
export const getHotelOrder = (id) => api.get(`/api/v1/hotel/order/${id}`)
export const payHotelOrder = (id, payChannel) =>
  api.post(`/api/v1/hotel/order/${id}/pay`, { pay_channel: payChannel })
export const cancelHotelOrder = (id) => api.post(`/api/v1/hotel/order/${id}/cancel`)

// v0.11 商户（单酒店）
export const getMyMerchantHotel = () => api.get('/api/v1/merchant/hotel')
export const getRooms = () => api.get('/api/v1/merchant/room')
export const createRoom = (data) => api.post('/api/v1/merchant/room', data)
export const updateRoom = (id, data) => api.put(`/api/v1/merchant/room/${id}`, data)
export const updateRoomStatus = (id, status) =>
  api.put(`/api/v1/merchant/room/${id}/status`, { status })
export const deleteRoom = (id) => api.delete(`/api/v1/merchant/room/${id}`)
export const getMerchantOrders = (params) => api.get('/api/v1/merchant/order', { params })
export const updateMerchantOrderStatus = (id, status) =>
  api.put(`/api/v1/merchant/order/${id}/status`, { status })
export const getGuests = () => api.get('/api/v1/merchant/guest')
export const checkinGuest = (data) => api.post('/api/v1/merchant/guest', data)
export const getBills = () => api.get('/api/v1/merchant/bill')
export const settleBill = (orderId) => api.post(`/api/v1/merchant/bill/${orderId}/settle`)
export const getReport = () => api.get('/api/v1/merchant/report')

// v0.11 管理员酒店维护 / 订单 / 商户绑定
export const adminCreateHotel = (data) => api.post('/api/v1/admin/hotel', data)
export const adminUpdateHotel = (id, data) => api.put(`/api/v1/admin/hotel/${id}`, data)
export const adminHotelStatus = (id, status) =>
  api.put(`/api/v1/admin/hotel/${id}/status`, { status })
export const adminDeleteHotel = (id) => api.delete(`/api/v1/admin/hotel/${id}`)
export const getAdminOrders = () => api.get('/api/v1/admin/order')
export const bindMerchantHotel = (uid, hotelId) =>
  api.put(`/api/v1/admin/merchant/${uid}/bind`, { hotel_id: hotelId })
