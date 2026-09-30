import React from 'react';
import { AlertCircle, CalendarX2, Clock } from 'lucide-react';
import type { AgendaCita } from '../../api/dashboardApi';
import { claseDe, nombreDe } from './estadoColors';

interface Props {
  citas: AgendaCita[];
  /** Al pulsar una fila. Sin esto la lista es de solo lectura. */
  onSelectCita?: (cita: AgendaCita) => void;
}

/** "2026-09-30T14:30:00+00:00" -> "14:30" */
function hora(iso: string): string {
  const fecha = new Date(iso);
  if (isNaN(fecha.getTime())) return '--:--';
  return `${String(fecha.getHours()).padStart(2, '0')}:${String(
    fecha.getMinutes(),
  ).padStart(2, '0')}`;
}

/** Duracion en minutos entre inicio y fin. */
function duracionMin(inicio: string, fin: string): number | null {
  const a = new Date(inicio).getTime();
  const b = new Date(fin).getTime();
  if (isNaN(a) || isNaN(b) || b <= a) return null;
  return Math.round((b - a) / 60000);
}

/**
 * Agenda del dia en orden cronologico.
 *
 * ## Por que la fila es un `button` y no un `div`
 *
 * Porque una fila pulsable tiene que funcionar con teclado. Con un `div` y un
 * `onClick`, quien navega con Tab se salta la agenda entera y no llega a abrir
 * el detalle de ninguna cita. Con un `button` se llega con Tab, se abre con
 * Enter o con espacio, y un lector de pantalla anuncia "botón".
 *
 * ## Por que no se edita desde aqui
 *
 * El detalle se abre en modo lectura. Las acciones que cambian el estado
 * (confirmar, suspender, cancelar) viven en la pantalla de citas, que tiene
 * las reglas de rol y la confirmacion de motivos obligatorios. Meterlas aqui
 * obligaria a duplicar esa logica en dos sitios, y basta con que se
 * desincronicen para que una regla de rol deje de aplicarse.
 */
const AgendaDelDia: React.FC<Props> = ({ citas, onSelectCita }) => {
  if (!citas.length) {
    return (
      <div className="py-12 text-center">
        <CalendarX2 size={32} className="mx-auto text-slate-300 mb-3" />
        <p className="text-sm text-slate-400 italic">
          No hay citas programadas para hoy.
        </p>
      </div>
    );
  }

  const ahora = Date.now();

  return (
    <div className="divide-y divide-slate-100">
      {citas.map((cita) => {
        const inicio = new Date(cita.hora_inicio).getTime();
        const minutos = duracionMin(cita.hora_inicio, cita.hora_fin);
        // Una cita pasada que sigue viva es la que se le paso al paciente.
        const vencida = !isNaN(inicio) && inicio < ahora;
        const Etiqueta = onSelectCita ? 'button' : 'div';

        return (
          <Etiqueta
            key={cita.id}
            onClick={onSelectCita ? () => onSelectCita(cita) : undefined}
            type={onSelectCita ? 'button' : undefined}
            aria-label={
              onSelectCita
                ? `Ver detalle de la cita de ${cita.paciente} a las ${hora(cita.hora_inicio)}`
                : undefined
            }
            className={`w-full text-left flex items-center gap-4 py-3 px-2 rounded-lg transition-colors ${
              onSelectCita
                ? 'cursor-pointer hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary focus-visible:bg-slate-50'
                : ''
            }`}
          >
            <div className="w-14 shrink-0 text-center">
              <span className="text-sm font-bold text-medical-textMain">
                {hora(cita.hora_inicio)}
              </span>
              {minutos !== null && (
                <span className="block text-[10px] text-medical-textMuted">
                  {minutos} min
                </span>
              )}
            </div>

            <div className="min-w-0 flex-1">
              {/* Sin `truncate` en el nombre: "Ramon Ra..." no identifica a
                  nadie. Con 18 citas y scroll interno hay sitio de sobra, y el
                  nombre completo es justo lo que un medico necesita para
                  preparar la consulta. */}
              <p className="text-sm font-medium text-medical-textMain">
                {cita.paciente}
              </p>
              <div className="flex items-center gap-2 text-xs text-medical-textMuted mt-0.5 min-w-0">
                {cita.paciente_documento && (
                  <span className="shrink-0">{cita.paciente_documento}</span>
                )}
                {cita.motivo && (
                  <>
                    <span className="text-slate-300 shrink-0">|</span>
                    <span className="truncate">{cita.motivo}</span>
                  </>
                )}
              </div>
            </div>

            {vencida && (
              <Clock
                size={14}
                className="text-medical-warning shrink-0"
                aria-label="Su hora ya paso"
              />
            )}

            <span
              className={`shrink-0 text-[11px] font-medium px-2.5 py-1 rounded-full ${claseDe(
                cita.estado,
              )}`}
            >
              {nombreDe(cita.estado)}
            </span>
          </Etiqueta>
        );
      })}
    </div>
  );
};

/** Aviso cuando el panel no puede mostrar datos por un fallo de permisos. */
export const AvisoDePermisos: React.FC<{ mensaje: string }> = ({ mensaje }) => (
  <div className="flex items-start gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
    <AlertCircle size={18} className="shrink-0 mt-0.5" />
    <span>{mensaje}</span>
  </div>
);

export default AgendaDelDia;
