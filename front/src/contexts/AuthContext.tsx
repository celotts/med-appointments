import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { clearTokens, getAccessToken } from '../api/tokenStorage';

export interface User {
  id: string;
  email: string;
  full_name: string;
  // Nombre del rol tal como lo guarda la BD: SUPER_ADMIN, ADMIN, DOCTOR,
  // SPECIALIST, ASSISTANT o PATIENT. Usar `hasRole()` de core/rbac.py para
  // decidir permisos, nunca comparar strings a mano.
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
  isLoading: boolean;
  isTokenValid: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function parseJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;
  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Al recargar se rehidrata desde `access_token` (clave que usa axiosInstance)
  // y el perfil cacheado. Antes se leia `auth_token`, que solo escribia el
  // login: tras un refresh de pagina el estado de sesion quedaba inconsistente.
  useEffect(() => {
    const token = getAccessToken();
    const userData = localStorage.getItem('user_data');
    if (token && userData) {
      if (isTokenExpired(token)) {
        clearTokens();
        localStorage.removeItem('user_data');
      } else {
        setUser(JSON.parse(userData));
        setIsAuthenticated(true);
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = setInterval(() => {
      const token = getAccessToken();
      if (!token || isTokenExpired(token)) {
        logout();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const login = (token: string, userData: User) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_data', JSON.stringify(userData));
    setUser(userData);
    setIsAuthenticated(true);
  };

  const logout = useCallback(() => {
    clearTokens();
    localStorage.removeItem('user_data');
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/login';
  }, []);

  const isTokenValid = useCallback(() => {
    const token = getAccessToken();
    if (!token) return false;
    return !isTokenExpired(token);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout, isLoading, isTokenValid }}>
      {!isLoading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
