import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { doctorScheduleApi, DoctorSchedule, DoctorScheduleCreate, DAYS_OF_WEEK } from '../api/doctorScheduleApi';
import { doctorApi, Doctor } from '../api/doctorApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const DoctorSchedulePage: React.FC = () => {
  const [schedules, setSchedules] = useState<DoctorSchedule[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<DoctorSchedule | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<DoctorScheduleCreate>();

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [data, docs] = await Promise.all([
        doctorScheduleApi.getAll(),
        doctorApi.getAll(),
      ]);
      setSchedules(Array.isArray(data) ? data : []);
      setDoctors(Array.isArray(docs) ? docs : []);
    } catch (error) {
      toast.error('Error al cargar horarios');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const openCreate = () => {
    setEditingSchedule(null);
    reset({ doctor_id: '', day_of_week: 1, start_time: '09:00', end_time: '17:00', slot_duration_minutes: 30 });
    setIsModalOpen(true);
  };

  const openEdit = (schedule: DoctorSchedule) => {
    setEditingSchedule(schedule);
    reset({
      doctor_id: schedule.doctor_id,
      day_of_week: schedule.day_of_week,
      start_time: schedule.start_time.slice(0, 5),
      end_time: schedule.end_time.slice(0, 5),
      slot_duration_minutes: schedule.slot_duration_minutes,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: DoctorScheduleCreate) => {
    try {
      if (editingSchedule) {
        await doctorScheduleApi.update(editingSchedule.id, data);
        toast.success('Horario actualizado');
      } else {
        await doctorScheduleApi.create(data);
        toast.success('Horario creado');
      }
      setIsModalOpen(false);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (schedule: DoctorSchedule) => {
    if (!confirm(`¿Eliminar este horario?`)) return;
    try {
      await doctorScheduleApi.delete(schedule.id);
      toast.success('Horario eliminado');
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = schedules.filter(
    (s) => doctors.find(d => d.id === Number(s.doctor_id))?.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           doctors.find(d => d.id === Number(s.doctor_id))?.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           s.day_of_week.toString().includes(searchTerm)
  );

  const doctorName = (id: string) => {
    const d = doctors.find(d => d.id === Number(id));
    return d ? `Dr. ${d.first_name} ${d.last_name}` : id;
  };

  const dayName = (day: number) => {
    return DAYS_OF_WEEK.find(d => d.value === day)?.label || day.toString();
  };

  const columns = [
    { header: 'Doctor', accessor: (s: DoctorSchedule) => doctorName(s.doctor_id) },
    { header: 'Día', accessor: (s: DoctorSchedule) => dayName(s.day_of_week) },
    { header: 'Inicio', accessor: (s: DoctorSchedule) => s.start_time.slice(0, 5) },
    { header: 'Fin', accessor: (s: DoctorSchedule) => s.end_time.slice(0, 5) },
    { header: 'Duración (min)', accessor: (s: DoctorSchedule) => s.slot_duration_minutes.toString() },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Horarios de Doctores</h2>
          <p className="text-medical-textMuted">Gestión de horarios de atención médica</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nuevo Horario
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por doctor o día..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando horarios...</p>
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
        title={editingSchedule ? 'Editar Horario' : 'Nuevo Horario'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Doctor *</label>
            <select
              {...register('doctor_id', {
                required: 'Doctor requerido',
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Día de la semana *</label>
              <select
                {...register('day_of_week', {
                  required: 'Día requerido',
                  setValueAs: (v) => (v === '' || v === null ? undefined : Number(v))
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              >
                <option value="">Seleccionar día...</option>
                {DAYS_OF_WEEK.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
              {errors.day_of_week && <p className="text-red-500 text-xs mt-1">{errors.day_of_week.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Duración de cita (min) *</label>
              <select
                {...register('slot_duration_minutes', {
                  required: 'Duración requerida',
                  setValueAs: (v) => (v === '' || v === null ? undefined : Number(v))
                })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              >
                <option value="15">15 min</option>
                <option value="20">20 min</option>
                <option value="30">30 min</option>
                <option value="45">45 min</option>
                <option value="60">60 min</option>
              </select>
              {errors.slot_duration_minutes && <p className="text-red-500 text-xs mt-1">{errors.slot_duration_minutes.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Hora inicio *</label>
              <input
                type="time"
                {...register('start_time', { required: 'Hora inicio requerida' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.start_time && <p className="text-red-500 text-xs mt-1">{errors.start_time.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Hora fin *</label>
              <input
                type="time"
                {...register('end_time', { required: 'Hora fin requerida' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.end_time && <p className="text-red-500 text-xs mt-1">{errors.end_time.message}</p>}
            </div>
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
              {editingSchedule ? 'Actualizar' : 'Crear Horario'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default DoctorSchedulePage;
