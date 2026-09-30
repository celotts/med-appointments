import axios, { AxiosInstance } from 'axios';
import { getAccessToken } from './tokenStorage';

/**
 * Cliente HTTP sin interceptores de sesion.
 *
 * ## Por que la baseURL es RELATIVA
 *
 * Con una URL absoluta (`http://localhost:5435`) el navegador hace la peticion
 * DIRECTO al backend, saltandose el proxy de Vite, y el preflight CORS falla:
 *
 *   Access to XMLHttpRequest at 'http://localhost:5435/api/v1/login/...'
 *   from origin 'http://localhost:5174' has been blocked by CORS policy
 *
 * `/api/v1` es relativa: todo sale por el proxy de Vite (`vite.config.ts`),
 * que es un mismo origen y por tanto no necesita CORS. Es lo que ya hace
 * `axiosInstance.ts`, y los dos clientes deben coincidir.
 *
 * ## Por que no lleva interceptor de 401
 *
 * `axiosInstance` ya renueva el token y cierra la sesion cuando recibe un 401.
 * Ponerlo aqui tambien crearia dos reintentos por peticion y dos renovaciones
 * (que ademas se invalidan entre si: el servidor rota el refresh token).
 *
 * Solo se usa para login, refresh y logout, donde un 401 significa
 * "credenciales malas" y no hay nada que renovar.
 */

const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {},
});

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // `URLSearchParams` (el login) necesita form-urlencoded; `FormData`
    // necesita que el navegador ponga el boundary del multipart, asi que
    // aqui no se toca su Content-Type.
    if (config.data instanceof URLSearchParams) {
      config.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else if (
      !(config.data instanceof FormData) &&
      !config.headers['Content-Type'] &&
      config.data &&
      typeof config.data === 'object'
    ) {
      config.headers['Content-Type'] = 'application/json';
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
