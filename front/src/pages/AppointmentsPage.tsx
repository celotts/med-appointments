import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { appointmentApi, Appointment, AppointmentCreate, AppointmentStatus } from '../api/appointmentApi';
import { patientApi, Patient } from '../api/patientApi';
import { doctorApi, Doctor } from '../api/doctorApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2, Calendar as CalendarIcon } from 'lucide-react';
import { toast } from 'react-hot-toast';

const statusColors: Record<string, string> = {
  'PENDIENTE': 'bg-amber-100 text-amber-700 border-amber-200',
  'CONFIRMADA': 'bg-blue-100 text-blue-700 border-blue-200',
  'COMPLETADA': 'bg-emerald-100 text-emerald-700 border-emerald-200',
  'CANCELADA': 'bg-red-100 text-red-700 border-red-200',
  'SUSPENDIDA': 'bg-slate-100 text-slate-700 border-slate-200',
  'REAGENDADA': 'bg-indigo-100 text-indigo-700 border-indigo-200',
};

const OCCUPYING_STATUSES = ['PENDIENTE', 'CONFIRMADA', 'REAGENDADA'];

const pad = (n: number) => String(n).padStart(2, '0');

const toLocalInput = (iso?: string) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const AppointmentsPage: React.FC = () => {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [statuses, setStatuses] = useState<AppointmentStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const { register, handleSubmit, reset, getValues, formState: { errors, isSubmitting } } = useForm<AppointmentCreate>();

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [appts, pats, docs, stats] = await Promise.all([
        appointmentApi.getAll(),
        patientApi.getAll(),
        doctorApi.getAll(),
        appointmentApi.getStatuses(),
      ]);
      setAppointments(Array.isArray(appts) ? appts : []);
      setPatients(Array.isArray(pats) ? pats : []);
      setDoctors(Array.isArray(docs) ? docs : []);
      setStatuses(Array.isArray(stats) ? stats : []);
    } catch (error) {
      toast.error('Error al cargar los datos de la agenda');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const patientName = (id: number) => {
    const p = patients.find((x) => x.id === id);
    return p ? `${p.first_name} ${p.last_name}` : `Paciente #${id}`;
  };
  const doctorName = (id: number) => {
    const d = doctors.find((x) => x.id === id);
    return d ? `Dr. ${d.first_name} ${d.last_name}` : `Médico #${id}`;
  };

  const hasDoctorConflict = (start?: string, end?: string, doctorId?: number) => {
    if (!start || !end || !doctorId) return false;
    const s = new Date(start).getTime();
    const e = new Date(end).getTime();
    if (isNaN(s) || isNaN(e)) return false;
    return appointments.some(
      (a) =>
        a.doctor_id === Number(doctorId) &&
        a.id !== editingAppointment?.id &&
        OCCUPYING_STATUSES.includes((a.status?.code || '').toUpperCase()) &&
        new Date(a.start_datetime).getTime() < e &&
        new Date(a.end_datetime).getTime() > s
    );
  };

  const openCreate = () => {
    setEditingAppointment(null);
    reset({
      patient_id: 0,
      doctor_id: 0,
      start_datetime: '',
      end_datetime: '',
      reason: '',
    });
    setIsModalOpen(true);
  };

  const openEdit = (appt: Appointment) => {
    setEditingAppointment(appt);
    reset({
      patient_id: appt.patient_id,
      doctor_id: appt.doctor_id,
      start_datetime: toLocalInput(appt.start_datetime),
      end_datetime: toLocalInput(appt.end_datetime),
      reason: appt.reason,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: AppointmentCreate) => {
    const start = new Date(data.start_datetime).getTime();
    const end = new Date(data.end_datetime).getTime();
    if (isNaN(start) || isNaN(end) || end <= start) {
      toast.error('La fecha/hora de fin debe ser posterior al inicio');
      return;
    }
    if (hasDoctorConflict(data.start_datetime, data.end_datetime, data.doctor_id)) {
      toast.error('El médico ya tiene una cita en ese horario');
      return;
    }
    try {
      const payload = {
        patient_id: Number(data.patient_id),
        doctor_id: Number(data.doctor_id),
        start_datetime: new Date(data.start_datetime).toISOString(),
        end_datetime: new Date(data.end_datetime).toISOString(),
        reason: data.reason,
      };
      if (editingAppointment) {
        await appointmentApi.update(editingAppointment.id, payload);
        toast.success('Cita actualizada correctamente');
      } else {
        await appointmentApi.create(payload);
        toast.success('Cita programada correctamente');
      }
      setIsModalOpen(false);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al guardar la cita');
    }
  };

  const handleDelete = async (appt: Appointment) => {
    if (!confirm(`¿Estás seguro de eliminar la cita #${appt.id}?`)) return;
    try {
      await appointmentApi.delete(appt.id);
      toast.success('Cita eliminada correctamente');
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al eliminar la cita');
    }
  };

  const filtered = appointments.filter(
    (a) =>
      patientName(a.patient_id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      doctorName(a.doctor_id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.reason || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    {
      header: 'Paciente',
      accessor: (a: Appointment) => (
        <span className="font-medium text-medical-textMain">{patientName(a.patient_id)}</span>
      )
    },
    {
      header: 'Doctor',
      accessor: (a: Appointment) => (
        <span className="text-slate-600">{doctorName(a.doctor_id)}</span>
      )
    },
    {
      header: 'Fecha y Hora',
      accessor: (a: Appointment) => (
        <div className="flex items-center gap-2 text-slate-600">
          <CalendarIcon size={14} />
          {a.start_datetime ? new Date(a.start_datetime).toLocaleString() : '-'}
        </div>
      )
    },
    {
      header: 'Estado',
      accessor: (a: Appointment) => {
        const status = a.status?.code || statuses.find((s) => s.id === a.status_id)?.code || 'DESCONOCIDO';
        const colorClass = statusColors[status.toUpperCase()] || 'bg-slate-100 text-slate-600 border-slate-200';
        return (
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClass}`}>
            {status}
          </span>
        );
      }
    },
    {
      header: 'Motivo',
      accessor: (a: Appointment) => (
        <span className="text-slate-600 truncate max-w-xs block">{a.reason || '-'}</span>
      )
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Agenda Médica</h2>
          <p className="text-medical-textMuted">Gestión de citas, reprogramaciones y estados</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nueva Cita
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por paciente, doctor o motivo..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Sincronizando agenda...</p>
          </div>
        ) : (
          <DataTable
            data={filtered}
            columns={columns}
            onEdit={openEdit}
            onDelete={handleDelete}
          />
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingAppointment ? 'Reprogramar Cita' : 'Nueva Cita'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Paciente *</label>
              <select
                {...register('patient_id', {
                  required: 'Paciente requerido',
                  setValueAs: (v) => (v === '' || v === null ? undefined : Number(v))
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              >
                <option value="">Seleccionar paciente...</option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              {errors.patient_id && <p className="text-red-500 text-xs mt-1">{errors.patient_id.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Doctor *</label>
              <select
                {...register('doctor_id', {
                  required: 'Doctor requerido',
                  setValueAs: (v) => (v === '' || v === null ? undefined : Number(v))
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              >
                <option value="">Seleccionar doctor...</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>Dr. {d.first_name} {d.last_name}</option>
                ))}
              </select>
              {errors.doctor_id && <p className="text-red-500 text-xs mt-1">{errors.doctor_id.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Inicio *</label>
              <input
                type="datetime-local"
                {...register('start_datetime', {
                  required: 'Fecha de inicio requerida',
                  validate: (value) =>
                    hasDoctorConflict(value, getValues('end_datetime'), getValues('doctor_id'))
                      ? 'El médico ya tiene una cita en ese horario'
                      : true
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.start_datetime && <p className="text-red-500 text-xs mt-1">{errors.start_datetime.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Fin *</label>
              <input
                type="datetime-local"
                {...register('end_datetime', {
                  required: 'Fecha de fin requerida',
                  validate: (value) =>
                    hasDoctorConflict(getValues('start_datetime'), value, getValues('doctor_id'))
                      ? 'El médico ya tiene una cita en ese horario'
                      : true
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.end_datetime && <p className="text-red-500 text-xs mt-1">{errors.end_datetime.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Motivo de la Cita *</label>
            <textarea
              {...register('reason', { required: 'El motivo es requerido' })}
              rows={3}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              placeholder="Describa brevemente el motivo de la consulta..."
            />
            {errors.reason && <p className="text-red-500 text-xs mt-1">{errors.reason.message}</p>}
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-medical-primary hover:bg-blue-800 rounded-lg transition-colors disabled:opacity-70 flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="animate-spin" size={16} />}
              {editingAppointment ? 'Guardar Cambios' : 'Programar Cita'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default AppointmentsPage;
