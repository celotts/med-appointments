import React, { useState, useEffect } from 'react';
import { branchApi, Branch } from '../api/branchApi';
import DataTable from '../components/common/DataTable';
import { Search, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

const BranchPage: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

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

  const filtered = branches.filter(
    (b) => b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (b.address || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
           (b.phone || '').includes(searchTerm)
  );

  const columns = [
    { header: 'Nombre', accessor: 'name' as const },
    { header: 'Dirección', accessor: (b: Branch) => b.address || '-' },
    { header: 'Teléfono', accessor: (b: Branch) => b.phone || '-' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Sucursales</h2>
          <p className="text-medical-textMuted">Listado de sedes (solo lectura - API de solo lectura)</p>
        </div>
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
          />
        )}
      </div>
    </div>
  );
};

export default BranchPage;
