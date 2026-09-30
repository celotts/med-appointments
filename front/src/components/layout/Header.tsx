import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useUnsavedChanges } from '../../contexts/UnsavedChangesContext';
import { LogOut, User, AlertTriangle, Menu } from 'lucide-react';
import NotificationBell from '../common/NotificationBell';
import { normalizeRole } from '../../auth/roles';

interface Props {
  alAbrirMenu: () => void;
  menuAbierto: boolean;
}

/**
 * Cabecera.
 *
 * El boton de menu solo existe por debajo de `lg`: en escritorio el sidebar ya
 * esta siempre visible y un boton que lo oculte seria ruido. En movil es
 * obligatorio, porque sin el no hay forma de llegar a la navegacion.
 *
 * El nombre se oculta en pantallas estrechas (`hidden sm:block`) porque con el
 * boton de menu, el nombre largo y el rol no caben a 375px sin partirse en dos
 * lineas o desbordar.
 */
const Header: React.FC<Props> = ({ alAbrirMenu, menuAbierto }) => {
  const { user, logout } = useAuth();
  const { hasUnsavedChanges } = useUnsavedChanges();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const handleLogout = () => {
    if (hasUnsavedChanges) {
      setShowLogoutModal(true);
    } else {
      logout();
    }
  };

  const confirmLogout = () => {
    setShowLogoutModal(false);
    logout();
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between gap-3 sticky top-0 z-[100] shadow-md [.modal-open_&]:z-[50] [.modal-open_&]:bg-transparent [.modal-open_&]:border-transparent [.modal-open_&]:shadow-none">
      <div className="flex items-center gap-3 min-w-0">
        {/* Solo movil: en escritorio el sidebar no se pliega. */}
        <button
          onClick={alAbrirMenu}
          className="lg:hidden p-2 -ml-1 text-medical-textMuted hover:text-medical-primary hover:bg-slate-100 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary"
          aria-label={menuAbierto ? 'Cerrar menu' : 'Abrir menu'}
          aria-expanded={menuAbierto}
        >
          <Menu size={22} />
        </button>

        <h1 className="hidden sm:block text-lg font-semibold text-medical-textMain truncate">
          Bienvenido, {user?.full_name || 'Usuario'}
        </h1>
        {/* En movil el saludo no cabe: se muestra solo el nombre. */}
        <h1 className="sm:hidden text-base font-semibold text-medical-textMain truncate">
          {user?.full_name?.split(' ')[0] || 'Usuario'}
        </h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        <NotificationBell />

        <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-4 border-l border-slate-200">
          <div className="h-9 w-9 bg-medical-primary rounded-full flex items-center justify-center text-white shrink-0">
            <User size={18} />
          </div>
          {/* El rol se normaliza: la BD guarda SUPER_ADMIN, el perfil puede
              traer 'admin'. Sin normalizar se veria el literal crudo. */}
          <div className="hidden md:flex flex-col">
            <span className="text-sm font-medium text-medical-textMain">
              {user?.full_name || 'Usuario'}
            </span>
            <span className="text-xs text-medical-textMuted">
              {normalizeRole(user?.role)}
            </span>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="p-2 text-slate-400 hover:text-medical-danger hover:bg-red-50 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-danger"
          title="Cerrar sesion"
          aria-label="Cerrar sesion"
        >
          <LogOut size={18} />
        </button>
      </div>

      {showLogoutModal && (
        <div
          className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-title"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
              <h3
                id="logout-title"
                className="text-lg font-semibold text-medical-textMain"
              >
                ¿Cerrar sesion?
              </h3>
            </div>
            {hasUnsavedChanges && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      Hay cambios sin guardar
                    </p>
                    <p className="text-xs text-amber-700 mt-1">
                      Si cierra sesion ahora, perderá la informacion que no haya guardado.
                    </p>
                  </div>
                </div>
              </div>
            )}
            <p className="text-sm text-slate-600 mb-6">
              ¿Esta seguro de que desea cerrar la sesion?
            </p>
            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary"
              >
                Cancelar
              </button>
              <button
                onClick={confirmLogout}
                className="px-4 py-2.5 text-sm font-semibold text-white rounded-lg bg-red-600 hover:bg-red-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-600"
              >
                <LogOut className="w-4 h-4 mr-2 inline-block" />
                Cerrar sesion
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
