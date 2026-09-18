import React, { useState, useEffect } from 'react';
import { roleApi, Role } from '../api/roleApi';
import DataTable from '../components/common/DataTable';
import { Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const RolePage: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadRoles = async () => {
    try {
      setIsLoading(true);
      const data = await roleApi.getAll();
      setRoles(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error('Error al cargar roles');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadRoles(); }, []);

  const filtered = roles.filter(
    (r) => r.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'Nombre', accessor: 'name' as const },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Roles del Sistema</h2>
          <p className="text-medical-textMuted">Listado de roles (solo lectura - API de solo lectura)</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
        <div className="relative max-w-sm mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Buscar por nombre..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="animate-spin mb-2" size={32} />
            <p className="text-sm">Cargando roles...</p>
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

export default RolePage;
