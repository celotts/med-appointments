import React, { useState, useEffect } from 'react';
import { Users, Calendar, CheckCircle, AlertCircle, TrendingUp, FileText } from 'lucide-react';
import { reportsApi, DashboardSummary } from '../api/reportsApi';
import { toast } from 'react-hot-toast';

const StatCard = ({ title, value, icon: Icon, color }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4 transition-all hover:shadow-md">
    <div className={`p-3 rounded-xl ${color} text-white`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-sm text-medical-textMuted font-medium">{title}</p>
      <h3 className="text-2xl font-bold text-medical-textMain">{value}</h3>
    </div>
  </div>
);

const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const data = await reportsApi.getDashboardSummary();
      setSummary(data);
    } catch (error: any) {
      console.error('Dashboard fetch error:', error);
      toast.error('Error al cargar las estadísticas del panel');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center py-20 text-slate-400">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medical-primary mb-4"></div>
        <p className="text-sm">Sincronizando panel de control...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Panel de Control</h2>
          <p className="text-medical-textMuted">Resumen general de la actividad clínica</p>
        </div>
        <button
          onClick={loadDashboardData}
          className="p-2 text-slate-400 hover:text-medical-primary transition-colors"
          title="Actualizar datos"
        >
          <TrendingUp size={20} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Pacientes"
          value={summary?.total_patients || 0}
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          title="Citas Hoy"
          value={summary?.total_appointments_today || 0}
          icon={Calendar}
          color="bg-indigo-500"
        />
        <StatCard
          title="Completadas"
          value={summary?.appointments_completed_today || 0}
          icon={CheckCircle}
          color="bg-emerald-500"
        />
        <StatCard
          title="Pendientes"
          value={summary?.appointments_pending || 0}
          icon={AlertCircle}
          color="bg-amber-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-medical-textMain">Actividad Reciente</h3>
            <button className="text-sm text-medical-secondary hover:underline font-medium">Ver todas</button>
          </div>
          <div className="space-y-4">
            {summary ? (
              <div className="text-center py-10 text-slate-400 italic">
                No hay actividad reciente para mostrar en este momento.
              </div>
            ) : (
              <div className="text-center py-10 text-slate-400 italic">Cargando...</div>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 mb-6">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <FileText size={20} />
            </div>
            <h3 className="text-lg font-semibold text-medical-textMain">Insights de IA</h3>
          </div>
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
            <p className="text-sm text-blue-800 leading-relaxed italic">
              "Basado en los datos actuales, la tasa de inasistencia ha disminuido un 5% esta semana. Se recomienda mantener el sistema de recordatorios activos."
            </p>
          </div>
          <div className="mt-6 space-y-3">
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
              <span className="text-xs text-slate-500">Tasa de No-Show</span>
              <span className="text-xs font-bold text-emerald-600">12% ↓</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
              <span className="text-xs text-slate-500">Carga de Trabajo</span>
              <span className="text-xs font-bold text-amber-600">Alta</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
