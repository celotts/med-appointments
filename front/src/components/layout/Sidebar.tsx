import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  Users,
  UserRound,
  Bot,
  BarChart3,
  Settings,
  Stethoscope
} from 'lucide-react';

const menuItems = [
  { path: '/', name: 'Dashboard', icon: LayoutDashboard },
  { path: '/appointments', name: 'Agenda', icon: Calendar },
  { path: '/patients', name: 'Pacientes', icon: Users },
  { path: '/doctors', name: 'Doctores', icon: UserRound },
  { path: '/ai-assistant', name: 'Asistente IA', icon: Bot },
  { path: '/reports', name: 'Reportes', icon: BarChart3 },
  { path: '/settings', name: 'Configuración', icon: Settings },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-medical-primary h-screen sticky top-0 text-white flex flex-col shadow-xl">
      <div className="p-6 flex items-center gap-3 border-b border-medical-operation">
        <div className="bg-medical-success text-medical-primary rounded-full p-2">
          <Stethoscope size={24} />
        </div>
        <span className="font-bold text-xl tracking-tight">MedApp</span>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {menuItems.map(({ path, name, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => `
              flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
              ${isActive
                ? `bg-medical-visit text-white shadow-md`
                : `text-medical-textMuted`}
            `}
          >
            <Icon size={20} />
            <span className="font-medium">{name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border-slate-200">
        <div className="bg-medical-primary/5 p-4 rounded-xl text-xs text-medical-textMuted">
          <p className="font-semibold mb-1">Agenda Sana v1.0</p>
          <p>Sistema de gestión médica</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;