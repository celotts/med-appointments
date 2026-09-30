import React from 'react';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import type { DashboardToday } from '../../api/dashboardApi';
import { claseDe, estadosVisibles, nombreDe } from './estadoColors';

interface Props {
  resumen: DashboardToday;
}

/**
 * Distribucion de estados del dia, en barras horizontales.
 *
 * Se muestran los 8 estados siempre, incluso los que valen 0: una leyenda que
 * cambia de una carga a otra impide comparar dos dias. Los que estan a 0 se
 * atenuan para que se lean como "no ocurrio" y no como dato.
 */
const DistribucionEstados: React.FC<Props> = ({ resumen }) => {
  const porEstado = resumen.por_estado;
  const maximo = Math.max(...Object.values(porEstado), 1);

  return (
    <div>
      <div className="flex items-center gap-4 mb-5 text-sm">
        <div className="flex items-center gap-1.5 text-medical-personal font-semibold">
          <CheckCircle2 size={16} />
          {resumen.avance_pct}% resuelto
        </div>
        {resumen.en_curso > 0 && (
          <div className="flex items-center gap-1.5 text-medical-visit font-medium">
            <Clock size={16} />
            {resumen.en_curso} en curso
          </div>
        )}
      </div>

      <div className="space-y-2.5">
        {estadosVisibles().map((estado) => {
          const cantidad = porEstado[estado] ?? 0;
          const ancho = (cantidad / maximo) * 100;
          const vacio = cantidad === 0;

          return (
            <div
              key={estado}
              className={`flex items-center gap-3 ${vacio ? 'opacity-40' : ''}`}
            >
              <div className="w-24 shrink-0 text-xs text-medical-textMuted text-right">
                {nombreDe(estado)}
              </div>
              <div className="flex-1 h-6 bg-slate-100 rounded-md overflow-hidden relative">
                {ancho > 0 && (
                  <div
                    className={`h-full ${claseDe(estado)} transition-all`}
                    style={{ width: `${ancho}%` }}
                  />
                )}
                <span className="absolute inset-y-0 left-2 flex items-center text-xs font-semibold text-medical-textMain">
                  {cantidad}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {resumen.total === 0 && (
        <div className="mt-5 flex items-start gap-2 p-3 bg-slate-50 rounded-lg text-xs text-medical-textMuted">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <span>
            No hay citas programadas para hoy en su alcance. Si deberia haberlas,
            compruebe que el paciente y el medico esten relacionados con su
            usuario: el panel resuelve el medico por correo.
          </span>
        </div>
      )}
    </div>
  );
};

export default DistribucionEstados;
