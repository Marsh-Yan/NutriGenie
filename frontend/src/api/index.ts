import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const value = item as { msg?: unknown; loc?: unknown }
          const location = Array.isArray(value.loc) ? value.loc.filter(Boolean).join(' → ') : ''
          return location && value.msg ? `${location}: ${String(value.msg)}` : String(value.msg || '请求参数有误')
        }
        return String(item)
      })
      .join('；')
  }
  if (detail && typeof detail === 'object') {
    const value = detail as { msg?: unknown; message?: unknown }
    return String(value.msg || value.message || '请求参数有误')
  }
  return ''
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('nutrigenie_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一错误处理
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const msg = formatApiErrorDetail(error.response?.data?.detail) || error.message || '网络错误'
    const apiError = new Error(msg) as Error & { status?: number }
    apiError.status = error.response?.status
    if (apiError.status !== 404) console.error('[API]', msg)
    return Promise.reject(apiError)
  },
)

export default api
