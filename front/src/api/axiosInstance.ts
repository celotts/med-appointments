import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  setTokens,
} from './tokenStorage';
import { expire } from './sessionManager';

/**
 * Cliente HTTP de la aplicacion.
 *
 * ## Tres barreras contra el uso de la app con la sesion cerrada
 *
 * 1. **Antes de enviar.** Si el token ya caduco, la peticion no sale: se
 *    comprueba el `exp` en local, sin gastar red y con aviso instantaneo.
 * 2. **Un 401 inesperado.** El token puede seguir vigente en el reloj del
 *    navegador y haberse revocado en la base. Se intenta renovar con el refresh
 *    token y se reintenta la peticion original.
 * 3. **Si el refresh tambien falla.** La sesion esta muerta: se limpian los
 *    tokens y se avisa una sola vez. `expire()` es idempotente, de modo que
 *    varias peticiones que fallen juntas producen un solo aviso.
 */

const axiosInstance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

/** Cliente sin interceptores, para la propia peticion de refresh. */
const apiPeligro = axios.create({ baseURL: '/api/v1' });

/** Marca las peticiones que ya se renovaron, para no entrar en bucle. */
type PeticionMarcada = InternalAxiosRequestConfig & { _renovada?: boolean };

/**
 * Renovacion compartida por todas las peticiones que la esperan.
 *
 * Sin esto, con el panel cargando 6 endpoints a la vez y el token caducado,
 * salen 6 renovaciones. El servidor ROTA el refresh token en cada llamada: las
 * 5 restantes llegarian con un token ya revocado, fallarian y cerrarian una
 * sesion que si se podia renovar. Una sola promesa compartida lo evita.
 */
let renovacionEnCurso: Promise<string> | null = null;

function renovarAccessToken(): Promise<string> {
  if (renovacionEnCurso) return renovacionEnCurso;

  const refresh_token = getRefreshToken();
  if (!refresh_token) {
    return Promise.reject(new Error('No hay refresh token'));
  }

  renovacionEnCurso = apiPeligro
    .post('/login/refresh', { refresh_token })
    .then(({ data }) => {
      setTokens(data.access_token, data.refresh_token);
      return data.access_token as string;
    })
    .finally(() => {
      // Se libera siempre: si se dejara cacheada, tras un fallo jamas volveria
      // a intentarse y la app se quedaria sin poder renovar.
      renovacionEnCurso = null;
    });

  return renovacionEnCurso;
}

axiosInstance.interceptors.request.use((config: PeticionMarcada) => {
  if (isTokenExpired()) {
    expire('expirado');
    return Promise.reject(new Error('Sesion expirada: la peticion no se ha enviado.'));
  }
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const peticion = error.config as PeticionMarcada | undefined;
    const status = error.response?.status;

    if (status !== 401 || !peticion) {
      return Promise.reject(error);
    }

    // Un 401 en /login/ es "credenciales malas" o "refresh invalido": no hay
    // nada que renovar, y reintentar entraria en bucle.
    if (peticion.url?.includes('/login/')) {
      clearTokens();
      expire('revocado');
      return Promise.reject(error);
    }

    // Ya se intento renovar y no funciono: la sesion esta muerta.
    if (peticion._renovada) {
      clearTokens();
      expire('revocado');
      return Promise.reject(error);
    }

    try {
      const token = await renovarAccessToken();
      peticion._renovada = true;
      peticion.headers.Authorization = `Bearer ${token}`;
      return axiosInstance(peticion);
    } catch {
      clearTokens();
      expire('revocado');
      return Promise.reject(error);
    }
  }
);

export default axiosInstance;
