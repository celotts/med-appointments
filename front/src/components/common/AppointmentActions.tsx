import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import axiosInstance from '../../api/axiosInstance';
import { Appointment } from '../../api/appointmentApi';
import { toast } from 'react-hot-toast';
import { CheckCircle, RotateCcw, PauseCircle, XCircle, AlertTriangle, Edit, Loader2 } from 'lucide-react';

interface AppointmentActionsProps {
  appointment: Appointment;
  isAdminOrSuperAdmin: boolean;
  isSpecialist: boolean;
  isAssistant: boolean;
  user: any;
  onRefresh: () => void;
  onEdit: (appt: Appointment) => void;
}

const AppointmentActions: React.FC<AppointmentActionsProps> = ({
  appointment,
  isAdminOrSuperAdmin,
  isSpecialist,
  isAssistant,
  user,
  onRefresh,
  onEdit,
}) => {
  const status = (appointment.status?.code || '').toUpperCase();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const handleAction = async (action: string, reason?: string) => {
    setLoadingAction(action);
    try {
      let endpoint = '';
      let payload: any = { reason };

      switch (action) {
        case 'confirm':
          endpoint = `/appointments/${appointment.id}/confirm`;
          break;
        case 'attend':
          endpoint = `/appointments/${appointment.id}/attend`;
          break;
        case 'suspend':
          endpoint = `/appointments/${appointment.id}/suspend`;
          break;
        case 'cancel':
          endpoint = `/appointments/${appointment.id}/cancel`;
          break;
        case 'reactivate':
          endpoint = `/appointments/${appointment.id}/reactivate`;
          break;
      }

      await axiosInstance.post(endpoint, payload);
      toast.success(`Cita ${action === 'attend' ? 'atendida' : action}d correctamente`);
      onRefresh();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al ${action} la cita`);
    } finally {
      setLoadingAction(null);
    }
  };

  const confirmAction = (action: string, label: string, reasonPrompt?: string) => {
    if (reasonPrompt) {
      const reason = prompt(`${label} - Ingrese el motivo (opcional):`);
      if (reason === null) return;
      handleAction(action, reason);
    } else {
      if (!confirm(`¿Confirmar ${label.toLowerCase()} esta cita?`)) return;
      handleAction(action);
    }
  };

  const canConfirm = status === 'PENDIENTE' && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canAttend = (status === 'CONFIRMADA' || status === 'REAGENDADA' || status === 'PENDIENTE') && isSpecialist && !isAssistant;
  const canSuspend = (status === 'PENDIENTE' || status === 'CONFIRMADA' || status === 'REAGENDADA') && (isAdminOrSuperAdmin || isSpecialist) && !isAssistant;
  const canCancel = (status === 'PENDIENTE' || status === 'CONFIRMADA' || status === 'REAGENDADA' || status === 'SUSPENDIDA') && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canReactivate = status === 'CANCELADA' && (isAdminOrSuperAdmin || isSpecialist);
  const canEdit = (status !== 'ATENDIDA') && (isAdminOrSuperAdmin || isSpecialist || isAssistant);

  const isTerminal = status === 'ATENDIDA';
  if (isTerminal) return null;

  const actions: Array<{
    label: string;
    action: string;
    icon: React.ReactNode;
    color: string;
    reasonPrompt?: string;
  }> = [];

  if (canConfirm) actions.push({ label: 'Confirmar', action: 'confirm', icon: <CheckCircle size={14} />, color: 'bg-blue-600 hover:bg-blue-700' });
  if (canAttend) actions.push({ label: 'Atender', action: 'attend', icon: <CheckCircle size={14} />, color: 'bg-emerald-600 hover:bg-emerald-700' });
  if (canSuspend) actions.push({ label: 'Suspender', action: 'suspend', icon: <PauseCircle size={14} />, color: 'bg-slate-600 hover:bg-slate-700', reasonPrompt: 'Motivo de suspensión' });
  if (canCancel) actions.push({ label: 'Cancelar', action: 'cancel', icon: <XCircle size={14} />, color: 'bg-red-600 hover:bg-red-700', reasonPrompt: 'Motivo de cancelación' });
  if (canReactivate) actions.push({ label: 'Reactivar', action: 'reactivate', icon: <RotateCcw size={14} />, color: 'bg-indigo-600 hover:bg-indigo-700' });
  if (canEdit) actions.push({ label: 'Editar', action: 'edit', icon: <Edit size={14} />, color: 'bg-indigo-600 hover:bg-indigo-700' });

  if (actions.length === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {actions.map((a) => (
        <button
          key={a.action}
          type="button"
          disabled={loadingAction === a.action}
          onClick={() => {
            if (a.action === 'edit') {
              onEdit(appointment);
            } else {
              confirmAction(a.action, a.label, a.reasonPrompt);
            }
          }}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-white transition-all shadow-sm ${a.color} disabled:opacity-50 disabled:cursor-not-allowed`}
          title={a.label}
        >
          {a.icon}
          {loadingAction === a.action ? <Loader2 className="animate-spin" size={12} /> : a.label}
        </button>
      ))}
    </div>
  );
};

export default AppointmentActions;