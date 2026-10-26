import axios from 'axios'
import router from '@/router'
import { clearAuth, loadAuth } from '@/utils/auth'

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 10000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    loadAuth()
    return response
  },
  (error) => {
    if (error?.response?.status === 401) {
      clearAuth()
      const current = router.currentRoute.value
      if (current.path !== '/login') {
        router.push({ path: '/login', query: { redirect: current.fullPath } })
      }
    }
    return Promise.reject(error)
  }
)

export default api
