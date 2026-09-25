import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useUnsavedChanges } from '../../contexts/UnsavedChangesContext';
import { LogOut, User, ChevronDown, AlertTriangle, X, Check } from 'lucide-react';
import NotificationBell from '../common/NotificationBell';

const Header: React.FC = () => {
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
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-[100] shadow-md [.modal-open_&]:z-[50] [.modal-open_&]:bg-transparent [.modal-open_&]:border-transparent [.modal-open_&]:shadow-none" style={{ backgroundColor: '#ffffff', position: 'sticky', top: 0 }}>
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-medical-textMain">
          Bienvenido, {user?.full_name || 'Usuario'}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <NotificationBell />
        <div className="flex items-center gap-3 pl-4 border-l border-medical-textMuted/30">
          <div className="h-9 w-9 bg-medical-primary rounded-full flex items-center justify-center text-white">
            <User size={18} />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-medical-textMain">
              {user?.full_name || 'Usuario'}
            </span>
            <span className="text-xs text-medical-textMuted capitalize">
              {user?.role || 'user'}
            </span>
          </div>
          <ChevronDown size={14} className="text-medical-textMuted/60" />
        </div>

        <button
          onClick={handleLogout}
          className="ml-2 p-2 text-medical-textMuted/60 hover:text-medical-danger hover:bg-medical-danger/5 rounded-lg transition-all"
          title="Cerrar sesión"
        >
          <LogOut size={18} />
        </button>
      </div>

      {showLogoutModal && (
        <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
              <h3 className="text-lg font-semibold text-medical-textMain">¿Cerrar sesión?</h3>
            </div>
            {hasUnsavedChanges && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Hay cambios sin guardar</p>
                    <p className="text-xs text-amber-700 mt-1">
                      Si cierra sesión ahora, perderá la información que no haya guardado.
                    </p>
                  </div>
                </div>
              </div>
            )}
            <p className="text-sm text-slate-600 mb-6">
              ¿Está seguro de que desea cerrar la sesión?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmLogout}
                className="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-all bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800"
              >
                <LogOut className="w-4 h-4 mr-2 inline-block" />
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;