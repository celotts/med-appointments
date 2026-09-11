import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, RefreshCw } from 'lucide-react';
import { medasistApi, ChatMessage } from '../api/medasistApi';
import { toast } from 'react-hot-toast';

const AIAssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hola, soy MedAssist. Estoy conectado a la base de datos clínica y documentos vectoriales. ¿En qué puedo ayudarte hoy?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await medasistApi.chat({
        message: input,
        historial: messages,
      });

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.respuesta }
      ]);
    } catch (error: any) {
      toast.error('Error al conectar con el agente de IA');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Lo siento, tuve un problema al procesar tu solicitud. Por favor, intenta de nuevo.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-medical-primary text-white rounded-lg shadow-lg">
            <Bot size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-medical-textMain">MedAssist AI</h2>
            <p className="text-medical-textMuted text-sm">Agente Clínico RAG (Recuperación Aumentada)</p>
          </div>
        </div>
        <button
          onClick={() => setMessages([{ role: 'assistant', content: 'Chat reiniciado. ¿En qué puedo ayudarte?' }])}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-medical-primary transition-colors"
        >
          <RefreshCw size={14} />
          Reiniciar Chat
        </button>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col min-h-[600px]">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === 'user' ? 'bg-medical-secondary text-white' : 'bg-medical-primary text-white'
                }`}>
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-medical-primary text-white rounded-tr-none'
                    : 'bg-slate-100 text-medical-textMain rounded-tl-none border border-slate-200'
                }`}>
                  {msg.content}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex gap-3 max-w-[80%]">
                <div className="h-8 w-8 rounded-full bg-medical-primary text-white flex items-center justify-center shrink-0">
                  <Bot size={16} />
                </div>
                <div className="p-4 bg-slate-100 text-medical-textMain rounded-2xl rounded-tl-none border border-slate-200 shadow-sm">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-slate-200 bg-slate-50">
          <div className="max-w-4xl mx-auto mb-4 flex flex-wrap gap-2">
            {[
              { label: 'Pacientes hoy', query: '¿Cuántos pacientes tengo programados para hoy?' },
              { label: 'Próxima cita', query: '¿Cuál es mi próxima cita?' },
              { label: 'Resumen clínico', query: 'Dame un resumen de la última nota clínica' },
              { label: 'Sugerir seguimiento', query: '¿Cómo debería programar el siguiente seguimiento?' },
            ].map((action, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInput(action.query);
                }}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:border-medical-primary hover:text-medical-primary transition-all shadow-sm"
              >
                {action.label}
              </button>
            ))}
          </div>
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre la agenda, pacientes o notas clínicas..."
              className="flex-1 px-4 py-3 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-medical-secondary transition-all text-sm"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-medical-primary text-white rounded-xl font-medium hover:bg-blue-800 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              Enviar
            </button>
          </form>
          <p className="text-center text-[10px] text-slate-400 mt-3">
            MedAssist AI puede cometer errores. Por favor, verifica la información clínica importante.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantPage;
