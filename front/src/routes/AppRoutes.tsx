import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '../components/layout/ProtectedRoute';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import PatientsPage from '../pages/PatientsPage';
import DoctorsPage from '../pages/DoctorsPage';
import AppointmentsPage from '../pages/AppointmentsPage';
import SpecialtyPage from '../pages/SpecialtyPage';
import BranchPage from '../pages/BranchPage';
import RolePage from '../pages/RolePage';
import AppointmentStatusPage from '../pages/AppointmentStatusPage';
import ConsultingRoomPage from '../pages/ConsultingRoomPage';
import DoctorSchedulePage from '../pages/DoctorSchedulePage';
import AIAssistantPage from '../pages/AIAssistantPage';
import ReportsPage from '../pages/ReportsPage';
import SettingsPage from '../pages/SettingsPage';
import MainLayout from '../components/layout/MainLayout';
import {
  SUPER_ADMIN,
  ADMIN,
  DOCTOR,
  SPECIALIST,
  ASSISTANT,
} from '../auth/roles';

/** Espejo de `rbac.DASHBOARD_ROLES`. */
const DASHBOARD_ROLES = [SUPER_ADMIN, ADMIN, DOCTOR, SPECIALIST, ASSISTANT] as const;
/** Espejo de `rbac.ADMIN_ROLES`. */
const ADMIN_ROLES = [SUPER_ADMIN, ADMIN] as const;

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          {/* El panel operativo exige un rol de agenda en el backend; el
              `Navigate` de ProtectedRoute evita mostrarlo a un PATIENT. */}
          <Route
            path="/"
            element={
              <ProtectedRoute roles={DASHBOARD_ROLES}>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/patients" element={<PatientsPage />} />
          <Route path="/doctors" element={<DoctorsPage />} />
          <Route path="/specialties" element={<SpecialtyPage />} />
          {/* Rutas de administracion: el backend ya exige require_admin. */}
          <Route
            path="/branches"
            element={
              <ProtectedRoute roles={ADMIN_ROLES}>
                <BranchPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/roles"
            element={
              <ProtectedRoute roles={ADMIN_ROLES}>
                <RolePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/appointment-statuses"
            element={
              <ProtectedRoute roles={ADMIN_ROLES}>
                <AppointmentStatusPage />
              </ProtectedRoute>
            }
          />
          <Route path="/consulting-rooms" element={<ConsultingRoomPage />} />
          <Route
            path="/doctor-schedules"
            element={
              <ProtectedRoute roles={DASHBOARD_ROLES}>
                <DoctorSchedulePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ai-assistant"
            element={
              <ProtectedRoute roles={DASHBOARD_ROLES}>
                <AIAssistantPage />
              </ProtectedRoute>
            }
          />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
