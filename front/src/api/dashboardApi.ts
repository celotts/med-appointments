import axiosInstance from './axiosInstance';

/**
 * Cliente del dashboard operativo.
 *
 * Un endpoint por pregunta, igual que en el backend: `/kpis` no necesita la
 * serie diaria para pintar las tarjetas, y separarlos permite no traer 30
 * dias de datos para mostrar un numero.
 *
 * Todos exigen un rol de `DASHBOARD_ROLES` en el backend. Un PATIENT recibe
 * 403, y eso lo decide el servidor: aqui no se filtra nada por rol porque no
 * hay ningun dato del que filtrar.
 */

/** Alcance del panel para el usuario actual. */
export interface DashboardScope {
  es_admin: boolean;
  es_asistente: boolean;
  es_medico: boolean;
  /** `null` = ve toda la clinica (administrador). */
  medicos_visibles: number | null;
}

/** Tarjetas principales. */
export interface DashboardKpis {
  citas_hoy: number;
  citas_hoy_atendidas: number;
  citas_hoy_pendientes: number;
  citas_hoy_confirmadas: number;
  citas_hoy_en_espera: number;
  citas_hoy_en_proceso: number;
  citas_semana: number;
  citas_mes: number;
  atendidas_mes: number;
  canceladas_mes: number;
  inasistencias_mes: number;
  tasa_asistencia_pct: number;
  tasa_cancelacion_pct: number;
  tasa_inasistencia_pct: number;
}

/** Como va el dia. */
export interface DashboardToday {
  fecha: string;
  total: number;
  en_curso: number;
  cerradas: number;
  avance_pct: number;
  /** Citas por codigo de estado. Solo aparecen los que tienen alguma cita. */
  por_estado: Record<string, number>;
}

/** Un punto de la serie diaria. */
export interface SeriePunto {
  dia: string;
  total: number;
  atendidas: number;
  canceladas: number;
  inasistencias: number;
}

export interface DashboardSerie {
  dias: number;
  data: SeriePunto[];
}

/** Una fila de carga por medico. */
export interface WorkloadFila {
  doctor_id: number;
  nombre: string;
  especialidad: string;
  total: number;
  atendidas: number;
  canceladas: number;
  /** `null` = sin horario en `doctor_schedules`, no se puede calcular. */
  ocupacion_pct: number | null;
}

export interface DashboardWorkload {
  dias: number;
  data: WorkloadFila[];
}

/** Una cita de la agenda del dia. */
export interface AgendaCita {
  id: number;
  hora_inicio: string;
  hora_fin: string;
  estado: string;
  estado_descripcion: string | null;
  paciente: string;
  paciente_documento: string | null;
  doctor_id: number;
  motivo: string;
}

export interface DashboardSchedule {
  fecha: string;
  total: number;
  citas: AgendaCita[];
}

/** Un dia del calendario, con el desglose por estado. */
export interface CalendarioDia {
  dia: string;
  total: number;
  /** Los 8 estados canonicos, siempre presentes (con 0 si no hay). */
  por_estado: Record<string, number>;
  confirmadas: number;
  pendientes: number;
  atendidas: number;
  canceladas: number;
}

/**
 * La rejilla de un mes, con los dias de los meses vecinos que se completan.
 *
 * `primera_semana` es el dia de la semana del primer dia del mes (0 = lunes).
 * Viene del backend para que el frontend y el servidor no discrepen sobre
 * donde empieza la semana.
 */
export interface CalendarioMes {
  anio: number;
  mes: number;
  primera_semana: number;
  dias_en_mes: number;
  dias: CalendarioDia[];
}

/** Los 8 estados canonicos. Espejo de `AppointmentStatusCode`. */
export const ESTADOS_CITA = [
  'PENDIENTE',
  'CONFIRMADA',
  'EN ESPERA',
  'EN PROCESO',
  'ATENDIDA',
  'CANCELADA',
  'SUSPENDIDA',
  'REAGENDADA',
] as const;

export type EstadoCita = (typeof ESTADOS_CITA)[number];

export const dashboardApi = {
  async getScope(): Promise<DashboardScope> {
    const response = await axiosInstance.get('/dashboard/scope');
    return response.data;
  },

  async getKpis(dias = 30): Promise<DashboardKpis> {
    const response = await axiosInstance.get('/dashboard/kpis', { params: { dias } });
    return response.data;
  },

  async getToday(fecha?: string): Promise<DashboardToday> {
    const response = await axiosInstance.get('/dashboard/today', {
      params: fecha ? { fecha } : {},
    });
    return response.data;
  },

  async getSerie(dias = 14): Promise<DashboardSerie> {
    const response = await axiosInstance.get('/dashboard/series', { params: { dias } });
    return response.data;
  },

  async getWorkload(dias = 30): Promise<DashboardWorkload> {
    const response = await axiosInstance.get('/dashboard/workload', { params: { dias } });
    return response.data;
  },

  async getSchedule(fecha?: string): Promise<DashboardSchedule> {
    const response = await axiosInstance.get('/dashboard/schedule', {
      params: fecha ? { fecha } : {},
    });
    return response.data;
  },

  /**
   * Calendario de un mes.
   *
   * Sin argumentos pide el mes actual. El backend devuelve la malla completa
   * (incluidos los dias del mes anterior y siguiente que se completan), de
   * modo que el frontend no tiene que calcular donde empieza la semana.
   */
  async getCalendario(anio?: number, mes?: number): Promise<CalendarioMes> {
    const params: Record<string, number> = {};
    if (anio) params.anio = anio;
    if (mes) params.mes = mes;
    const response = await axiosInstance.get('/dashboard/calendario', { params });
    return response.data;
  },
};
