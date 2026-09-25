import React, { useState, useEffect } from 'react';
import { appointmentApi, AppointmentStatus } from '../api/appointmentApi';
import DataTable, { Column } from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2, Edit, Trash2, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useForm } from 'react-hook-form';

const AppointmentStatusPage: React.FC = () => {
  const [statuses, setStatuses] = useState<AppointmentStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStatus, setEditingStatus] = useState<AppointmentStatus | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<AppointmentStatus | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<AppointmentStatus>();

  const loadStatuses = async () => {
    try {
      setIsLoading(true);
      const data = await appointmentApi.getStatuses();
      setStatuses(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar estados');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadStatuses(); }, []);

  const filtered = statuses.filter(
    (s) => s.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
           s.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const openCreate = () => {
    setEditingStatus(null);
    reset({ code: '', description: '' });
    setIsModalOpen(true);
  };

  const openEdit = (status: AppointmentStatus) => {
    setEditingStatus(status);
    reset({ code: status.code, description: status.description || '' });
    setIsModalOpen(true);
  };

  const confirmDelete = (status: AppointmentStatus) => {
    setDeleteConfirm(status);
  };

  const onSubmit = async (data: AppointmentStatus) => {
    try {
      if (editingStatus) {
        await appointmentApi.updateStatus(editingStatus.id, data);
        toast.success('Estado actualizado correctamente');
      } else {
        await appointmentApi.createStatus(data);
        toast.success('Estado creado correctamente');
      }
      setIsModalOpen(false);
      loadStatuses();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await appointmentApi.deleteStatus(deleteConfirm.id);
      toast.success('Estado eliminado correctamente');
      setDeleteConfirm(null);
      loadStatuses();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
      setDeleteConfirm(null);
    }
  };

  const columns: Column<AppointmentStatus>[] = [
    {
      header: 'Código',
      accessor: 'code',
      sortable: true,
    },
    {
      header: 'Descripción',
      accessor: (s: AppointmentStatus) => (
        <span className="text-slate-600 truncate max-w-xs block">{s.description || '-'}</span>
      ),
      sortable: true,
    },
    {
      header: 'Acciones',
      accessor: (s: AppointmentStatus) => (
        <div className="flex items-center justify-center gap-1">
          <button
            onClick={() => openEdit(s)}
            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Editar"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={() => confirmDelete(s)}
            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Eliminar"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Estados de Cita</h2>
          <p className="text-medical-textMuted">Mantenimiento de catálogo de estados (CRUD completo)</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all duration-200 text-sm font-semibold"
        >
          <Plus size={20} />
          Nuevo Estado
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por código o descripción..."
            className="w-full pl-10 pr-4 py-2.5 border-2 border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-primary focus:border-transparent outline-none text-sm transition-all hover:border-slate-300 bg-white"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando estados...</p>
          </div>
        ) : (
          <DataTable
            data={filtered}
            columns={columns}
          />
        )}

        {statuses.length === 0 && !isLoading && (
          <div className="text-center py-12 text-slate-400">
            <AlertCircle className="mx-auto mb-2" size={48} />
            <p className="text-sm">No hay estados registrados</p>
          </div>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingStatus ? 'Editar Estado' : 'Nuevo Estado'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Código *</label>
            <input
              {...register('code', { required: 'Código requerido' })}
              disabled={!!editingStatus}
              className="w-full px-3 py-2 border-2 border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-primary focus:border-transparent outline-none text-sm transition-all hover:border-slate-300 bg-white disabled:bg-slate-50 disabled:text-slate-500"
              placeholder="Ej: PENDIENTE"
              maxLength={50}
            />
            {errors.code && <p className="text-red-500 text-xs mt-1">{errors.code.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Descripción</label>
            <textarea
              {...register('description')}
              rows={3}
              className="w-full px-3 py-2 border-2 border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-primary focus:border-transparent outline-none text-sm transition-all hover:border-slate-300 bg-white"
              placeholder="Descripción del estado..."
              maxLength={255}
            />
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-800 rounded-xl transition-all duration-200 border border-slate-200 hover:border-slate-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 text-sm font-semibold text-white rounded-xl transition-all duration-200 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:hover:from-blue-600 disabled:hover:to-blue-700 flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="animate-spin" size={18} />}
              {editingStatus ? 'Guardar Cambios' : 'Crear Estado'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Confirmar Eliminación"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-slate-600">
            <AlertCircle className="text-red-500" size={24} />
            <p>¿Eliminar el estado <strong className="text-medical-textMain">{deleteConfirm?.code}</strong>?</p>
          </div>
          {deleteConfirm?.description && (
            <p className="text-sm text-slate-500">{deleteConfirm.description}</p>
          )}
          <p className="text-sm text-amber-600 flex items-center gap-1.5">
            <AlertCircle size={14} />
            Esta acción no se puede deshacer. No se puede eliminar si hay citas usando este estado.
          </p>
          <div className="pt-4 flex justify-end gap-3">
            <button
              onClick={() => setDeleteConfirm(null)}
              className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-800 rounded-xl transition-all duration-200 border border-slate-200 hover:border-slate-300"
            >
              Cancelar
            </button>
            <button
              onClick={handleDelete}
              disabled={isSubmitting}
              className="px-5 py-2.5 text-sm font-semibold text-white rounded-xl transition-all duration-200 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 focus:ring-4 focus:ring-red-500/30 focus:ring-offset-2 shadow-lg shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/40 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Trash2 size={16} />
              Eliminar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AppointmentStatusPage;