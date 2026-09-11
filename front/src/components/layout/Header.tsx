import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, User, ChevronDown } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-medical-primary/10 border-b border-medical-textMuted/30 px-6 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-medical-textMain">
          Bienvenido, {user?.full_name || 'Usuario'}
        </h1>
      </div>

      <div className="flex items-center gap-4">
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
          onClick={logout}
          className="ml-2 p-2 text-medical-textMuted/60 hover:text-medical-danger hover:bg-medical-danger/5 rounded-lg transition-all"
          title="Cerrar sesión"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
};

export default Header;