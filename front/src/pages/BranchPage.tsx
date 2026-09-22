import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { branchApi, Branch, BranchCreate } from '../api/branchApi';
import DataTable, { Column } from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const BranchPage: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<BranchCreate>();

  const loadBranches = async () => {
    try {
      setIsLoading(true);
      const data = await branchApi.getAll();
      setBranches(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar sucursales');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadBranches(); }, []);

  const openCreate = () => {
    setEditingBranch(null);
    reset({ name: '', address: '', phone: '', email: '', is_active: true });
    setIsModalOpen(true);
  };

  const openEdit = (branch: Branch) => {
    setEditingBranch(branch);
    reset({
      name: branch.name,
      address: branch.address || '',
      phone: branch.phone || '',
      email: branch.email || '',
      is_active: branch.is_active ?? true,
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: BranchCreate) => {
    try {
      if (editingBranch) {
        await branchApi.update(editingBranch.id, data);
        toast.success('Sucursal actualizada');
      } else {
        await branchApi.create(data);
        toast.success('Sucursal creada');
      }
      setIsModalOpen(false);
      loadBranches();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (branch: Branch) => {
    if (!confirm(`¿Eliminar la sucursal "${branch.name}"?`)) return;
    try {
      await branchApi.delete(branch.id);
      toast.success('Sucursal eliminada');
      loadBranches();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = branches.filter(
    (b) => b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (b.address || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
           (b.phone || '').includes(searchTerm)
  );

  const columns: Column<Branch>[] = [
    { header: 'Nombre', accessor: (b: Branch) => (
        <span className="font-medium text-medical-textMain">{b.name}</span>
      ), sortable: true },
    { header: 'Dirección', accessor: (b: Branch) => b.address || '-' },
    { header: 'Teléfono', accessor: (b: Branch) => b.phone || '-' },
    { header: 'Estado', accessor: (b: Branch) => (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${b.is_active ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
          {b.is_active ? 'Activa' : 'Inactiva'}
        </span>
      ), sortable: true },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Sucursales</h2>
          <p className="text-medical-textMuted">Gestión de sedes y sucursales</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nueva Sucursal
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por nombre, dirección o teléfono..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando sucursales...</p>
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
        title={editingBranch ? 'Editar Sucursal' : 'Nueva Sucursal'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Nombre *</label>
            <input
              {...register('name', { required: 'El nombre es requerido' })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
            />
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Dirección</label>
            <input
              {...register('address')}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              placeholder="Dirección opcional..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Teléfono</label>
              <input
                {...register('phone')}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
                placeholder="Teléfono opcional..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1">Correo</label>
              <input
                type="email"
                {...register('email')}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
                placeholder="Correo opcional..."
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-medical-textMain">
            <input type="checkbox" {...register('is_active')} className="w-4 h-4 accent-blue-600" />
            Sucursal activa
          </label>

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
              {editingBranch ? 'Actualizar' : 'Guardar Sucursal'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default BranchPage;