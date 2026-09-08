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
  { path: '/appointments', name: 'Appointments', icon: Calendar },
  { path: '/patients', name: 'Patients', icon: Users },
  { path: '/doctors', name: 'Doctors', icon: UserRound },
  { path: '/ai-assistant', name: 'MedAssist AI', icon: Bot },
  { path: '/reports', name: 'Reports', icon: BarChart3 },
  { path: '/settings', name: 'Settings', icon: Settings },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-medical-primary h-screen sticky top-0 text-white flex flex-col shadow-xl">
      <div className="p-6 flex items-center gap-3 border-b border-blue-800">
        <div className="bg-white text-medical-primary p-2 rounded-lg">
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
                ? 'bg-medical-secondary text-white shadow-md'
                : 'text-blue-100 hover:bg-blue-800 hover:text-white'}
            `}
          >
            <Icon size={20} />
            <span className="font-medium">{name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-blue-800">
        <div className="bg-blue-950 p-4 rounded-xl text-xs text-blue-300">
          <p className="font-semibold mb-1">Clinic System v1.0</p>
          <p>Ready for clinical use</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
