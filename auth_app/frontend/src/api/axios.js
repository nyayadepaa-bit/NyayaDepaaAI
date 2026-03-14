import axios from 'axios'

const ENV_API_BASE = import.meta.env.VITE_API_BASE_URL
const DEFAULT_API_BASE = window.location.hostname === 'localhost'
    ? '/api'
    : 'https://nyayadepaaai-api.onrender.com/api'

const API_BASE = (ENV_API_BASE || DEFAULT_API_BASE).replace(/\/$/, '')

const api = axios.create({ baseURL: API_BASE })

// Attach JWT to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

// On 401, try refresh once, then force logout
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
    failedQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
    failedQueue = []
}

api.interceptors.response.use(
    (res) => res,
    async (error) => {
        const original = error.config
        if (error.response?.status === 401 && !original._retry) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                }).then((token) => {
                    original.headers.Authorization = `Bearer ${token}`
                    return api(original)
                })
            }
            original._retry = true
            isRefreshing = true
            try {
                const refresh = localStorage.getItem('refresh_token')
                if (!refresh) throw new Error('No refresh token')
                const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh })
                localStorage.setItem('access_token', data.access_token)
                localStorage.setItem('refresh_token', data.refresh_token)
                processQueue(null, data.access_token)
                original.headers.Authorization = `Bearer ${data.access_token}`
                return api(original)
            } catch (err) {
                processQueue(err, null)
                localStorage.clear()
                window.location.href = '/admin/login'
                return Promise.reject(err)
            } finally {
                isRefreshing = false
            }
        }
        return Promise.reject(error)
    },
)

export default api
