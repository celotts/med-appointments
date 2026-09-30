import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { CalendarioDia, CalendarioMes } from '../../api/dashboardApi';

interface Props {
  calendario: CalendarioMes;
  /** Dia seleccionado, en formato YYYY-MM-DD. */
  seleccionado: string | null;
  onSeleccionar: (dia: string) => void;
  onMesAnterior: () => void;
  onMesSiguiente: () => void;
  cargando?: boolean;
}

/**
 * Encabezados de la semana, generados desde una fecha real.
 *
 * Antes eran literales: `['Lun', 'Mar', 'Mie', ...]`. Con eso, si el navegador
 * traducia la pagina, podia reinterpretarlos ("Vie" llego a mostrarse como
 * "Rivalizar" en un `lang` incorrecto) y el calendario quedaba ilegible.
 *
 * `Intl` los produce en el idioma del documento, de modo que el texto viene
 * siempre de la plataforma y no de una constante que alguien pueda traducir
 * por error. El lunes es el inicio de semana en Mexico y en casi toda Latinoamerica.
 */
const DIAS_SEMANA = Array.from({ length: 7 }, (_, i) =>
  new Intl.DateTimeFormat('es-MX', { weekday: 'short' })
    .format(new Date(2026, 0, 5 + i)) // 2026-01-05 fue lunes
    .replace('.', '')
    .replace(/^./, (c) => c.toUpperCase())
);
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

const HOY = () => new Date().toISOString().slice(0, 10);

/**
 * Intensidad segun cuantas citas tiene el dia.
 *
 * Cuatro escalones, no una escala continua. Con cinco escalones el matiz entre
 * "6 citas" y "7" no lo distingue nadie, y lo que un especialista necesita es
 * leer la carga del dia de un vistazo, con el detalle al pulsarlo.
 */
function nivel(total: number): 0 | 1 | 2 | 3 {
  if (total === 0) return 0;
  if (total <= 3) return 1;
  if (total <= 7) return 2;
  return 3;
}

const FONDO = [
  '',
  'bg-medical-primary/10 hover:bg-medical-primary/20',
  'bg-medical-primary/25 hover:bg-medical-primary/35',
  'bg-medical-primary/45 hover:bg-medical-primary/55',
];

/**
 * Calendario mensual con los dias que tienen citas marcados.
 *
 * ## Por que el backend manda la malla
 *
 * El servidor devuelve tambien los dias del mes anterior y siguiente que
 * completan las filas. Si el frontend los calculara por su cuenta, cualquier
 * diferencia de criterio (donde empieza la semana, años bisiestos)eria una
 * rejilla que "baille" al cambiar de mes. Aqui se pinta lo que llega.
 *
 * ## Navegacion por teclado
 *
 * Un calendario que solo se maneja con el raton deja fuera a quien navega con
 * teclado. Cada dia es un `<button>`, con lo que se llega con Tab y se activa
 * con Enter o espacio, sin codigo extra.
 */
const CalendarioMensual: React.FC<Props> = ({
  calendario,
  seleccionado,
  onSeleccionar,
  onMesAnterior,
  onMesSiguiente,
  cargando = false,
}) => {
  const hoy = HOY();
  const anio = calendario.anio;
  const mes = calendario.mes;

  return (
    <div className={cargando ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-medical-textMain">
            {MESES[mes - 1]} {anio}
          </h3>
          {seleccionado && (
            <p className="text-xs text-medical-textMuted mt-0.5">
              {resumenDelDia(seleccionado, calendario.dias)}
            </p>
          )}
        </div>
        <div className="flex gap-1">
          <button
            onClick={onMesAnterior}
            className="p-2 rounded-lg text-medical-textMuted hover:bg-slate-100 hover:text-medical-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary"
            aria-label="Mes anterior"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={onMesSiguiente}
            className="p-2 rounded-lg text-medical-textMuted hover:bg-slate-100 hover:text-medical-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary"
            aria-label="Mes siguiente"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 mb-1" role="row">
        {DIAS_SEMANA.map((d) => (
          <div
            key={d}
            className="text-[11px] font-semibold text-medical-textMuted text-center py-1"
            aria-hidden="true"
          >
            {d}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1" role="grid" aria-label={`Calendario de ${MESES[mes - 1]} ${anio}`}>
        {calendario.dias.map((dia) => (
          <Celda
            key={dia.dia}
            dia={dia}
            enMes={Number(dia.dia.slice(5, 7)) === mes}
            esHoy={dia.dia === hoy}
            seleccionado={dia.dia === seleccionado}
            onSeleccionar={onSeleccionar}
          />
        ))}
      </div>

      <Leyenda />
    </div>
  );
};

interface CeldaProps {
  dia: CalendarioDia;
  enMes: boolean;
  esHoy: boolean;
  seleccionado: boolean;
  onSeleccionar: (dia: string) => void;
}

const Celda: React.FC<CeldaProps> = ({
  dia,
  enMes,
  esHoy,
  seleccionado,
  onSeleccionar,
}) => {
  const numero = Number(dia.dia.slice(8, 10));
  const n = nivel(dia.total);

  // Un dia fuera del mes sigue siendo navegable (se puede agendar ahi), pero
  // atenuado para que se lea como "no es parte de este mes".
  const clases = [
    'relative flex flex-col items-center justify-start rounded-lg py-1.5 min-h-[3.25rem]',
    'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary',
    enMes ? '' : 'opacity-35',
    FONDO[n],
    seleccionado ? 'ring-2 ring-medical-primary' : '',
    esHoy ? 'font-bold' : '',
  ].join(' ');

  return (
    <button
      onClick={() => onSeleccionar(dia.dia)}
      className={clases}
      aria-label={etiquetaAccesible(dia)}
      aria-current={esHoy ? 'date' : undefined}
      aria-selected={seleccionado}
      role="gridcell"
    >
      <span className={`text-xs ${esHoy ? 'text-medical-primary' : 'text-medical-textMain'}`}>
        {numero}
      </span>
      {dia.total > 0 && (
        <span className="text-[10px] font-semibold text-medical-primary mt-0.5 leading-none">
          {dia.total}
        </span>
      )}
      {/* Punto de confirmadas: el dato que un especialista usa para saber si
          tiene que llamar a alguien. Un unico punto, no un segundo numero. */}
      {dia.confirmadas > 0 && (
        <span
          className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-medical-personal"
          aria-hidden="true"
        />
      )}
    </button>
  );
};

/** Texto que lee un lector de pantalla para un dia. */
function etiquetaAccesible(dia: CalendarioDia): string {
  const partes = [`${dia.dia}: ${dia.total} citas`];
  if (dia.confirmadas) partes.push(`${dia.confirmadas} confirmadas`);
  if (dia.pendientes) partes.push(`${dia.pendientes} pendientes`);
  if (dia.atendidas) partes.push(`${dia.atendidas} atendidas`);
  return partes.join(', ');
}

function resumenDelDia(iso: string, dias: CalendarioDia[]): string {
  const dia = dias.find((d) => d.dia === iso);
  if (!dia || dia.total === 0) return 'Sin citas ese dia';
  const partes = [`${dia.total} citas`];
  if (dia.confirmadas) partes.push(`${dia.confirmadas} confirmadas`);
  if (dia.pendientes) partes.push(`${dia.pendientes} por confirmar`);
  return partes.join(' · ');
}

const Leyenda: React.FC = () => (
  <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-slate-100 text-[11px] text-medical-textMuted">
    <span className="flex items-center gap-1.5">
      <span className="w-4 h-4 rounded bg-medical-primary/10" /> 1-3 citas
    </span>
    <span className="flex items-center gap-1.5">
      <span className="w-4 h-4 rounded bg-medical-primary/25" /> 4-7
    </span>
    <span className="flex items-center gap-1.5">
      <span className="w-4 h-4 rounded bg-medical-primary/45" /> 8 o mas
    </span>
    <span className="flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full bg-medical-personal" /> tiene confirmadas
    </span>
    <span className="flex items-center gap-1.5">
      <span className="w-3 h-3 rounded border-2 border-medical-primary" /> seleccionado
    </span>
  </div>
);

export default CalendarioMensual;
