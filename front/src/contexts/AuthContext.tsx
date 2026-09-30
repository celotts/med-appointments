import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
} from '../api/tokenStorage';
import { revivir, suscribir } from '../api/sessionManager';

export interface User {
  id: string;
  email: string;
  full_name: string;
  // Nombre del rol tal como lo guarda la BD: SUPER_ADMIN, ADMIN, DOCTOR,
  // SPECIALIST, ASSISTANT o PATIENT. Usar `hasRole()` de auth/roles.ts para
  // decidir permisos, nunca comparar strings a mano.
  role: string;
}

/** Por que se cerro la sesion. La pantalla de login lo muestra. */
export type MotivoCierre = 'expirado' | 'revocado' | 'invalido' | null;

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
  isLoading: boolean;
  isTokenValid: () => boolean;
  /** Non-null cuando la sesion se cerro sola. */
  motivoCierre: MotivoCierre;
  /** Limpia el motivo una vez la pantalla de login lo ha mostrado. */
  limpiarMotivo: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const MOTIVOS: Record<string, string> = {
  expirado:
    'Su sesion expiro por seguridad. Vuelva a iniciar sesion para continuar.',
  revocado:
    'Su sesion dejo de ser valida. Esto ocurre si su cuenta fue desactivada o si el token fue revocado.',
  invalido:
    'No pudimos verificar su sesion. Vuelva a iniciar sesion.',
};

export const mensajeDeCierre = (motivo: MotivoCierre): string | null =>
  motivo ? MOTIVOS[motivo] ?? MOTIVOS.invalido : null;

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [motivoCierre, setMotivoCierre] = useState<MotivoCierre>(null);
  const expiracionProgramada = useRef<number | null>(null);

  /** Cierra sesion en memoria sin navegar: el enrutador decide el destino. */
  const cerrarEnMemoria = useCallback((motivo: MotivoCierre) => {
    clearTokens();
    localStorage.removeItem('user_data');
    setUser(null);
    setIsAuthenticated(false);
    setMotivoCierre(motivo);
  }, []);

  // Al recargar se rehidrata desde `access_token` (la clave que usa
  // axiosInstance) y el perfil cacheado. Antes se leia `auth_token`, que solo
  // escribia el login: tras un refresh el estado de sesion quedaba
  // inconsistente.
  useEffect(() => {
    const token = getAccessToken();
    const userData = localStorage.getItem('user_data');
    if (token && userData) {
      if (isTokenExpired(token)) {
        cerrarEnMemoria('expirado');
      } else {
        try {
          setUser(JSON.parse(userData));
          setIsAuthenticated(true);
        } catch {
          // `user_data` corrupto: se descarta en vez de romper el arranque.
          cerrarEnMemoria('invalido');
        }
      }
    }
    setIsLoading(false);
  }, [cerrarEnMemoria]);

  /**
   * Vigilancia por reloj, no por sondeo ciego.
   *
   * Antes un `setInterval` de 30 s comprobaba el token para siempre. Eso
   * despierta la app cada 30 segundos aunque no pase nada, y aun asi puede
   * dejar pasar hasta 30 s con la sesion caducada.
   *
   * Ahora se calcula el `exp` del token una vez y se programa un unico
   * temporizador para ese instante exacto. Se despierta una vez, en el
   * momento justo. Ademas se re-comprueba en cada `visibilitychange`, porque un
   * token puede caducar mientras la pestana esta en segundo plano y los
   * temporizadores no siempre se disparan en suspensiones largas.
   */
  useEffect(() => {
    if (!isAuthenticated) return;

    const programar = () => {
      if (expiracionProgramada.current !== null) {
        window.clearTimeout(expiracionProgramada.current);
      }
      const token = getAccessToken();
      if (!token) {
        cerrarEnMemoria('expirado');
        return;
      }
      const payload = (() => {
        try {
          return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        } catch {
          return null;
        }
      })();
      const exp = payload?.exp;
      if (typeof exp !== 'number') {
        cerrarEnMemoria('invalido');
        return;
      }
      const ms = exp * 1000 - Date.now() + 500;
      if (ms <= 0) {
        cerrarEnMemoria('expirado');
        return;
      }
      expiracionProgramada.current = window.setTimeout(() => {
        cerrarEnMemoria('expirado');
      }, ms);
    };

    programar();

    // Al volver a la pestana: el token puede haber caducado en segundo plano.
    const alVolver = () => {
      if (document.visibilityState === 'visible' && isAuthenticated) {
        programar();
      }
    };
    document.addEventListener('visibilitychange', alVolver);

    // El reloj se salta hacia adelante al suspender un equipo: al volver,
    // `setTimeout` puede no haber saltado. Un intervalo largo lo cubre.
    const intervalo = window.setInterval(programar, 60_000);

    return () => {
      document.removeEventListener('visibilitychange', alVolver);
      window.clearInterval(intervalo);
      if (expiracionProgramada.current !== null) {
        window.clearTimeout(expiracionProgramada.current);
        expiracionProgramada.current = null;
      }
    };
  }, [isAuthenticated, cerrarEnMemoria]);

  /** Recibe el aviso del sessionManager (interceptor de axios). */
  useEffect(() => {
    return suscribir((motivo) => cerrarEnMemoria(motivo));
  }, [cerrarEnMemoria]);

  const login = useCallback((token: string, userData: User) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_data', JSON.stringify(userData));
    revivir();
    setUser(userData);
    setIsAuthenticated(true);
    setMotivoCierre(null);
  }, []);

  /**
   * Cierra sesion en el SERVIDOR, no solo en el navegador.
   *
   * Antes `logout()` borraba el localStorage y nada mas: el token seguido
   * sirviendo en el backend hasta 25 horas despues. Ahora revoca el refresh
   * token, de modo que la sesion queda muerta aunque alguien hubiera copiado
   * el token.
   *
   * El estado local se limpia siempre, pase lo que pase con la red: si el
   * servidor no responde, el usuario debe salir igual.
   */
  const logout = useCallback(() => {
    const token = getRefreshToken();
    if (token) {
      // Fire-and-forget: el estado local no espera al servidor.
      fetch('/api/v1/login/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token }),
        keepalive: true,
      }).catch(() => {
        // Sin red: se cierra en el cliente igualmente.
      });
    }
    cerrarEnMemoria(null);
  }, [cerrarEnMemoria]);

  const isTokenValid = useCallback(() => !isTokenExpired(), []);

  const limpiarMotivo = useCallback(() => setMotivoCierre(null), []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        login,
        logout,
        isLoading,
        isTokenValid,
        motivoCierre,
        limpiarMotivo,
      }}
    >
      {!isLoading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
