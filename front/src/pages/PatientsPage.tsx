import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { patientApi, Patient, PatientCreate } from '../api/patientApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { TableSkeleton } from '../components/common/Skeleton';
import { Plus, Search } from 'lucide-react';
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
      toast.error('Error al cargar pacientes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadPatients(); }, []);

  const openCreate = () => {
    setEditingPatient(null);
    reset({ first_name: '', last_name: '', email: '', phone: '', birth_date: '' });
    setIsModalOpen(true);
  };

  const openEdit = (patient: Patient) => {
    setEditingPatient(patient);
    reset({
      first_name: patient.first_name,
      last_name: patient.last_name,
      email: patient.email,
      phone: patient.phone,
      birth_date: patient.birth_date,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: PatientCreate) => {
    try {
      if (editingPatient) {
        await patientApi.update(editingPatient.id, data);
        toast.success('Paciente actualizado');
      } else {
        await patientApi.create(data);
        toast.success('Paciente creado');
      }
      setIsModalOpen(false);
      loadPatients();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (patient: Patient) => {
    if (!confirm(`¿Eliminar a ${patient.first_name} ${patient.last_name}?`)) return;
    try {
      await patientApi.delete(patient.id);
      toast.success('Paciente eliminado');
      loadPatients();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = patients.filter(
    (p) =>
      p.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Nombre', accessor: (p: Patient) => `${p.first_name} ${p.last_name}` },
    { header: 'Email', accessor: 'email' as const },
    { header: 'Telefono', accessor: 'phone' as const },
    { header: 'Fecha Nac.', accessor: (p: Patient) => p.birth_date || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Pacientes</h2>
          <p className="text-medical-textMuted">Directorio de pacientes registrados</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium"
        >
          <Plus size={18} />
          Nuevo Paciente
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por nombre o email..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <TableSkeleton rows={5} cols={4} />
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
                {...register('first_name', { required: 'Nombre requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              />
              {errors.first_name && <p className="text-red-500 text-xs mt-1">{errors.first_name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Apellido *</label>
              <input
                {...register('last_name', { required: 'Apellido requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              />
              {errors.last_name && <p className="text-red-500 text-xs mt-1">{errors.last_name.message}</p>}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Email *</label>
            <input
              type="email"
              {...register('email', {
                required: 'Email requerido',
                pattern: { value: /^\S+@\S+$/i, message: 'Email invalido' }
              })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Telefono *</label>
              <input
                {...register('phone', { required: 'Telefono requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              />
              {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha Nacimiento *</label>
              <input
                type="date"
                {...register('birth_date', { required: 'Fecha requerida' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm"
              />
              {errors.birth_date && <p className="text-red-500 text-xs mt-1">{errors.birth_date.message}</p>}
            </div>
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
              {isSubmitting ? 'Guardando...' : editingPatient ? 'Actualizar' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default PatientsPage;
