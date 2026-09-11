import React, { useState } from 'react';
import { User, Lock, Globe, Bell, ShieldCheck, Save } from 'lucide-react';
import { toast } from 'react-hot-toast';

const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'app'>('profile');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast.success('Configuración guardada correctamente');
  };

  const tabs = [
    { id: 'profile', label: 'Perfil', icon: User },
    { id: 'security', label: 'Seguridad', icon: ShieldCheck },
    { id: 'app', label: 'Aplicación', icon: Globe },
  ];

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">Configuración</h2>
          <p className="text-medical-textMuted">Gestiona tu cuenta y preferencias del sistema</p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-64 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-medical-primary text-white shadow-md'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
              }`}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-medical-textMain mb-4">Información Personal</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-600">Nombre Completo</label>
                  <input
                    type="text"
                    defaultValue="Dr. Carlos Lott"
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-600">Correo Electrónico</label>
                  <input
                    type="email"
                    defaultValue="admin@medapi.com"
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-600">Teléfono</label>
                  <input
                    type="text"
                    defaultValue="+1 234 567 890"
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-600">Especialidad</label>
                  <input
                    type="text"
                    defaultValue="Medicina General"
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-medical-secondary outline-none transition-all"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-8">
              <h3 className="text-lg font-semibold text-medical-textMain mb-4">Seguridad de la Cuenta</h3>
              <div className="space-y-6">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-4">
                  <div className="flex items-center gap-3 text-slate-700 font-medium">
                    <Lock size={18} />
                    <span>Cambiar Contraseña</span>
                  </div>
                  <div className="space-y-4 pl-7">
                    <div className="space-y-2">
                      <label className="block text-xs font-medium text-slate-500">Contraseña Actual</label>
                      <input
                        type="password"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-medical-secondary text-sm"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="block text-xs font-medium text-slate-500">Nueva Contraseña</label>
                        <input
                        type="password"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-medical-secondary text-sm"
                      />
                      </div>
                      <div className="space-y-2">
                        <label className="block text-xs font-medium text-slate-500">Confirmar Nueva</label>
                        <input
                        type="password"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-medical-secondary text-sm"
                      />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="flex items-center gap-3">
                    <Bell size={18} className="text-slate-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-700">Notificaciones de Citas</p>
                      <p className="text-xs text-slate-500">Recibir alertas cuando se programen nuevas citas</p>
                    </div>
                  </div>
                  <input type="checkbox" className="w-4 h-4 text-medical-primary focus:ring-medical-primary border-slate-300 rounded" defaultChecked />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'app' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-medical-textMain mb-4">Preferencias del Sistema</h3>
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="flex items-center gap-3">
                    <Globe size={18} className="text-slate-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-700">Idioma de la Interfaz</p>
                      <p className="text-xs text-slate-500">Cambiar el idioma de navegación y formularios</p>
                    </div>
                  </div>
                  <select className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-medical-secondary bg-white">
                    <option value="es">Español</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className="p-1 bg-slate-200 rounded">
                      <div className="w-4 h-4 bg-white rounded-full border border-slate-300"></div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-700">Modo de Visualización</p>
                      <p className="text-xs text-slate-500">Alternar entre modo claro y oscuro (Próximamente)</p>
                    </div>
                  </div>
                  <button disabled className="px-3 py-1.5 bg-slate-200 text-slate-400 rounded-lg text-xs font-medium cursor-not-allowed">
                    Próximamente
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="mt-8 pt-6 border-t border-slate-100 flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-6 py-2.5 bg-medical-primary text-white rounded-lg hover:bg-blue-800 transition-all text-sm font-medium shadow-sm disabled:opacity-70"
            >
              {isSaving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
              Guardar Cambios
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Loader2 = ({ className, size }: any) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size || 24}
    height={size || 24}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);

export default SettingsPage;
