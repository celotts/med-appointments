import { useState, useRef, useEffect } from 'react';
import { Bot, Clock, Send, Loader2, MessageSquare, Activity, Sparkles } from 'lucide-react';
import { medasistApi, RescheduleSuggestion, AvailabilitySlot } from '../api/medasistApi';
import { ragApi, ChatMessage, HealthCheck } from '../api/ragApi';
import toast from 'react-hot-toast';

type Tab = 'chat' | 'reschedule' | 'availability' | 'followup';

const tabs = [
  { id: 'chat' as Tab, label: 'Chat IA', icon: MessageSquare },
  { id: 'reschedule' as Tab, label: 'Reagendar', icon: Clock },
  { id: 'availability' as Tab, label: 'Disponibilidad', icon: Activity },
  { id: 'followup' as Tab, label: 'Seguimiento', icon: Sparkles },
];

function ChatTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streaming, setStreaming] = useState('');
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ragApi.health().then(setHealth).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  const send = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg: ChatMessage = { role: 'user', content: input.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);
    setStreaming('');

    try {
      const response = await ragApi.chatStream(
        userMsg.content,
        messages.slice(-10),
        (partial) => setStreaming(partial)
      );
      setMessages([...newMessages, { role: 'assistant', content: response }]);
      setStreaming('');
    } catch (error: any) {
      const errMsg = error.response?.data?.detail || 'Error al conectar con la IA';
      toast.error(errMsg);
      setMessages([...newMessages, { role: 'assistant', content: `Error: ${errMsg}` }]);
      setStreaming('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-280px)] min-h-[400px]">
      {health && (
        <div className="flex items-center gap-4 px-4 py-2 bg-slate-50 rounded-t-xl border border-b-0 border-slate-200 text-xs text-medical-textMuted">
          <span className="flex items-center gap-1">
            <span className={`h-2 w-2 rounded-full ${health.ollama === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
            Ollama: {health.ollama}
          </span>
          <span>Modelo: {health.llm_model}</span>
          <span>Embeddings: {health.embedding_model}</span>
          <span>Docs: {health.vector_count}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="h-16 w-16 bg-medical-primary/10 rounded-2xl flex items-center justify-center mb-4">
              <Bot className="text-medical-primary" size={32} />
            </div>
            <h3 className="text-lg font-semibold text-medical-textMain mb-1">MedAssist IA</h3>
            <p className="text-sm text-medical-textMuted max-w-md">
              Asistente inteligente para gestion de citas. Puedo ayudarte a buscar pacientes, 
              verificar disponibilidad, o responder preguntas sobre la clinica.
            </p>
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              {['Cuantos pacientes hay?', 'Que doctores hay?', 'Mostrar citas de hoy'].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-full hover:bg-slate-50 text-medical-textMuted transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-medical-primary text-white rounded-br-md'
                : 'bg-white border border-slate-200 text-medical-textMain rounded-bl-md'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {streaming && (
          <div className="flex justify-start">
            <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-bl-md bg-white border border-slate-200 text-sm leading-relaxed text-medical-textMain">
              {streaming}
              <span className="inline-block w-1.5 h-4 bg-medical-primary/60 ml-0.5 animate-pulse" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-slate-200 bg-white rounded-b-xl">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Escribe tu pregunta..."
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none text-sm disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={isLoading || !input.trim()}
            className="p-2.5 bg-medical-primary text-white rounded-xl hover:bg-blue-800 transition-colors disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}

function RescheduleTab() {
  const [appointmentId, setAppointmentId] = useState('');
  const [preferredDate, setPreferredDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RescheduleSuggestion[] | null>(null);
  const [message, setMessage] = useState('');

  const handle = async () => {
    if (!appointmentId || !preferredDate) return;
    setLoading(true);
    try {
      const res = await medasistApi.reschedule({ appointment_id: parseInt(appointmentId), preferred_date: preferredDate });
      setResult(res.suggestions);
      setMessage(res.message);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">ID Cita</label>
          <input
            type="number"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha Preferida</label>
          <input
            type="date"
            value={preferredDate}
            onChange={(e) => setPreferredDate(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
      </div>
      <button
        onClick={handle}
        disabled={loading || !appointmentId || !preferredDate}
        className="px-4 py-2 bg-medical-primary text-white rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors disabled:opacity-50"
      >
        {loading ? 'Buscando...' : 'Buscar Alternativas'}
      </button>

      {message && <p className="text-sm text-medical-textMuted">{message}</p>}

      {result && result.length > 0 && (
        <div className="space-y-2">
          {result.map((s, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg">
              <div>
                <p className="text-sm font-medium text-medical-textMain">
                  {new Date(s.start).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  {' - '}
                  {new Date(s.end).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                </p>
                <p className="text-xs text-medical-textMuted">Score: {s.score}</p>
              </div>
              <button className="px-3 py-1 text-xs bg-medical-primary text-white rounded-lg hover:bg-blue-800">
                Seleccionar
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AvailabilityTab() {
  const [doctorId, setDoctorId] = useState('');
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);

  const handle = async () => {
    if (!doctorId || !date) return;
    setLoading(true);
    try {
      const res = await medasistApi.getAvailableSlots({ doctor_id: parseInt(doctorId), date, duration_minutes: 30 });
      setSlots(res);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">ID Doctor</label>
          <input
            type="number"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">Fecha</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
      </div>
      <button
        onClick={handle}
        disabled={loading || !doctorId || !date}
        className="px-4 py-2 bg-medical-primary text-white rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors disabled:opacity-50"
      >
        {loading ? 'Buscando...' : 'Ver Disponibilidad'}
      </button>

      {slots.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {slots.map((s, i) => (
            <div key={i} className="p-3 bg-white border border-slate-200 rounded-lg text-center hover:border-medical-secondary transition-colors cursor-pointer">
              <p className="text-sm font-medium text-medical-textMain">
                {new Date(s.start).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </p>
              <p className="text-xs text-medical-textMuted">
                {new Date(s.end).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          ))}
        </div>
      )}
      {slots.length === 0 && !loading && doctorId && date && (
        <p className="text-sm text-medical-textMuted text-center py-4">No hay slots disponibles</p>
      )}
    </div>
  );
}

function FollowupTab() {
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [lastDate, setLastDate] = useState('');
  const [visitType, setVisitType] = useState('routine');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ recommended_date: string; reason: string } | null>(null);

  const handle = async () => {
    if (!patientId || !doctorId || !lastDate) return;
    setLoading(true);
    try {
      const res = await medasistApi.suggestFollowUp({
        patient_id: parseInt(patientId),
        doctor_id: parseInt(doctorId),
        last_appointment_date: lastDate,
        visit_type: visitType as any,
      });
      setResult(res);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">ID Paciente</label>
          <input
            type="number"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">ID Doctor</label>
          <input
            type="number"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">Ultima Cita</label>
          <input
            type="date"
            value={lastDate}
            onChange={(e) => setLastDate(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-medical-textMain mb-1">Tipo Visita</label>
          <select
            value={visitType}
            onChange={(e) => setVisitType(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none"
          >
            <option value="routine">Rutina</option>
            <option value="control">Control</option>
            <option value="urgent">Urgente</option>
            <option value="surgery_followup">Seg. Cirugia</option>
          </select>
        </div>
      </div>
      <button
        onClick={handle}
        disabled={loading || !patientId || !doctorId || !lastDate}
        className="px-4 py-2 bg-medical-primary text-white rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors disabled:opacity-50"
      >
        {loading ? 'Calculando...' : 'Sugerir Seguimiento'}
      </button>

      {result && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
          <p className="text-sm font-medium text-green-800">{result.reason}</p>
          <p className="text-lg font-bold text-green-900 mt-1">
            {new Date(result.recommended_date).toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
      )}
    </div>
  );
}

const AIAssistantPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-medical-textMain">MedAssist IA</h2>
        <p className="text-medical-textMuted">Asistente inteligente para gestion clinica</p>
      </div>

      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === id
                ? 'bg-white text-medical-primary shadow-sm'
                : 'text-medical-textMuted hover:text-medical-textMain'
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        {activeTab === 'chat' && <ChatTab />}
        {activeTab === 'reschedule' && <RescheduleTab />}
        {activeTab === 'availability' && <AvailabilityTab />}
        {activeTab === 'followup' && <FollowupTab />}
      </div>
    </div>
  );
};

export default AIAssistantPage;
