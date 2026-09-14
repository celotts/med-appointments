import axios from 'axios';

// Usar valor por defecto directamente en lugar de import.meta.env
// para evitar errores de TypeScript con import.meta.env en este proyecto
const API_BASE_URL = 'http://localhost:5435';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor: Agrega el token a CADA petición automáticamente
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor: Maneja errores 401 (token expirado) y renueva automáticamente
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado - intentar renovar con refresh_token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        return axios.post('http://localhost:5435/api/v1/login/refresh-token', {
          refresh_token: refreshToken,
        }).then((res) => {
          // Guardar nuevos tokens en localStorage
          localStorage.setItem('access_token', res.data.access_token);
          localStorage.setItem('refresh_token', res.data.refresh_token);

          // Reconfigurar header con nuevo token para el reintento
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`;

          // Reintentar la petición original
          return api(error.config);
        })
        .catch((renewError) => {
          // Si no se puede renovar, cerrar sesión
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          return Promise.reject(renewError);
        });
      }
    }
    return Promise.reject(error);
  }
);

export default api;