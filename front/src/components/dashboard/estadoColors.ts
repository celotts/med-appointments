import { ESTADOS_CITA, type EstadoCita } from '../../api/dashboardApi';

/**
 * Colores por estado de cita.
 *
 * Solo 4 son colores del tema (`medical.*`); los demas son tonos sueltos
 * porque un estado no puede tener "el color del tema": tiene que distinguirse
 * de los otros siete. La deuda de tenerlos aqui en vez de en el tema es
 * conscious y esta anotada en docs/PENDIENTES.md.
 */
export const COLOR_ESTADO: Record<string, string> = {
  PENDIENTE: 'bg-slate-400',
  CONFIRMADA: 'bg-medical-primary',
  'EN ESPERA': 'bg-medical-visit',
  'EN PROCESO': 'bg-medical-operation',
  ATENDIDA: 'bg-medical-personal',
  CANCELADA: 'bg-medical-danger',
  SUSPENDIDA: 'bg-medical-warning',
  REAGENDADA: 'bg-medical-secondary',
};

/** Texto legible para cada estado, para tooltips y etiquetas. */
export const TEXTO_ESTADO: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  CONFIRMADA: 'Confirmada',
  'EN ESPERA': 'En espera',
  'EN PROCESO': 'En proceso',
  ATENDIDA: 'Atendida',
  CANCELADA: 'Cancelada',
  SUSPENDIDA: 'Suspendida',
  REAGENDADA: 'Reagendada',
};

/** Clases de texto (no de fondo) para las insignias de estado. */
export const TEXTO_ESTADO_CLASE: Record<string, string> = {
  PENDIENTE: 'text-slate-600 bg-slate-100',
  CONFIRMADA: 'text-medical-primary bg-blue-50',
  'EN ESPERA': 'text-medical-visit bg-orange-50',
  'EN PROCESO': 'text-medical-operation bg-red-50',
  ATENDIDA: 'text-medical-personal bg-green-50',
  CANCELADA: 'text-medical-danger bg-red-50',
  SUSPENDIDA: 'text-medical-warning bg-amber-50',
  REAGENDADA: 'text-medical-secondary bg-blue-50',
};

export function colorDe(estado: string): string {
  return COLOR_ESTADO[estado] ?? 'bg-slate-300';
}

export function claseDe(estado: string): string {
  return TEXTO_ESTADO_CLASE[estado] ?? 'text-slate-600 bg-slate-100';
}

export function nombreDe(estado: string): string {
  return TEXTO_ESTADO[estado] ?? estado;
}

/**
 * Los 8 estados siempre, aunque no tengan citas.
 *
 * Un `Object.keys(por_estado)` solo devolveria los que tienen algo, y la
 * leyenda cambiaria de una carga a otra: el usuario no podria comparar dos
 * dias. Los 8 son el marco fijo, y quien no tiene citas se atenua en el
 * componente.
 *
 * No recibe el mapa a proposito: la lista no depende de los datos, y aceptar
 * el parametro invita a usarlo y volver al problema.
 */
export function estadosVisibles(): EstadoCita[] {
  return ESTADOS_CITA.slice() as EstadoCita[];
}
