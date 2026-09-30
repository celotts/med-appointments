import api from './api'
import { clearTokens, getAccessToken, getRefreshToken, isAuthenticated, setTokens } from './tokenStorage'

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
  /**
   * Rol del usuario. `/api/v1/me` lo devuelve como objeto `{name}`, mientras
   * `/api/v1/users/{id}/permissions` lo devuelve como string. Acepta ambos:
   * normalizalo con `normalizeRole` de src/auth/roles.ts.
   */
  role: string | { name: string }
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

  // Guardar tokens via tokenStorage (fuente unica de verdad)
  if (response.data.access_token) {
    setTokens(response.data.access_token, response.data.refresh_token)
  }

  return response.data as Tokens
}

// Reexportados desde tokenStorage para mantener la API publica existente.
export { getAccessToken, getRefreshToken, isAuthenticated }

// Logout: Limpia todos los tokens de localStorage
export function logout(): void {
  clearTokens()
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
