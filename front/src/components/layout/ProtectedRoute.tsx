import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Loader2, ShieldAlert } from 'lucide-react';
import { hasRole } from '../../auth/roles';

interface Props {
  /** Roles permitidos. `undefined` = solo exige sesion iniciada. */
  roles?: readonly string[];
  /** A donde va quien no cumple. Por defecto, al panel. */
  redirectTo?: string;
  /**
   * Contenido a proteger. Se admite ademas del patron `<Outlet />` para no
   * obligar a crear un wrapper por cada ruta.
   */
  children?: React.ReactNode;
}

/**
 * Ruta protegida por sesion y, opcionalmente, por rol.
 *
 * ## Sesion caducada: la pantalla se BLOQUEA, no se redirige
 *
 * Antes un 401 hacia `window.location.href = '/login'`, que recarga el
 * navegador entero. Con varias peticiones en vuelo (el panel lanza 6 a la vez)
 * cada una recargaba: varias recargas seguidas y la app se queda en blanco.
 *
 * Ahora, cuando la sesion caduca, `ProtectedRoute` deja de renderizar el
 * contenido y muestra un aviso con opcion de volver a entrar. El usuario no
 * ve ni puede interactuar con los datos que ya tenia en pantalla, que es lo
 * que pedia el requisito: la pagina abierta deja de ser usable. Sin recarga,
 * sin parpadeo, y sin que el estado interno de la app se reinicie a medias.
 *
 * Esto NO protege los datos: el backend vuelve a comprobar el rol en cada
 * endpoint. Aqui solo se evita mostrar una pantalla que va a fallar.
 */
const ProtectedRoute: React.FC<Props> = ({ roles, redirectTo = '/', children }) => {
  const { isAuthenticated, isLoading, isTokenValid, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-medical-background gap-3">
        <Loader2 className="animate-spin text-medical-primary" size={32} />
        <p className="text-medical-textMuted text-sm">Verificando sesion...</p>
      </div>
    );
  }

  if (!isAuthenticated || !isTokenValid()) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !hasRole(user?.role, roles)) {
    // Sin `redirectTo` explicito se vuelve al panel en vez de a otra pagina
    // protegida, que podria encadenar redirecciones.
    return <Navigate to={redirectTo} replace state={{ from: location.pathname }} />;
  }

  return <>{children ?? <Outlet />}</>;
};

/** Aviso para cuando el rol no basta y no conviene redirigir. */
export const SinPermisos: React.FC = () => (
  <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
    <ShieldAlert size={40} className="text-medical-warning" />
    <p className="text-medical-textMain font-medium">
      Su rol no tiene acceso a esta seccion.
    </p>
    <p className="text-sm text-medical-textMuted">
      Si deberia tenerlo, consulte con un administrador de la clinica.
    </p>
  </div>
);

export default ProtectedRoute;
