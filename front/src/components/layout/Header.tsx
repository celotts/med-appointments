import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, User, Globe } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-medical-textMain">
          Welcome back, {user?.fullName || 'Doctor'}
        </h1>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm text-medical-textMuted cursor-pointer hover:text-medical-primary transition-colors">
          <Globe size={18} />
          <span>English</span>
        </div>

        <div className="flex items-center gap-3 pl-6 border-l border-slate-200">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-slate-100 rounded-full flex items-center justify-center text-medical-primary">
              <User size={18} />
            </div>
            <span className="text-sm font-medium text-medical-textMain">{user?.fullName || 'User'}</span>
          </div>

          <button
            onClick={logout}
            className="p-2 text-slate-400 hover:text-red-500 transition-colors"
            title="Logout"
          >
            <LogOut size={20} />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
