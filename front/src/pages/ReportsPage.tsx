import React, { useState, useEffect } from 'react';
import { FileText, Download, TrendingUp, Users, AlertCircle } from 'lucide-react';
import { reportsApi } from '../api/reportsApi';
import { toast } from 'react-hot-toast';
import DataTable from '../components/common/DataTable';

const ReportsPage: React.FC = () => {
  const [apptsByDoctor, setApptsByDoctor] = useState<any[]>([]);
  const [noShowRate, setNoShowRate] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);

  const loadReports = async () => {
    try {
      setIsLoading(true);
      const [byDoctor, nsRate] = await Promise.all([
        reportsApi.getAppointmentsByDoctor(),
        reportsApi.getNoShowRate(),
      ]);
      setApptsByDoctor(Array.isArray(byDoctor) ? byDoctor : []);
      setNoShowRate(typeof nsRate === 'number' ? nsRate : (nsRate as any)?.rate || 0);
    } catch (error) {
      toast.error('Error al cargar los reportes analíticos');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const exportToCSV = (data: any[], filename: string) => {
    if (!data || data.length === 0) return;
    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => Object.values(row).join(',')).join('\\n');
    const csvContent = `data:text/csv;charset=utf-8,${headers}\\n${rows}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Exportación iniciada');
  };

  const columns = [
    {
      header: 'Doctor',
      accessor: (d: any) => <span className="font-medium text-medical-textMain">{d.doctor_name || 'Desconocido'}</span>
    },
    {
      header: 'Citas Totales',
      accessor: (d: any) => <span className="text-slate-600">{d.count}</span>
    },
    {
      header: 'Eficiencia',
      accessor: (d: any) => (
        <div className="flex items-center gap-2">
          <div className="w-full bg-slate-200 rounded-full h-2 max-w-[100px]">
            <div
              className="bg-medical-primary h-2 rounded-full"
              style={{ width: `${Math.min(100, (d.count / 50) * 100)}%` }}
            ></div>
          </div>
          <span className="text-xs text-slate-500">{d.count}</span>
        </div>
      )
    }
  ];

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center py-20 text-slate-400">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-primary mb-4"></div>
        <p className="text-sm">Generando reportes clínicos...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Reportes y Analítica</h2>
          <p className="text-medical-textMuted">Análisis de rendimiento y métricas operativas</p>
        </div>
        <button
          onClick={() => exportToCSV(apptsByDoctor, 'reporte_doctores')}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors text-sm font-medium shadow-sm"
        >
          <Download size={18} />
          Exportar CSV
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-start gap-4">
          <div className="p-3 bg-amber-100 text-amber-600 rounded-xl">
            <AlertCircle size={24} />
          </div>
          <div>
            <p className="text-sm text-medical-textMuted font-medium">Tasa de No-Show</p>
            <h3 className="text-2xl font-bold text-medical-textMain">{noShowRate.toFixed(1)}%</h3>
            <p className="text-xs text-amber-600 mt-1 font-medium">Requiere atención</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-start gap-4">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl">
            <Users size={24} />
          </div>
          <div>
            <p className="text-sm text-medical-textMuted font-medium">Promedio Pacientes</p>
            <h3 className="text-2xl font-bold text-medical-textMain">
              {(apptsByDoctor.reduce((acc, curr) => acc + curr.count, 0) / (apptsByDoctor.length || 1)).toFixed(1)}
            </h3>
            <p className="text-xs text-slate-400 mt-1">Por profesional</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-start gap-4">
          <div className="p-3 bg-emerald-100 text-emerald-600 rounded-xl">
            <TrendingUp size={24} />
          </div>
          <div>
            <p className="text-sm text-medical-textMuted font-medium">Crecimiento Mensual</p>
            <h3 className="text-2xl font-bold text-medical-textMain">+12.5%</h3>
            <p className="text-xs text-emerald-600 mt-1 font-medium">Tendencia positiva</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-6">
          <FileText size={20} className="text-medical-primary" />
          <h3 className="text-lg font-semibold text-medical-textMain">Distribución de Citas por Doctor</h3>
        </div>
        <DataTable
          data={apptsByDoctor}
          columns={columns}
        />
      </div>
    </div>
  );
};

export default ReportsPage;
