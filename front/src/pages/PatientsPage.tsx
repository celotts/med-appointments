import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { patientApi, Patient, PatientCreate } from '../api/patientApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import DatePicker from 'react-datepicker';
import { parse } from 'date-fns';
import { format } from 'date-fns';
import { Plus, Search, Loader2 } from 'lucide-react';
import 'react-datepicker/dist/react-datepicker.css';
import { toast } from 'react-hot-toast';

const PatientsPage: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<PatientCreate>();

  const loadPatients = async () => {
    try {
      setIsLoading(true);
      const data = await patientApi.getAll();
      setPatients(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar los pacientes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPatients();
  }, []);

  const openCreate = () => {
    setEditingPatient(null);
    reset({
      first_name: '',
      last_name: '',
      birth_date: '',
      email: '',
      phone: ''
    });
    setIsModalOpen(true);
  };

  const openEdit = (patient: Patient) => {
    setEditingPatient(patient);
    reset({
      first_name: patient.first_name,
      last_name: patient.last_name,
      birth_date: patient.birth_date,
      email: patient.email,
      phone: patient.phone,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: PatientCreate) => {
    try {
      if (editingPatient) {
        await patientApi.update(editingPatient.id, data);
        toast.success('Paciente actualizado correctamente');
      } else {
        await patientApi.create(data);
        toast.success('Paciente registrado correctamente');
      }
      setIsModalOpen(false);
      loadPatients();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar el paciente');
    }
  };

  const handleDelete = async (patient: Patient) => {
    if (!confirm(`¿Estás seguro de eliminar al paciente ${patient.first_name} ${patient.last_name}?`)) return;
    try {
      await patientApi.delete(patient.id);
      toast.success('Paciente eliminado correctamente');
      loadPatients();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar el paciente');
    }
  };

  const filtered = patients.filter(
    (p) =>
      p.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Nombre Completo', accessor: (p: Patient) => `${p.first_name} ${p.last_name}` },
    { header: 'Email', accessor: 'email' as const },
    { header: 'Teléfono', accessor: 'phone' as const },
    { header: 'Fecha Nac.', accessor: 'birth_date' as const },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Directorio de Pacientes</h2>
          <p className="text-medical-textMuted">Gestión de expedientes y datos de contacto</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nuevo Paciente
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por nombre o email..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando pacientes...</p>
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
        title={editingPatient ? 'Editar Paciente' : 'Nuevo Paciente'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Nombre *</label>
              <input
                {...register('first_name', { required: 'El nombre es requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.first_name && <p className="text-red-500 text-xs mt-1">{errors.first_name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Apellido *</label>
              <input
                {...register('last_name', { required: 'El apellido es requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.last_name && <p className="text-red-500 text-xs mt-1">{errors.last_name.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Email *</label>
            <input
              type="email"
              {...register('email', {
                required: 'El email es requerido',
                pattern: { value: /^\S+@\S+$/i, message: 'Email inválido' }
              })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha de Nacimiento *</label>
              <DatePicker
                selected={editingPatient ? parse(editingPatient.birth_date, 'yyyy-MM-dd', new Date()) : undefined}
                onChange={(date: any) => {
                  if (date) {
                    const formattedDate = format(date, 'yyyy-MM-dd');
                    reset({
                      first_name: editingPatient?.first_name,
                      last_name: editingPatient?.last_name,
                      birth_date: formattedDate,
                      email: editingPatient?.email,
                      phone: editingPatient?.phone,
                    });
                    setEditingPatient(prev => prev ? { ...prev, birth_date: formattedDate } : null);
                  }
                }}
                dateFormat="yyyy-MM-dd"
                required={true}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.birth_date && <p className="text-red-500 text-xs mt-1">{errors.birth_date.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Teléfono *</label>
              <input
                {...register('phone', { required: 'Teléfono requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>}
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
              {editingPatient ? 'Actualizar' : 'Guardar Paciente'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default PatientsPage;
