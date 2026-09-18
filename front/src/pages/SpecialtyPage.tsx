import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { specialtyApi, Specialty } from '../api/specialtyApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const SpecialtyPage: React.FC = () => {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSpecialty, setEditingSpecialty] = useState<Specialty | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<Specialty>();

  const loadSpecialties = async () => {
    try {
      setIsLoading(true);
      const data = await specialtyApi.getAll();
      setSpecialties(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar especialidades');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadSpecialties(); }, []);

  const openCreate = () => {
    setEditingSpecialty(null);
    reset({ name: '', description: '' });
    setIsModalOpen(true);
  };

  const openEdit = (specialty: Specialty) => {
    setEditingSpecialty(specialty);
    reset({
      name: specialty.name,
      description: specialty.description || '',
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: Specialty) => {
    try {
      if (editingSpecialty) {
        await specialtyApi.update(editingSpecialty.id, data);
        toast.success('Especialidad actualizada');
      } else {
        await specialtyApi.create(data);
        toast.success('Especialidad creada');
      }
      setIsModalOpen(false);
      loadSpecialties();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (specialty: Specialty) => {
    if (!confirm(`¿Eliminar la especialidad "${specialty.name}"?`)) return;
    try {
      await specialtyApi.delete(specialty.id);
      toast.success('Especialidad eliminada');
      loadSpecialties();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = specialties.filter(
    (s) => s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (s.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Nombre', accessor: 'name' as const },
    { header: 'Descripción', accessor: (s: Specialty) => s.description || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Catálogo de Especialidades</h2>
          <p className="text-medical-textMuted">Gestión de especialidades médicas</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nueva Especialidad
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por nombre o descripción..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando especialidades...</p>
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
        title={editingSpecialty ? 'Editar Especialidad' : 'Nueva Especialidad'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Nombre *</label>
            <input
              {...register('name', {
                required: 'El nombre es requerido',
                validate: (value) =>
                  specialties.some(
                    (s) =>
                      s.name.toLowerCase() === value.trim().toLowerCase() &&
                      s.id !== editingSpecialty?.id
                  )
                    ? 'Ya existe una especialidad con este nombre'
                    : true
              })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
            />
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Descripción</label>
            <textarea
              {...register('description')}
              rows={3}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              placeholder="Descripción opcional..."
            />
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
              {editingSpecialty ? 'Actualizar' : 'Guardar Especialidad'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default SpecialtyPage;
