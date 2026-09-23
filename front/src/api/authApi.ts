import api from './api'

export interface LoginCredentials {
  email: string
  password: string
}

export interface Tokens {
  access_token: string
  refresh_token: string
}

export interface User {
  id: string
  email: string
  full_name: string
  role: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

// Login: Obtiene tokens y los guarda en localStorage
export async function login(credentials: LoginCredentials): Promise<Tokens> {
  const formData = new URLSearchParams()
  formData.set('username', credentials.email)
  formData.set('password', credentials.password)

  const response = await api.post('/api/v1/login/access-token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  // Guardar tokens en localStorage para persistencia
  if (response.data.access_token) {
    localStorage.setItem('access_token', response.data.access_token)
  }
  if (response.data.refresh_token) {
    localStorage.setItem('refresh_token', response.data.refresh_token)
  }

  return response.data as Tokens
}

// Logout: Limpia todos los tokens de localStorage
export function logout(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

// Obtener token actual de acceso
export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

// Obtener token de refresco actual
export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

// Verificar si el usuario está autenticado
export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token')
}

// Obtener datos del usuario actual
export async function getMe(): Promise<User> {
  const response = await api.get('/api/v1/me')
  return response.data as User
}

// Objeto de compatibilidad para importaciones antiguas
export const authApi = {
  login,
  logout,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  getMe,
}
