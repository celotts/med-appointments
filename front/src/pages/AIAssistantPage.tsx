import React, { useState } from 'react';
import { Calendar, Clock, AlertTriangle, RefreshCw, Search, CheckCircle } from 'lucide-react';
import { medasistApi, RescheduleSuggestion, AvailabilitySlot } from '../api/medasistApi';
import toast from 'react-hot-toast';

type Tab = 'reschedule' | 'availability' | 'followup';

const AIAssistantPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('reschedule');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-medical-primary text-white rounded-lg">
          <span className="font-bold">MedAssist IA</span>
        </div>
        <h2 className="text-2xl font-bold text-medical-textMain">Asistente de Agenda</h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('reschedule')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'reschedule'
              ? 'bg-medical-primary text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <RefreshCw size={16} />
          Reagendar
        </button>
        <button
          onClick={() => setActiveTab('availability')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'availability'
              ? 'bg-medical-primary text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Clock size={16} />
          Disponibilidad
        </button>
        <button
          onClick={() => setActiveTab('followup')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'followup'
              ? 'bg-medical-primary text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Calendar size={16} />
          Seguimiento
        </button>
      </div>

      {/* Content */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        {activeTab === 'reschedule' && <RescheduleTab />}
        {activeTab === 'availability' && <AvailabilityTab />}
        {activeTab === 'followup' && <FollowUpTab />}
      </div>
    </div>
  );
};

// ─── Reagendar Tab ──────────────────────────────────────────────────────
const RescheduleTab: React.FC = () => {
  const [appointmentId, setAppointmentId] = useState('');
  const [preferredDate, setPreferredDate] = useState('');
  const [suggestions, setSuggestions] = useState<RescheduleSuggestion[]>([]);
  const [currentStart, setCurrentStart] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!appointmentId || !preferredDate) {
      toast.error('Rellene todos los campos');
      return;
    }
    setLoading(true);
    try {
      const result = await medasistApi.reschedule({
        appointment_id: Number(appointmentId),
        preferred_date: preferredDate,
      });
      setSuggestions(result.suggestions);
      setCurrentStart(result.current_start);
      toast.success(result.message);
    } catch (err) {
      toast.error('Error al obtener sugerencias');
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-lg font-semibold text-medical-textMain">
        <RefreshCw size={20} />
        Reagendar Cita
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">ID Cita</label>
          <input
            type="number"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
            placeholder="5"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Fecha Preferida</label>
          <input
            type="date"
            value={preferredDate}
            onChange={(e) => setPreferredDate(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full px-6 py-2 bg-medical-primary text-white rounded-xl font-medium hover:bg-blue-800 transition-all disabled:opacity-50"
          >
            {loading ? 'Buscando...' : 'Buscar Alternativas'}
          </button>
        </div>
      </div>

      {currentStart && (
        <div className="p-3 bg-slate-50 rounded-xl text-sm text-slate-600">
          <strong>Horario actual:</strong> {formatDateTime(currentStart)}
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-slate-700">Alternativas sugeridas:</h4>
          {suggestions.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between p-4 border border-slate-200 rounded-xl hover:border-medical-primary transition-all"
            >
              <div>
                <p className="font-medium text-medical-textMain">{formatDateTime(s.start)}</p>
                <p className="text-sm text-slate-500">hasta {formatDateTime(s.end)}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-500">Fit: {Math.round(s.score * 100)}%</span>
                <button className="px-4 py-2 bg-medical-secondary text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-all">
                  Seleccionar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {suggestions.length === 0 && !loading && (
        <div className="text-center py-8 text-slate-400">
          <Search size={48} className="mx-auto mb-3 opacity-50" />
          <p>Ingrese el ID de la cita y la fecha preferida para encontrar alternativas.</p>
        </div>
      )}
    </div>
  );
};

// ─── Disponibilidad Tab ─────────────────────────────────────────────────
const AvailabilityTab: React.FC = () => {
  const [doctorId, setDoctorId] = useState('');
  const [date, setDate] = useState('');
  const [duration, setDuration] = useState('30');
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!doctorId || !date) {
      toast.error('Rellene el ID del doctor y la fecha');
      return;
    }
    setLoading(true);
    try {
      const result = await medasistApi.getAvailableSlots({
        doctor_id: Number(doctorId),
        date,
        duration_minutes: Number(duration),
      });
      setSlots(result);
      toast.success(`Se encontraron ${result.length} horario(s) disponible(s)`);
    } catch (err) {
      toast.error('Error al obtener disponibilidad');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-lg font-semibold text-medical-textMain">
        <Clock size={20} />
        Horarios Disponibles
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">ID Doctor</label>
          <input
            type="number"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
            placeholder="1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Fecha</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Duración (min)</label>
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          >
            <option value="15">15 min</option>
            <option value="30">30 min</option>
            <option value="45">45 min</option>
            <option value="60">60 min</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full px-6 py-2 bg-medical-primary text-white rounded-xl font-medium hover:bg-blue-800 transition-all disabled:opacity-50"
          >
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
      </div>

      {slots.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {slots.map((slot, i) => (
            <div
              key={i}
              className="p-3 border border-slate-200 rounded-xl text-center hover:border-medical-primary hover:bg-blue-50 transition-all cursor-pointer"
            >
              <p className="font-semibold text-medical-textMain">{formatTime(slot.start)}</p>
              <p className="text-xs text-slate-500">a {formatTime(slot.end)}</p>
            </div>
          ))}
        </div>
      )}

      {slots.length === 0 && !loading && (
        <div className="text-center py-8 text-slate-400">
          <Clock size={48} className="mx-auto mb-3 opacity-50" />
          <p>Seleccione un doctor y una fecha para ver los horarios disponibles.</p>
        </div>
      )}
    </div>
  );
};

// ─── Seguimiento Tab ────────────────────────────────────────────────────
const FollowUpTab: React.FC = () => {
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [lastDate, setLastDate] = useState('');
  const [visitType, setVisitType] = useState<string>('control');
  const [result, setResult] = useState<{ recommended_date: string; reason: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSuggest = async () => {
    if (!patientId || !doctorId || !lastDate) {
      toast.error('Rellene todos los campos');
      return;
    }
    setLoading(true);
    try {
      const res = await medasistApi.suggestFollowUp({
        patient_id: Number(patientId),
        doctor_id: Number(doctorId),
        last_appointment_date: lastDate,
        visit_type: visitType as any,
      });
      setResult({ recommended_date: res.recommended_date, reason: res.reason });
      toast.success('Seguimiento sugerido');
    } catch (err) {
      toast.error('Error al calcular seguimiento');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-lg font-semibold text-medical-textMain">
        <Calendar size={20} />
        Sugerir Seguimiento
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">ID Paciente</label>
          <input
            type="number"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">ID Doctor</label>
          <input
            type="number"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Última Cita</label>
          <input
            type="date"
            value={lastDate}
            onChange={(e) => setLastDate(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Tipo de Visita</label>
          <select
            value={visitType}
            onChange={(e) => setVisitType(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-medical-secondary outline-none"
          >
            <option value="control">Control</option>
            <option value="urgent">Urgente</option>
            <option value="routine">Rutina</option>
            <option value="surgery_followup">Seg. Quirúrgico</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSuggest}
            disabled={loading}
            className="w-full px-6 py-2 bg-medical-primary text-white rounded-xl font-medium hover:bg-blue-800 transition-all disabled:opacity-50"
          >
            {loading ? 'Calculando...' : 'Sugerir'}
          </button>
        </div>
      </div>

      {result && (
        <div className="p-6 bg-green-50 border border-green-200 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="text-green-600" size={24} />
            <h4 className="font-semibold text-green-800">Seguimiento Sugerido</h4>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-slate-500">Fecha recomendada</p>
              <p className="text-lg font-bold text-medical-textMain">{result.recommended_date}</p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Razón</p>
              <p className="text-lg font-bold text-medical-textMain">{result.reason}</p>
            </div>
          </div>
          <button className="mt-4 px-6 py-2 bg-medical-secondary text-white rounded-xl font-medium hover:bg-teal-700 transition-all">
            Agendar Seguimiento
          </button>
        </div>
      )}
    </div>
  );
};

export default AIAssistantPage;
