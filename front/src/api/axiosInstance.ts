import axios, { AxiosInstance } from 'axios'
import { toast } from 'react-hot-toast'

// Axios instance con base URL /api/v1 (usado por todos los endpoints de la API)
const axiosInstance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request Interceptor: Agrega el token de acceso a CADA petición automáticamente
axiosInstance.interceptors.request.use(
  (config: any) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response Interceptor simple: Solo maneja errores 401
axiosInstance.interceptors.response.use(
  (response: any) => response,
  (error: any) => {
    if (error.response?.status === 401) {
      // Token expirado - limpiar y redirect al login
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      toast.error('Sesión expirada. Por favor, inicia sesión nuevamente.')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default axiosInstance
