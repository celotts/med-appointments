import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { doctorApi, Doctor, DoctorCreate } from '../api/doctorApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const DoctorsPage: React.FC = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<DoctorCreate>();

  const loadDoctors = async () => {
    try {
      setIsLoading(true);
      const data = await doctorApi.getAll();
      setDoctors(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar doctores');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadDoctors(); }, []);

  const openCreate = () => {
    setEditingDoctor(null);
    reset({ first_name: '', last_name: '', email: '', phone: '', license_number: '', specialty_id: 0 });
    setIsModalOpen(true);
  };

  const openEdit = (doctor: Doctor) => {
    setEditingDoctor(doctor);
    reset({
      first_name: doctor.first_name,
      last_name: doctor.last_name,
      email: doctor.email,
      phone: doctor.phone,
      license_number: doctor.license_number,
      specialty_id: doctor.specialty_id,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: DoctorCreate) => {
    try {
      if (editingDoctor) {
        await doctorApi.update(editingDoctor.id, data);
        toast.success('Doctor actualizado');
      } else {
        await doctorApi.create(data);
        toast.success('Doctor creado');
      }
      setIsModalOpen(false);
      loadDoctors();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (doctor: Doctor) => {
    if (!confirm(`¿Eliminar al Dr. ${doctor.first_name} ${doctor.last_name}?`)) return;
    try {
      await doctorApi.delete(doctor.id);
      toast.success('Doctor eliminado');
      loadDoctors();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = doctors.filter(
    (d) =>
      d.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Nombre', accessor: (d: Doctor) => `Dr. ${d.first_name} ${d.last_name}` },
    { header: 'Email', accessor: 'email' as const },
    { header: 'Telefono', accessor: 'phone' as const },
    { header: 'Licencia', accessor: 'license_number' as const },
    { header: 'Especialidad', accessor: (d: Doctor) => d.specialty_name || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Directorio de Médicos</h2>
          <p className="text-medical-textMuted">Registro de personal médico y especialidades</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nuevo Doctor
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
            <p className="text-sm">Cargando doctores...</p>
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
        title={editingDoctor ? 'Editar Doctor' : 'Nuevo Doctor'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Nombre *</label>
              <input
                {...register('first_name', { required: 'Nombre requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.first_name && <p className="text-red-500 text-xs mt-1">{errors.first_name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Apellido *</label>
              <input
                {...register('last_name', { required: 'Apellido requerido' })}
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
                required: 'Email requerido',
                pattern: { value: /^\S+@\S+$/i, message: 'Email inválido' }
              })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Teléfono *</label>
              <input
                {...register('phone', { required: 'Teléfono requerido' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">No. Licencia *</label>
              <input
                {...register('license_number', { required: 'Licencia requerida' })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              />
              {errors.license_number && <p className="text-red-500 text-xs mt-1">{errors.license_number.message}</p>}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">ID Especialidad *</label>
            <input
              type="number"
              {...register('specialty_id', { required: 'Especialidad requerida', valueAsNumber: true })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
            />
            {errors.specialty_id && <p className="text-red-500 text-xs mt-1">{errors.specialty_id.message}</p>}
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
              {editingDoctor ? 'Actualizar' : 'Guardar Doctor'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default DoctorsPage;
