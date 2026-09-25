import React, { useState } from 'react';
import axiosInstance from '../../api/axiosInstance';
import { Appointment } from '../../api/appointmentApi';
import { toast } from 'react-hot-toast';
import { CheckCircle, RotateCcw, PauseCircle, XCircle, Edit, Loader2, MoreVertical, Clock, Play, UserCheck } from 'lucide-react';
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
  const [reason, setReason] = useState('');
  const [showReasonModal, setShowReasonModal] = useState<string | null>(null);


  const handleAction = async (action: string, reason?: string) => {
    setLoadingAction(action);
    try {
      let endpoint = '';
      let payload: any = { reason };

      switch (action) {
        case 'confirm':
          endpoint = `/appointments/${appointment.id}/confirm`;
          break;
        case 'wait':
          endpoint = `/appointments/${appointment.id}/wait`;
          break;
        case 'start':
          endpoint = `/appointments/${appointment.id}/start`;
          break;
        case 'attend':
          endpoint = `/appointments/${appointment.id}/attend`;
          payload = { notes: reason };
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
      const actionLabels: Record<string, string> = {
        confirm: 'confirmada',
        wait: 'en espera',
        start: 'iniciada',
        attend: 'atendida',
        suspend: 'suspendida',
        cancel: 'cancelada',
        reactivate: 'reactivada',
      };
      toast.success(`Cita ${actionLabels[action] || action}d correctamente`);
      onRefresh();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al ${action} la cita`);
    } finally {
      setLoadingAction(null);
      setShowReasonModal(null);
      setReason('');
    }
  };


  const confirmAction = (action: string, label: string, requiresReason: boolean = false) => {
    if (requiresReason) {
      setShowReasonModal(action);
    } else {
      if (!confirm(`¿Confirmar ${label.toLowerCase()} esta cita?`)) return;
      handleAction(action);
    }
  };


  const canConfirm = status === 'PENDIENTE' && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canWait = status === 'CONFIRMADA' && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canStart = status === 'EN ESPERA' && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canAttend = status === 'EN PROCESO' && isSpecialist && !isAssistant;
  const canSuspend = (status === 'PENDIENTE' || status === 'CONFIRMADA' || status === 'EN ESPERA' || status === 'EN PROCESO' || status === 'REAGENDADA') && (isAdminOrSuperAdmin || isSpecialist) && !isAssistant;
  const canCancel = (status === 'PENDIENTE' || status === 'CONFIRMADA' || status === 'EN ESPERA' || status === 'EN PROCESO' || status === 'REAGENDADA' || status === 'SUSPENDIDA') && (isAdminOrSuperAdmin || isSpecialist || isAssistant);
  const canReactivate = status === 'CANCELADA' && (isAdminOrSuperAdmin || isSpecialist);
  const canEdit = (status !== 'ATENDIDA' && status !== 'CANCELADA') && (isAdminOrSuperAdmin || isSpecialist || isAssistant);


  const isTerminal = status === 'ATENDIDA';
  if (isTerminal) return null;


  const actions: Array<{
    label: string;
    action: string;
    icon: React.ReactNode;
    color: string;
    requiresReason?: boolean;
  }> = [];


  if (canConfirm) actions.push({ label: 'Confirmar', action: 'confirm', icon: <CheckCircle size={14} />, color: 'text-blue-600 hover:bg-blue-50' });
  if (canWait) actions.push({ label: 'Paciente Llegó', action: 'wait', icon: <Clock size={14} />, color: 'text-violet-600 hover:bg-violet-50' });
  if (canStart) actions.push({ label: 'Iniciar Consulta', action: 'start', icon: <Play size={14} />, color: 'text-orange-600 hover:bg-orange-50' });
  if (canAttend) actions.push({ label: 'Atender', action: 'attend', icon: <UserCheck size={14} />, color: 'text-emerald-600 hover:bg-emerald-50', requiresReason: true });
  if (canSuspend) actions.push({ label: 'Suspender', action: 'suspend', icon: <PauseCircle size={14} />, color: 'text-slate-600 hover:bg-slate-50', requiresReason: true });
  if (canCancel) actions.push({ label: 'Cancelar', action: 'cancel', icon: <XCircle size={14} />, color: 'text-red-600 hover:bg-red-50', requiresReason: true });
  if (canReactivate) actions.push({ label: 'Reactivar', action: 'reactivate', icon: <RotateCcw size={14} />, color: 'text-indigo-600 hover:bg-indigo-50' });
  if (canEdit) actions.push({ label: 'Editar', action: 'edit', icon: <Edit size={14} />, color: 'text-indigo-600 hover:bg-indigo-50' });


  if (actions.length === 0) return null;


  return (
    <>
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
                        } else if (a.requiresReason) {
                          setShowReasonModal(a.action);
                        } else {
                          confirmAction(a.action, a.label);
                        }
                      }}
                      disabled={loadingAction === a.action || showReasonModal !== null}
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
      {showReasonModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-medical-textMain mb-2">
              {showReasonModal === 'attend' ? 'Notas de la atención' : 
               showReasonModal === 'suspend' ? 'Motivo de suspensión' : 
               'Motivo de cancelación'}
            </h3>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border-2 border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-primary focus:border-transparent outline-none text-sm transition-all hover:border-slate-300 bg-white"
              placeholder={showReasonModal === 'attend' ? 'Notas de la atención (opcional)' : 'Motivo obligatorio...'}
              required={showReasonModal !== 'attend'}
            />
            <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
              <span>Este campo es obligatorio para continuar</span>
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => { setShowReasonModal(null); setReason(''); }}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleAction(showReasonModal, reason)}
                disabled={loadingAction === showReasonModal || (showReasonModal !== 'attend' && !reason.trim())}
                className="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800"
              >
                {loadingAction === showReasonModal ? <Loader2 className="animate-spin mr-2" size={16} /> : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AppointmentActions;