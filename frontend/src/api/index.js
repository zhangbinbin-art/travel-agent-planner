import axios from 'axios'
import router from '@/router'
import { clearAuth, loadAuth } from '@/utils/auth'

// 局域网访问时用当前域名/IP，避免硬编码 127.0.0.1 导致手机连不上后端
const getBaseURL = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    return `http://${hostname}:8000`
  }
  return 'http://localhost:8000'
}

const api = axios.create({
  baseURL: getBaseURL(),
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
