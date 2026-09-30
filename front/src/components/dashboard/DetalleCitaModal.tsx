import React from 'react';
import { Clock, FileText, Hash, Stethoscope, User } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Modal from '../common/Modal';
import type { AgendaCita } from '../../api/dashboardApi';
import { claseDe, nombreDe } from './estadoColors';

interface Props {
  cita: AgendaCita | null;
  onClose: () => void;
}

/** "2026-09-30T14:30:00+00:00" -> "30/09/2026, 14:30" */
function fechaHora(iso: string): string {
  const f = new Date(iso);
  if (isNaN(f.getTime())) return '--';
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(f.getDate())}/${p(f.getMonth() + 1)}/${f.getFullYear()}, ${p(f.getHours())}:${p(f.getMinutes())}`;
}

function duracion(inicio: string, fin: string): string {
  const a = new Date(inicio).getTime();
  const b = new Date(fin).getTime();
  if (isNaN(a) || isNaN(b) || b <= a) return '--';
  return `${Math.round((b - a) / 60000)} min`;
}

/**
 * Detalle de una cita, en modo lectura.
 *
 * ## Solo se muestra lo que el backend devuelve
 *
 * Cada campo viene de `AgendaCita`. No se deducen horas ni se completan datos
 * que el servidor no manda: un modal que muestra mas de lo que sabe produce
 * informacion inventada, que en una cita clinica es peor que un campo vacio.
 *
 * ## Por que no hay botones de accion
 *
 * Confirmar, suspender o cancelar tienen sus reglas (motivo obligatorio,
 * transiciones validas, rol). Esas reglas viven en la pantalla de citas. Duplicar
 * aqui las acciones sin las reglas dejaria un camino para saltarselas.
 */
const DetalleCitaModal: React.FC<Props> = ({ cita, onClose }) => {
  return (
    <Modal
      isOpen={cita !== null}
      onClose={onClose}
      title="Detalle de la cita"
      tamano="lg"
    >
      {cita && (
        <div className="space-y-5">
          {/* Estado arriba: es lo primero que se mira al abrir una cita. */}
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs text-medical-textMuted">Estado</p>
              <span
                className={`inline-block mt-1 text-xs font-medium px-3 py-1 rounded-full ${claseDe(
                  cita.estado,
                )}`}
              >
                {nombreDe(cita.estado)}
              </span>
            </div>
            {cita.estado_descripcion && (
              <p className="text-xs text-medical-textMuted text-right max-w-[50%]">
                {cita.estado_descripcion}
              </p>
            )}
          </div>

          <Campo icono={Clock} etiqueta="Horario">
            <p className="text-sm text-medical-textMain">
              {fechaHora(cita.hora_inicio)} — {fechaHora(cita.hora_fin).split(', ')[1]}
            </p>
            <p className="text-xs text-medical-textMuted mt-0.5">
              Duracion: {duracion(cita.hora_inicio, cita.hora_fin)}
            </p>
          </Campo>

          <Campo icono={User} etiqueta="Paciente">
            <p className="text-sm text-medical-textMain">{cita.paciente}</p>
            {cita.paciente_documento && (
              <p className="text-xs text-medical-textMuted mt-0.5 flex items-center gap-1">
                <Hash size={11} />
                {cita.paciente_documento}
              </p>
            )}
          </Campo>

          {cita.motivo && (
            <Campo icono={FileText} etiqueta="Motivo">
              <p className="text-sm text-medical-textMain whitespace-pre-line">
                {cita.motivo}
              </p>
              {/* El motivo acumula los sufijos que escribe el backend al
                  cancelar o suspender (`[Cancelada]: ...`). Se separan para que
                  el motivo original no quede escondido detras del tecnicismo. */}
              {/\n\[/.test(cita.motivo) && (
                <p className="text-xs text-medical-textMuted mt-2 pt-2 border-t border-slate-100">
                  {cita.motivo.split('\n').filter((l) => l.startsWith('[')).join(' · ')}
                </p>
              )}
            </Campo>
          )}

          <Campo icono={Stethoscope} etiqueta="Medico">
            <p className="text-sm text-medical-textMain">
              Id. {cita.doctor_id}
            </p>
          </Campo>

          <p className="text-xs text-medical-textMuted pt-3 border-t border-slate-100">
            Para cambiar el estado de la cita, usa la pantalla Agenda, que
            comprueba las transiciones validas y exige el motivo cuando hace
            falta.
          </p>
        </div>
      )}
    </Modal>
  );
};

interface CampoProps {
  icono: LucideIcon;
  etiqueta: string;
  children: React.ReactNode;
}

const Campo: React.FC<CampoProps> = ({ icono: Icono, etiqueta, children }) => (
  <div className="flex gap-3">
    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
      <Icono size={16} />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-xs text-medical-textMuted mb-1">{etiqueta}</p>
      {children}
    </div>
  </div>
);

export default DetalleCitaModal;
