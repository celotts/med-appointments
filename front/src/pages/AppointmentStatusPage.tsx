import React, { useState, useEffect } from 'react';
import { appointmentStatusApi, AppointmentStatus } from '../api/appointmentStatusApi';
import DataTable from '../components/common/DataTable';
import { Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const AppointmentStatusPage: React.FC = () => {
  const [statuses, setStatuses] = useState<AppointmentStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadStatuses = async () => {
    try {
      setIsLoading(true);
      const data = await appointmentStatusApi.getAll();
      setStatuses(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar estados de cita');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadStatuses(); }, []);

  const filtered = statuses.filter(
    (s) => s.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (s.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Código', accessor: 'code' as const },
    { header: 'Descripción', accessor: (s: AppointmentStatus) => s.description || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Estados de Cita</h2>
          <p className="text-medical-textMuted">Catálogo de estados (solo lectura - API de solo lectura)</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por código o descripción..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
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
      </div>
    </div>
  );
};

export default AppointmentStatusPage;
