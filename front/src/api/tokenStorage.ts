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

/**
 * Margen de seguridad, en segundos.
 *
 * Un token que expira en 3 segundos pasa la comprobacion del navegador y
 * llega al servidor justo cuando caduca, que responde 401. Anticiparse evita
 * ese viaje perdido.
 */
const MARGEN_SEGUNDOS = 30;

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

/**
 * Payload de un JWT, o `null` si no se puede leer.
 *
 * NO valida la firma: eso es trabajo del servidor y no se puede hacer en el
 * navegador sin exponer la clave. Aqui solo se lee `exp` para saber cuando
 * caduca, y el backend sigue validando en cada peticion.
 */
export function payloadDe(token: string | null): Record<string, unknown> | null {
  if (!token) return null;
  try {
    const parte = token.split('.')[1];
    if (!parte) return null;
    const base64 = parte.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Segundos hasta que caduca el token, con margen. Negativo = ya caducado. */
export function segundosParaCaducar(token: string | null = getAccessToken()): number {
  const payload = payloadDe(token);
  if (!payload || typeof payload.exp !== 'number') return -1;
  return payload.exp - Math.floor(Date.now() / 1000) - MARGEN_SEGUNDOS;
}

/**
 * El token esta caducado o a punto de estarlo.
 *
 * Un token ilegible (sin `exp`, corrupto, de otro formato) se considera
 * caducado: en caso de duda se cierra la sesion, que es el fallo seguro. Lo
 * contrario — dar por bueno un token que no se puede comprobar — dejaria al
 * usuario en una pagina que ya no le sirve de nada.
 */
export function isTokenExpired(token: string | null = getAccessToken()): boolean {
  return segundosParaCaducar(token) <= 0;
}

/** Hay sesion con un token vigente. */
export function isAuthenticated(): boolean {
  return !isTokenExpired();
}
