import api from './api';
import { clearTokens, getRefreshToken, setTokens } from './tokenStorage';

/**
 * Cliente de autenticacion.
 *
 * ## Por que el refresh no va por axiosInstance
 *
 * `axiosInstance` renueva el token cuando recibe un 401. Usar el mismo cliente
 * para renovar crearia un bucle: la peticion de refresh fallaria con 401,
 * dispararia otro refresh, y otra vez. Este modulo usa `api`, que no tiene
 * interceptores.
 */

export interface LoginCredentials {
  email: string;
  password: string;
}

/** Lo que devuelve `/api/v1/login/*`. */
export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  /** Segundos de validez del access token. */
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  /**
   * Rol del usuario. `/api/v1/me` lo devuelve como objeto `{name}`, mientras
   * `/api/v1/users/{id}/permissions` lo devuelve como string. Acepta ambos:
   * normalizalo con `normalizeRole` de src/auth/roles.ts.
   */
  role: string | { name: string };
}

/**
 * Inicia sesion.
 *
 * Se guarda el par entero: el access token va en cada peticion y el refresh
 * solo se usa cuando caduca. Antes `LoginResponse` declaraba `refresh_token`
 * que el backend nunca devolvia, asi que era un campo de mentira.
 */
export async function login(credentials: LoginCredentials): Promise<Tokens> {
  const formData = new URLSearchParams();
  formData.set('username', credentials.email);
  formData.set('password', credentials.password);

  const response = await api.post('/login/access-token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  const tokens = response.data as Tokens;
  if (tokens.access_token) {
    setTokens(tokens.access_token, tokens.refresh_token);
  }
  return tokens;
}

/**
 * Renueva el access token.
 *
 * El servidor rota el refresh token en cada llamada, asi que se guarda el par
 * nuevo: usar dos veces el mismo refresh daria 401.
 */
export async function refreshSession(): Promise<Tokens> {
  const refresh_token = getRefreshToken();
  if (!refresh_token) {
    throw new Error('No hay refresh token: la sesion no se puede renovar.');
  }

  const response = await api.post('/login/refresh', { refresh_token });
  const tokens = response.data as Tokens;
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

/**
 * Cierra sesion EN EL SERVIDOR.
 *
 * Antes esto solo borraba el localStorage y el token seguia sirviendo hasta
 * 25 horas despues. Ahora revoca el refresh token: la sesion queda muerta.
 *
 * Los errores se ignoran a proposito: si el servidor no responde, el usuario
 * debe salir igual. El token local se borra siempre.
 */
export async function logout(): Promise<void> {
  const refresh_token = getRefreshToken();
  try {
    if (refresh_token) {
      await api.post('/login/logout', { refresh_token });
    }
  } catch {
    // Sin red, o con el servidor caido: se cierra en el cliente igual.
  } finally {
    clearTokens();
  }
}

/** Cierra TODAS las sesiones del usuario (robo de token, equipo compartido). */
export async function logoutAll(): Promise<void> {
  try {
    await api.post('/login/logout-all');
  } finally {
    clearTokens();
  }
}

/** Sesiones activas del usuario, para la pantalla de seguridad. */
export interface Sesion {
  id: string;
  creada: string;
  expira: string;
  origen: string;
  ip: string | null;
}

export async function getSesiones(): Promise<Sesion[]> {
  const response = await api.get('/login/sesiones');
  return response.data as Sesion[];
}

/** Perfil del usuario actual. */
export async function getMe(): Promise<User> {
  const response = await api.get('/me');
  return response.data as User;
}

export { getAccessToken, getRefreshToken, isAuthenticated } from './tokenStorage';

/** Objeto de compatibilidad para importaciones antiguas. */
export const authApi = {
  login,
  logout,
  logoutAll,
  refreshSession,
  getSesiones,
  getMe,
};
