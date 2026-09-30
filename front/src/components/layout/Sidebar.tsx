import React from 'react';
import { NavLink } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard,
  Calendar,
  Users,
  UserRound,
  Bot,
  BarChart3,
  Settings,
  Stethoscope,
  Building2,
  Shield,
  ClipboardList,
  Building,
  CalendarClock,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import {
  hasRole,
  isAdmin,
  isClinical,
  AGENDA_ROLES,
  DOCTOR,
  SPECIALIST,
} from '../../auth/roles';

interface MenuItem {
  path: string;
  name: string;
  icon: LucideIcon;
  /** `null` = visible para todos los roles del panel. */
  soloRoles?: readonly string[] | null;
}

/**
 * Navegacion filtrada por rol.
 *
 * Antes los 13 items se mostraban a todos: un DOCTOR veia `/roles` y
 * `/branches`, que exigen `require_admin` en el backend, asi que pulsaba y
 * recibia un 403 sin explicacion.
 *
 * Ocultar el enlace NO es la proteccion: el backend sigue exigiendo el rol.
 * Es solo para que el menu no ofrezca acciones que van a fallar.
 */
const MENU: MenuItem[] = [
  {
    path: '/',
    name: 'Dashboard',
    icon: LayoutDashboard,
    soloRoles: [...AGENDA_ROLES, 'SUPER_ADMIN', 'ADMIN'],
  },
  { path: '/appointments', name: 'Agenda', icon: Calendar, soloRoles: null },
  { path: '/patients', name: 'Pacientes', icon: Users, soloRoles: null },
  { path: '/doctors', name: 'Doctores', icon: UserRound, soloRoles: null },
  { path: '/specialties', name: 'Especialidades', icon: Stethoscope, soloRoles: null },
  // administracion: el backend exige require_admin
  { path: '/branches', name: 'Sucursales', icon: Building2, soloRoles: ['SUPER_ADMIN', 'ADMIN'] },
  { path: '/roles', name: 'Roles', icon: Shield, soloRoles: ['SUPER_ADMIN', 'ADMIN'] },
  {
    path: '/appointment-statuses',
    name: 'Estados Cita',
    icon: ClipboardList,
    soloRoles: ['SUPER_ADMIN', 'ADMIN'],
  },
  { path: '/consulting-rooms', name: 'Consultorios', icon: Building, soloRoles: null },
  {
    path: '/doctor-schedules',
    name: 'Horarios',
    icon: CalendarClock,
    soloRoles: [...AGENDA_ROLES, 'SUPER_ADMIN', 'ADMIN'],
  },
  {
    path: '/ai-assistant',
    name: 'Asistente IA',
    icon: Bot,
    soloRoles: [DOCTOR, SPECIALIST, 'SUPER_ADMIN', 'ADMIN'],
  },
  { path: '/reports', name: 'Reportes', icon: BarChart3, soloRoles: null },
  { path: '/settings', name: 'Configuración', icon: Settings, soloRoles: null },
];

interface Props {
  /** Se llama al navegar, para que el cajon movil se cierre solo. */
  alNavegar?: () => void;
}

const Sidebar: React.FC<Props> = ({ alNavegar }) => {
  const { user } = useAuth();
  const rol = user?.role;

  // Un PATIENT no deberia llegar aqui: ProtectedRoute solo exige token. Si
  // llega, no se le ofrece nada en vez de una lista de enlaces que fallan.
  if (!isClinical(rol)) {
    return (
      <aside className="w-64 bg-medical-primary h-screen sticky top-0 text-white flex flex-col shadow-xl">
        <div className="p-6 flex items-center gap-3 border-b border-medical-operation">
          <div className="bg-medical-success text-medical-primary rounded-full p-2">
            <Stethoscope size={24} />
          </div>
          <span className="font-bold text-xl tracking-tight">MedApp</span>
        </div>
        <div className="p-6 text-sm text-medical-textMuted">
          Su rol no tiene acceso a la gestion de la clinica.
        </div>
      </aside>
    );
  }

  const visibles = MENU.filter(
    (item) => !item.soloRoles || hasRole(rol, item.soloRoles)
  );

  return (
    <aside className="w-64 h-screen bg-medical-primary text-white flex flex-col shadow-xl lg:sticky lg:top-0">
      <div className="p-5 sm:p-6 flex items-center justify-between gap-3 border-b border-medical-operation">
        <div className="flex items-center gap-3">
          <div className="bg-medical-success text-medical-primary rounded-full p-2 shrink-0">
            <Stethoscope size={24} />
          </div>
          <span className="font-bold text-xl tracking-tight">MedApp</span>
        </div>
      </div>

      {/* El cajon movil necesita un borde de foco visible para teclado y un
          nombre accesible: un `aside` sin etiqueta no le dice a un lector de
          pantalla que es la navegacion principal. */}
      <nav
        className="flex-1 p-4 space-y-1.5 overflow-y-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        aria-label="Navegacion principal"
      >
        {visibles.map(({ path, name, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            onClick={alNavegar}
            className={({ isActive }) => `
              flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
              focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70
              ${isActive
                ? `bg-medical-visit text-white shadow-md font-semibold`
                : `text-medical-textMuted hover:bg-white/10 hover:text-white`}
            `}
          >
            <Icon size={20} />
            <span className="font-medium">{name}</span>
          </NavLink>
        ))}      </nav>

      <div className="p-4 border-t border-border-slate-200">
        <div className="bg-medical-primary/5 p-4 rounded-xl text-xs text-medical-textMuted">
          <p className="font-semibold mb-1">Agenda Sana v1.0</p>
          <p>{isAdmin(rol) ? 'Administracion de clinica' : 'Gestion de agenda'}</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
