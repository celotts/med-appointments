import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { appointmentApi, Appointment, AppointmentCreate, AppointmentStatus } from '../api/appointmentApi';
import { patientApi, Patient } from '../api/patientApi';
import { doctorApi, Doctor } from '../api/doctorApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { TableSkeleton } from '../components/common/Skeleton';
import { Plus, Search } from 'lucide-react';
import { toast } from 'react-hot-toast';

const statusColors: Record<string, string> = {
  'programada': 'bg-blue-100 text-blue-700',
  'scheduled': 'bg-blue-100 text-blue-700',
  'confirmada': 'bg-green-100 text-green-700',
  'confirmed': 'bg-green-100 text-green-700',
  'en_progreso': 'bg-yellow-100 text-yellow-700',
  'in_progress': 'bg-yellow-100 text-yellow-700',
  'completada': 'bg-emerald-100 text-emerald-700',
  'completed': 'bg-emerald-100 text-emerald-700',
  'cancelada': 'bg-red-100 text-red-700',
  'cancelled': 'bg-red-100 text-red-700',
  'no_show': 'bg-orange-100 text-orange-700',
  'reprogramada': 'bg-purple-100 text-purple-700',
  'rescheduled': 'bg-purple-100 text-purple-700',
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
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<AppointmentCreate>();

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
      toast.error('Error al cargar datos');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const openCreate = () => {
    setEditingAppointment(null);
    reset({ patient_id: 0, doctor_id: 0, status_id: 1, appointment_date: '', reason: '' });
    setIsModalOpen(true);
  };

  const openEdit = (appt: Appointment) => {
    setEditingAppointment(appt);
    reset({
      patient_id: appt.patient_id,
      doctor_id: appt.doctor_id,
      status_id: appt.status_id,
      appointment_date: appt.appointment_date?.slice(0, 16) || '',
      reason: appt.reason || '',
      notes: appt.notes || '',
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: AppointmentCreate) => {
    try {
      if (editingAppointment) {
        await appointmentApi.update(editingAppointment.id, data);
        toast.success('Cita actualizada');
      } else {
        await appointmentApi.create(data);
        toast.success('Cita creada');
      }
      setIsModalOpen(false);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (appt: Appointment) => {
    if (!confirm('¿Eliminar esta cita?')) return;
    try {
      await appointmentApi.delete(appt.id);
      toast.success('Cita eliminada');
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const getPatientName = (id: number) => {
    const p = patients.find((p) => p.id === id);
    return p ? `${p.first_name} ${p.last_name}` : `#${id}`;
  };

  const getDoctorName = (id: number) => {
    const d = doctors.find((d) => d.id === id);
    return d ? `Dr. ${d.first_name} ${d.last_name}` : `#${id}`;
  };

  const getStatusName = (id: number) => {
    const s = statuses.find((s) => s.id === id);
    return s?.name || null;
  };

  const getStatusColor = (name: string | null) => {
    if (!name) return 'bg-slate-100 text-slate-700';
    return statusColors[name.toLowerCase().replace(/\s+/g, '_')] || 'bg-slate-100 text-slate-700';
  };

  const filtered = appointments.filter(
    (a) =>
      getPatientName(a.patient_id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      getDoctorName(a.doctor_id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.reason || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Paciente', accessor: (a: Appointment) => getPatientName(a.patient_id) },
    { header: 'Doctor', accessor: (a: Appointment) => getDoctorName(a.doctor_id) },
    { header: 'Fecha', accessor: (a: Appointment) => {
      if (!a.appointment_date) return '-';
      const d = new Date(a.appointment_date);
      return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }},
    { header: 'Estado', accessor: (a: Appointment) => {
      const name = getStatusName(a.status_id) || 'Sin estado';
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(name)}`}>
          {name}
        </span>
      );
    }},
    { header: 'Motivo', accessor: (a: Appointment) => a.reason || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Citas</h2>
          <p className="text-medical-textMuted">Gestion de citas médicas</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium"
        >
          <Plus size={18} />
          Nueva Cita
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por paciente, doctor o motivo..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <TableSkeleton rows={5} cols={5} />
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
        title={editingAppointment ? 'Editar Cita' : 'Nueva Cita'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Paciente *</label>
            <select
              {...register('patient_id', { required: 'Paciente requerido', valueAsNumber: true })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
            >
              <option value={0}>Seleccionar paciente...</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
              ))}
            </select>
            {errors.patient_id && <p className="text-red-500 text-xs mt-1">{errors.patient_id.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Doctor *</label>
            <select
              {...register('doctor_id', { required: 'Doctor requerido', valueAsNumber: true })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
            >
              <option value={0}>Seleccionar doctor...</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>Dr. {d.first_name} {d.last_name}</option>
              ))}
            </select>
            {errors.doctor_id && <p className="text-red-500 text-xs mt-1">{errors.doctor_id.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha y Hora *</label>
              <input
                type="datetime-local"
                {...register('appointment_date', { required: 'Fecha requerida' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              />
              {errors.appointment_date && <p className="text-red-500 text-xs mt-1">{errors.appointment_date.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Estado *</label>
              <select
                {...register('status_id', { required: 'Estado requerido', valueAsNumber: true })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              >
                {statuses.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              {errors.status_id && <p className="text-red-500 text-xs mt-1">{errors.status_id.message}</p>}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Motivo *</label>
            <textarea
              {...register('reason', { required: 'Motivo requerido' })}
              rows={3}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm resize-none"
            />
            {errors.reason && <p className="text-red-500 text-xs mt-1">{errors.reason.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Notas</label>
            <textarea
              {...register('notes')}
              rows={2}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-medical-textMuted hover:text-medical-textMain border border-slate-200 rounded-lg text-sm font-medium transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-medical-primary text-white rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors disabled:opacity-70"
            >
              {isSubmitting ? 'Guardando...' : editingAppointment ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default AppointmentsPage;
