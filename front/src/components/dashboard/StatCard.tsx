import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

interface Props {
  titulo: string;
  valor: string | number;
  icono: LucideIcon;
  /** Clase de fondo del icono. Sin hex sueltos: tokens `medical-*`. */
  colorIcono: string;
  /** Texto pequeno bajo el numero. */
  detalle?: string;
  /** Variacion en % frente al periodo anterior. `null` = sin comparacion. */
  tendencia?: number | null;
  /** Que representa la tendencia, para que el icono no sea ambiguo. */
  tendenciaLabel?: string;
  /**
   * Si subir es bueno. En `citas atendidas` si; en `cancelaciones` no.
   * Sin esto, un -30% en cancelaciones se pinta en rojo como si fuera malo.
   */
  subirEsBueno?: boolean;
}

/**
 * Tarjeta de indicador.
 *
 * `tendencia` null NO se muestra como 0%: un 0% dice "no cambio" y un null
 * dice "no hay con que comparar". Confundirlos hace que un mes sin datos
 * pareciera un mes estable.
 */
const StatCard: React.FC<Props> = ({
  titulo,
  valor,
  icono: Icono,
  colorIcono,
  detalle,
  tendencia,
  tendenciaLabel,
  subirEsBueno = true,
}) => {
  const hayTendencia = tendencia !== null && tendencia !== undefined;
  const sube = hayTendencia && tendencia! > 0;
  const baja = hayTendencia && tendencia! < 0;
  const Flecha = sube ? ArrowUpRight : baja ? ArrowDownRight : Minus;

  const claseTendencia = !hayTendencia || tendencia === 0
    ? 'text-slate-400'
    : (sube === subirEsBueno)
      ? 'text-medical-personal'
      : 'text-medical-danger';

  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
      <div className="flex items-start justify-between">
        <p className="text-sm text-medical-textMuted font-medium">{titulo}</p>
        <div className={`p-2.5 rounded-xl ${colorIcono} text-white`}>
          <Icono size={20} />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <h3 className="text-3xl font-bold text-medical-textMain">{valor}</h3>
        {hayTendencia && (
          <span className={`flex items-center text-xs font-semibold ${claseTendencia}`}>
            <Flecha size={14} />
            {Math.abs(tendencia!).toFixed(1)}%
          </span>
        )}
      </div>
      {detalle && <p className="mt-1 text-xs text-medical-textMuted">{detalle}</p>}
      {hayTendencia && tendenciaLabel && (
        <p className="mt-1 text-xs text-slate-400">{tendenciaLabel}</p>
      )}
    </div>
  );
};

export default StatCard;
