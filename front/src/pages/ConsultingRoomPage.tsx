import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { consultingRoomApi, ConsultingRoom, ConsultingRoomCreate, ConsultingRoomUpdate } from '../api/consultingRoomApi';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { Plus, Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const ConsultingRoomPage: React.FC = () => {
  const [rooms, setRooms] = useState<ConsultingRoom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<ConsultingRoom | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ConsultingRoomCreate>();

  const loadRooms = async () => {
    try {
      setIsLoading(true);
      const data = await consultingRoomApi.getAll();
      setRooms(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar consultorios');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadRooms(); }, []);

  const openCreate = () => {
    setEditingRoom(null);
    reset({ name: '', address: '', phone_number: '' });
    setIsModalOpen(true);
  };

  const openEdit = (room: ConsultingRoom) => {
    setEditingRoom(room);
    reset({
      name: room.name,
      address: room.address || '',
      phone_number: room.phone_number || '',
    });
    setIsModalOpen(true);
  };

  const onSubmit = async (data: ConsultingRoomCreate | ConsultingRoomUpdate) => {
    try {
      if (editingRoom) {
        await consultingRoomApi.update(editingRoom.id, data);
        toast.success('Consultorio actualizado');
      } else {
        await consultingRoomApi.create(data);
        toast.success('Consultorio creado');
      }
      setIsModalOpen(false);
      loadRooms();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (room: ConsultingRoom) => {
    if (!confirm(`¿Eliminar el consultorio "${room.name}"?`)) return;
    try {
      await consultingRoomApi.delete(room.id);
      toast.success('Consultorio eliminado');
      loadRooms();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const filtered = rooms.filter(
    (r) => r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (r.address || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
           (r.phone_number || '').includes(searchTerm)
  );

  const columns = [
    { header: 'Nombre', accessor: 'name' as const },
    { header: 'Dirección', accessor: (r: ConsultingRoom) => r.address || '-' },
    { header: 'Teléfono', accessor: (r: ConsultingRoom) => r.phone_number || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Consultorios</h2>
          <p className="text-medical-textMuted">Gestión de consultorios médicos</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <Plus size={18} />
          Nuevo Consultorio
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
            <p className="text-sm">Cargando consultorios...</p>
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
        title={editingRoom ? 'Editar Consultorio' : 'Nuevo Consultorio'}
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

          <div>
            <label className="block text-sm font-medium text-medical-textMain mb-1">Teléfono</label>
            <input
              {...register('phone_number')}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none text-sm transition-all"
              placeholder="Teléfono opcional..."
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
              {editingRoom ? 'Actualizar' : 'Guardar Consultorio'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ConsultingRoomPage;
