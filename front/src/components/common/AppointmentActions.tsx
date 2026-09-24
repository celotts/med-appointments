import React, { useState } from 'react';
import axiosInstance from '../../api/axiosInstance';
import { Appointment } from '../../api/appointmentApi';
import { toast } from 'react-hot-toast';
import { CheckCircle, RotateCcw, PauseCircle, XCircle, Edit, Loader2, MoreVertical } from 'lucide-react';
import { Menu, MenuButton, MenuItem, MenuItems, Transition } from '@headlessui/react';


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


  if (canConfirm) actions.push({ label: 'Confirmar', action: 'confirm', icon: <CheckCircle size={14} />, color: 'text-blue-600 hover:bg-blue-50' });
  if (canAttend) actions.push({ label: 'Atender', action: 'attend', icon: <CheckCircle size={14} />, color: 'text-emerald-600 hover:bg-emerald-50' });
  if (canSuspend) actions.push({ label: 'Suspender', action: 'suspend', icon: <PauseCircle size={14} />, color: 'text-slate-600 hover:bg-slate-50', reasonPrompt: 'Motivo de suspensión' });
  if (canCancel) actions.push({ label: 'Cancelar', action: 'cancel', icon: <XCircle size={14} />, color: 'text-red-600 hover:bg-red-50', reasonPrompt: 'Motivo de cancelación' });
  if (canReactivate) actions.push({ label: 'Reactivar', action: 'reactivate', icon: <RotateCcw size={14} />, color: 'text-indigo-600 hover:bg-indigo-50' });
  if (canEdit) actions.push({ label: 'Editar', action: 'edit', icon: <Edit size={14} />, color: 'text-indigo-600 hover:bg-indigo-50' });


  if (actions.length === 0) return null;


  return (
    <Menu as="div" className="relative inline-block text-left">
      <div>
        <MenuButton className="inline-flex justify-center w-full rounded-md bg-white p-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75">
          <MoreVertical className="h-5 w-5" aria-hidden="true" />
        </MenuButton>
      </div>
      <Transition
        as={React.Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <MenuItems className="absolute right-0 mt-2 w-56 origin-top-right divide-y divide-slate-100 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
          <div className="px-1 py-1 ">
            {actions.map((a) => (
              <MenuItem key={a.action}>
                {({ active }) => (
                  <button
                    onClick={() => {
                      if (a.action === 'edit') {
                        onEdit(appointment);
                      } else {
                        confirmAction(a.action, a.label, a.reasonPrompt);
                      }
                    }}
                    disabled={loadingAction === a.action}
                    className={`${
                      active ? 'bg-medical-primary text-white shadow-md shadow-blue-500/30' : 'bg-white ' + a.color
                    } group flex w-full items-center rounded-md px-3 py-2.5 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 hover:shadow-sm`}
                  >
                    {loadingAction === a.action ? <Loader2 className="animate-spin mr-2" size={16} /> : <span className="mr-3">{a.icon}</span>}
                    {a.label}
                  </button>
                )}
              </MenuItem>
            ))}
          </div>
        </MenuItems>
      </Transition>
    </Menu>
  );
};


export default AppointmentActions;