import React from 'react';
import type { WorkloadFila } from '../../api/dashboardApi';

interface Props {
  datos: WorkloadFila[];
}

/**
 * Carga por medico, en barras horizontales.
 *
 * La barra es relativa al maximo del grupo, no al 100%: con un medico a 40
 * citas y otro a 2, una barra al 100% diria que ambos estan al maximo.
 *
 * `ocupacion_pct` null (medico sin horario en `doctor_schedules`) se muestra
 * como "sin horario", no como 0%: no se puede calcular.
 */
const CargaPorMedico: React.FC<Props> = ({ datos }) => {
  if (!datos.length) {
    return (
      <p className="py-12 text-center text-sm text-slate-400 italic">
        Sin citas en el periodo para los medicos de su alcance.
      </p>
    );
  }

  const maximo = Math.max(...datos.map((f) => f.total), 1);

  return (
    <div className="space-y-4">
      {datos.map((fila) => {
        const porcentaje = (fila.total / maximo) * 100;
        const total = fila.total || 1;
        // Cada tramo es un porcentaje DE LA BARRA, no del total: asi la
        // longitud de la barra sigue siendo comparable entre medicos.
        const anchoAtendidas = (fila.atendidas / total) * porcentaje;
        const anchoCanceladas = (fila.canceladas / total) * porcentaje;
        const anchoResto = Math.max(
          0,
          porcentaje - anchoAtendidas - anchoCanceladas,
        );

        return (
          <div key={fila.doctor_id}>
            <div className="flex items-baseline justify-between mb-1.5">
              <div className="min-w-0">
                <p className="text-sm font-medium text-medical-textMain truncate">
                  {fila.nombre}
                </p>
                <p className="text-xs text-medical-textMuted">
                  {fila.especialidad}
                  {fila.ocupacion_pct !== null && (
                    <span className="ml-2 text-slate-400">
                      ocupacion {fila.ocupacion_pct}%
                    </span>
                  )}
                  {fila.ocupacion_pct === null && (
                    <span className="ml-2 text-slate-400">sin horario configurado</span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs text-medical-textMuted shrink-0 ml-3">
                <span className="font-semibold text-medical-textMain">{fila.total}</span>
                <span>{fila.atendidas} atendidas</span>
              </div>
            </div>

            <div
              className="h-2.5 bg-slate-100 rounded-full overflow-hidden flex"
              role="img"
              aria-label={`${fila.nombre}: ${fila.total} citas, ${fila.atendidas} atendidas, ${fila.canceladas} canceladas`}
            >
              <div
                className="h-full bg-medical-personal"
                style={{ width: `${anchoAtendidas}%` }}
              />
              <div
                className="h-full bg-medical-warning"
                style={{ width: `${anchoCanceladas}%` }}
              />
              <div
                className="h-full bg-slate-300"
                style={{ width: `${anchoResto}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CargaPorMedico;
