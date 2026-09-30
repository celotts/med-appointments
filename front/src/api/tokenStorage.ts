/**
 * Almacenamiento de tokens: fuente unica de verdad.
 *
 * Antes cada modulo usaba su propia clave: AuthContext escribia `auth_token`,
 * mientras axiosInstance, api.ts y authApi leian `access_token`. Funcionaba
 * solo porque el login escribia las dos por accidente; `logout()` ademas
 * olvidaba borrar `access_token`, dejando un token vivo en localStorage
 * despues de cerrar sesion.
 *
 * Regla: nadie mas debe llamar a localStorage para tokens. Usar este modulo.
 */

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string | null): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

/** Borra TODOS los tokens. Usar siempre en logout y en respuesta 401. */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}