import React, { useState, useEffect } from 'react';
import { reportsApi, DashboardSummary } from '../api/reportsApi';
import { Users, Calendar, CheckCircle, Clock, XCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

const StatCard = ({ title, value, icon: Icon, color, loading }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
    <div className={`p-3 rounded-xl ${color} text-white`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-sm text-medical-textMuted font-medium">{title}</p>
      {loading ? (
        <div className="h-7 w-16 bg-slate-200 rounded animate-pulse mt-1" />
      ) : (
        <h3 className="text-2xl font-bold text-medical-textMain">{value}</h3>
      )}
    </div>
  </div>
);

const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await reportsApi.getDashboardSummary();
        setSummary(data);
      } catch (error) {
        toast.error('Error al cargar dashboard');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-medical-textMain">Panel Clinico</h2>
        <p className="text-medical-textMuted">Resumen general de la clinica</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard title="Total Pacientes" value={summary?.total_patients ?? 0} icon={Users} color="bg-blue-500" loading={loading} />
        <StatCard title="Total Doctores" value={summary?.total_doctors ?? 0} icon={Users} color="bg-indigo-500" loading={loading} />
        <StatCard title="Citas Hoy" value={summary?.total_appointments_today ?? 0} icon={Calendar} color="bg-emerald-500" loading={loading} />
        <StatCard title="Completadas Hoy" value={summary?.appointments_completed_today ?? 0} icon={CheckCircle} color="bg-green-500" loading={loading} />
        <StatCard title="Pendientes" value={summary?.appointments_pending ?? 0} icon={Clock} color="bg-amber-500" loading={loading} />
        <StatCard title="Canceladas Mes" value={summary?.appointments_cancelled_month ?? 0} icon={XCircle} color="bg-red-500" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold mb-2 text-medical-textMain">Esta Semana</h3>
          <p className="text-3xl font-bold text-medical-primary">{summary?.total_appointments_week ?? 0}</p>
          <p className="text-sm text-medical-textMuted mt-1">citas programadas</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold mb-2 text-medical-textMain">Este Mes</h3>
          <p className="text-3xl font-bold text-medical-primary">{summary?.total_appointments_month ?? 0}</p>
          <p className="text-sm text-medical-textMuted mt-1">citas totales</p>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
