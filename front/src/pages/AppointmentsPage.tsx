import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { appointmentApi, Appointment, AppointmentCreate, AppointmentStatus, PaginatedResponse } from '../api/appointmentApi';
import { patientApi, Patient } from '../api/patientApi';
import { doctorApi, Doctor } from '../api/doctorApi';
import DataTable, { Column } from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { FilterButtons } from '../components/common/FilterButtons';
import { Plus, Search, Loader2, Sparkles, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { medasistApi, RescheduleSuggestion, AvailabilitySlot } from '../api/medasistApi';

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
  const { user } = useAuth();
  const isAdminOrSuperAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'admin';
  const isSpecialist = user?.role === 'specialist' || user?.role === 'doctor';

  const [patients, setPatients] = useState<Patient[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [statuses, setStatuses] = useState<AppointmentStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  
  // Server-side pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  const { register, handleSubmit, reset, getValues, setValue, watch, formState: { errors, isSubmitting } } = useForm<AppointmentCreate>();

  // IA: sugerencias de reagendamiento
  const [aiAppt, setAiAppt] = useState<Appointment | null>(null);
  const [aiDate, setAiDate] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<RescheduleSuggestion[] | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // IA: horarios disponibles al crear/editar cita
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotError, setSlotError] = useState<string | null>(null);
  const [availableSlots, setAvailableSlots] = useState<AvailabilitySlot[] | null>(null);

  // Load reference data (patients, doctors, statuses)
  const loadReferenceData = useCallback(async () => {
    try {
      const [pats, docs, stats] = await Promise.all([
        patientApi.getAll(),
        doctorApi.getAll(),
        appointmentApi.getStatuses(),
      ]);

      let filteredPatients = Array.isArray(pats) ? pats : [];
      let filteredDoctors = Array.isArray(docs) ? docs : [];

      if (!isAdminOrSuperAdmin && isSpecialist) {
        filteredPatients = filteredPatients.filter((p) => p.doctor_id === user?.id);
        filteredDoctors = filteredDoctors.filter((d) => d.id === user?.id);
      }

      setPatients(filteredPatients);
      setDoctors(filteredDoctors);
      setStatuses(Array.isArray(stats) ? stats : []);
    } catch (error) {
      toast.error('Error al cargar datos de referencia');
    }
  }, [isAdminOrSuperAdmin, isSpecialist, user?.id]);

  // Load appointments with server-side pagination
  const loadAppointments = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // Determine page size: larger when searching to allow client-side filtering
      const fetchPageSize = searchTerm ? 100 : pageSize;
      
      const filters: { status?: string } = {};
      if (activeFilter !== 'all') {
        filters.status = activeFilter;
      }
      if (!isAdminOrSuperAdmin && isSpecialist) {
        // For specialists, the backend already filters by user_id
      }

      const response: PaginatedResponse<Appointment> = await appointmentApi.getAll(
        currentPage,
        fetchPageSize,
        filters
      );

      setAppointments(response.items);
      setTotalItems(response.total);
      setTotalPages(response.total_pages);
      
      // Adjust current page if it exceeds total pages
      if (currentPage > response.total_pages && response.total_pages > 0) {
        setCurrentPage(response.total_pages);
      }
    } catch (error) {
      toast.error('Error al cargar las citas');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize, searchTerm, activeFilter, isAdminOrSuperAdmin, isSpecialist]);

  // Load reference data on mount
  useEffect(() => {
    loadReferenceData();
  }, [loadReferenceData]);

  // Load appointments when pagination/filter changes
  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, activeFilter]);

  const patientName = (id: number) => {
    const p = patients.find((x) => x.id === id);
    return p ? `${p.first_name} ${p.last_name}` : `Paciente #${id}`;
  };
  const doctorName = (id: number) => {
    const d = doctors.find((x) => x.id === id);
    return d ? `Dr. ${d.first_name} ${d.last_name}` : `Médico #${id}`;
  };

  const statusName = (id: number) => {
    const s = statuses.find((x) => x.id === id);
    return s ? s.code : `Estado #${id}`;
  };

  const toDateInput = (iso?: string) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  };

  const fmtTime = (iso: string) => {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  // ── IA: reagendar con sugerencias ───────────────────────────────────────
  const openAiReschedule = (appt: Appointment) => {
    setAiAppt(appt);
    setAiDate(toDateInput(appt.start_datetime) || new Date().toISOString().slice(0, 10));
    setAiSuggestions(null);
    setAiError(null);
  };

  const closeAiReschedule = () => {
    setAiAppt(null);
    setAiSuggestions(null);
    setAiError(null);
  };

  const askAiSuggestions = async () => {
    if (!aiAppt || !aiDate) return;
    setAiLoading(true);
    setAiError(null);
    setAiSuggestions(null);
    try {
      const response = await medasistApi.reschedule({
        appointment_id: aiAppt.id,
        preferred_date: aiDate,
      });
      setAiSuggestions(response.suggestions);
      if (response.suggestions.length === 0) {
        setAiError('La IA no encontró horarios libres para esa fecha');
      }
    } catch (error: any) {
      setAiError(error.response?.data?.detail || 'Error al consultar la IA');
    } finally {
      setAiLoading(false);
    }
  };

  const applySuggestion = async (slot: RescheduleSuggestion) => {
    if (!aiAppt) return;
    try {
      await appointmentApi.update(aiAppt.id, {
        start_datetime: new Date(slot.start).toISOString(),
        end_datetime: new Date(slot.end).toISOString(),
        reason: aiAppt.reason,
      });
      toast.success('Cita reagendada con IA');
      closeAiReschedule();
      loadAppointments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al aplicar el horario');
    }
  };

  // ── IA: horarios disponibles en el formulario ───────────────────────────
  const askAvailableSlots = async () => {
    const doctorId = watch('doctor_id');
    const date = toDateInput(watch('start_datetime'));
    if (!doctorId) {
      toast.error('Selecciona un doctor primero');
      return;
    }
    if (!date) {
      toast.error('Selecciona la fecha de inicio primero');
      return;
    }
    setSlotLoading(true);
    setSlotError(null);
    setAvailableSlots(null);
    try {
      const slots = await medasistApi.getAvailableSlots({
        doctor_id: Number(doctorId),
        date,
        duration_minutes: 30,
      });
      setAvailableSlots(slots);
    } catch (error: any) {
      setSlotError(error.response?.data?.detail || 'Error al consultar disponibilidad');
    } finally {
      setSlotLoading(false);
    }
  };

  const applySlot = (slot: AvailabilitySlot) => {
    setValue('start_datetime', toLocalInput(slot.start), { shouldValidate: true });
    setValue('end_datetime', toLocalInput(slot.end), { shouldValidate: true });
  };

  const columns: Column<Appointment>[] = [
    {
      header: 'Fecha y Hora',
      accessor: 'start_datetime',
      type: 'date',
      sortable: true,
    },
    {
      header: 'Paciente',
      accessor: (a: Appointment) => (
        <span className="font-medium text-medical-textMain">{patientName(a.patient_id)}</span>
      ),
      sortable: true,
    },
    {
      header: 'Doctor',
      accessor: (a: Appointment) => (
        <span className="text-slate-600">{doctorName(a.doctor_id)}</span>
      ),
      sortable: true,
    },
    {
      header: 'Estado',
      accessor: (a: Appointment) => {
        const status = a.status?.code || statusName(a.status_id);
        const colorClass = statusColors[status] || 'bg-slate-100 text-slate-600 border-slate-200';
        return (
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClass}`}>
            {status}
          </span>
        );
      },
      sortable: true,
    },
    {
      header: 'Motivo',
      accessor: (a: Appointment) => (
        <span className="text-slate-600 truncate max-w-xs block">{a.reason || '-'}</span>
      ),
      sortable: true,
    },
    {
      header: 'IA',
      accessor: (a: Appointment) => {
        const status = (a.status?.code || statusName(a.status_id)).toUpperCase();
        if (status !== 'PENDIENTE') return null;
        return (
          <button
            type="button"
            onClick={() => openAiReschedule(a)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm"
          >
            <Sparkles size={14} />
            Sugerir horarios
          </button>
        );
      },
    },
  ];

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
      loadAppointments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al guardar la cita');
    }
  };

  const handleDelete = async (appt: Appointment) => {
    if (!confirm(`¿Estás seguro de eliminar la cita #${appt.id}?`)) return;
    try {
      await appointmentApi.delete(appt.id);
      toast.success('Cita eliminada correctamente');
      loadAppointments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al eliminar la cita');
    }
  };

  // Client-side search filtering on current page data
  const filteredAppointments = useMemo(() => {
    if (!searchTerm) return appointments;
    
    const term = searchTerm.toLowerCase();
    return appointments.filter(
      (a) =>
        patientName(a.patient_id).toLowerCase().includes(term) ||
        doctorName(a.doctor_id).toLowerCase().includes(term) ||
        (a.reason || '').toLowerCase().includes(term)
    );
  }, [appointments, searchTerm, patients, doctors]);

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
        <div className="mb-6">
          <div className="relative max-w-sm mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Buscar por paciente, doctor o motivo..."
              className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <FilterButtons activeFilter={activeFilter} onFilterChange={setActiveFilter} />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Sincronizando agenda...</p>
          </div>
        ) : (
          <DataTable
            data={filteredAppointments}
            columns={columns}
            onEdit={openEdit}
            onDelete={handleDelete}
            pageSize={pageSize}
            // Pass pagination info for server-side pagination display
            defaultSortKey="start_datetime"
            defaultSortDirection="desc"
          />
        )}

        {/* Pagination info */}
        <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
          <span>
            Mostrando {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalItems)} de {totalItems} citas
          </span>
          <span>Página {currentPage} de {totalPages || 1}</span>
        </div>
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

          <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-indigo-900">
                <Sparkles size={16} />
                <span className="text-sm font-semibold">IA — Sugerir horarios disponibles</span>
              </div>
              <button
                type="button"
                onClick={askAvailableSlots}
                disabled={slotLoading}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-all disabled:opacity-60 flex items-center gap-1.5"
              >
                {slotLoading ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
                Buscar
              </button>
            </div>
            <p className="text-xs text-indigo-700/70">
              Usa la fecha del campo Inicio (arriba) y el doctor seleccionado. Cupos de 30 min.
            </p>
            {slotLoading && (
              <p className="text-xs text-indigo-700 flex items-center gap-1.5">
                <Loader2 className="animate-spin" size={12} /> Consultando disponibilidad en la agenda...
              </p>
            )}
            {slotError && <p className="text-xs text-red-600">{slotError}</p>}
            {availableSlots && availableSlots.length === 0 && (
              <p className="text-xs text-slate-500">No hay cupos libres para ese día.</p>
            )}
            {availableSlots && availableSlots.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {availableSlots.map((slot, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => applySlot(slot)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-indigo-200 text-indigo-800 hover:border-indigo-500 hover:bg-indigo-100 transition-all flex items-center gap-1.5"
                  >
                    <Check size={12} />
                    {fmtTime(slot.start)} — {fmtTime(slot.end)}
                  </button>
                ))}
              </div>
            )}
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

      <Modal
        isOpen={!!aiAppt}
        onClose={closeAiReschedule}
        title={aiAppt ? `Reagendar con IA — Cita #${aiAppt.id}` : 'Reagendar con IA'}
      >
        <div className="space-y-4">
          {aiAppt && (
            <div className="text-sm space-y-1 bg-slate-50 border border-slate-200 rounded-lg p-3">
              <p className="text-medical-textMain font-medium">
                {patientName(aiAppt.patient_id)} con {doctorName(aiAppt.doctor_id)}
              </p>
              <p className="text-slate-500">
                Actual: <span className="font-medium text-slate-700">{fmtTime(aiAppt.start_datetime)} — {fmtTime(aiAppt.end_datetime)}</span>
              </p>
            </div>
          )}

          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha preferida *</label>
              <input
                type="date"
                value={aiDate}
                onChange={(e) => setAiDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
            </div>
            <button
              type="button"
              onClick={askAiSuggestions}
              disabled={aiLoading || !aiDate}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 transition-all disabled:opacity-60 flex items-center gap-2"
            >
              {aiLoading ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
              Buscar horarios IA
            </button>
          </div>

          {aiError && <p className="text-sm text-red-600">{aiError}</p>}

          {aiSuggestions && aiSuggestions.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-medical-textMain">Horarios sugeridos por la IA:</p>
              {aiSuggestions.map((slot, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-3 hover:border-indigo-400 transition-all"
                >
                  <div>
                    <p className="text-sm font-medium text-medical-textMain">{fmtTime(slot.start)} — {fmtTime(slot.end)}</p>
                    <p className="text-xs text-slate-500">Compatibilidad: {Math.round(slot.score * 100)}%</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => applySuggestion(slot)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-all flex items-center gap-1.5"
                  >
                    <Check size={14} />
                    Usar
                  </button>
                </div>
              ))}
            </div>
          )}

          <p className="text-[10px] text-slate-400">
            La IA propone horarios libres según la agenda del médico. Verifica antes de confirmar.
          </p>
        </div>
      </Modal>
    </div>
  );
};

export default AppointmentsPage;