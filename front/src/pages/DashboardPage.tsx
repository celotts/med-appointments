import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import {
  Activity,
  CalendarCheck,
  CalendarDays,
  Loader2,
  RefreshCw,
  TrendingUp,
  UserX,
  Users,
  ChevronDown,
} from 'lucide-react';

import {
  dashboardApi,
  type AgendaCita,
  type CalendarioMes,
  type DashboardKpis,
  type DashboardSchedule,
  type DashboardScope,
  type DashboardSerie,
  type DashboardToday,
  type DashboardWorkload,
} from '../api/dashboardApi';
import StatCard from '../components/dashboard/StatCard';
import SerieDiaria from '../components/dashboard/SerieDiaria';
import CargaPorMedico from '../components/dashboard/CargaPorMedico';
import DistribucionEstados from '../components/dashboard/DistribucionEstados';
import AgendaDelDia from '../components/dashboard/AgendaDelDia';
import CalendarioMensual from '../components/dashboard/CalendarioMensual';
import DetalleCitaModal from '../components/dashboard/DetalleCitaModal';
import { useAuth } from '../contexts/AuthContext';
import { hasRole, DOCTOR, SPECIALIST, ASSISTANT } from '../auth/roles';

/**
 * Dashboard operativo para quien lleva la agenda.
 *
 * ## Que se ve segun el rol
 *
 * El backend ya limita los datos (`crud_agenda_scope`), asi que esta pagina
 * no filtra nada: solo cambia el titulo y el orden de las secciones para no
 * mostrarle a un asistente una tabla que siempre saldra vacia.
 *
 * ## Nada de numeros inventados
 *
 * La version anterior de esta pagina mostraba "Tasa de No-Show 12%", "Carga de
 * Trabajo: Alta" y un texto de insights de IA como texto literal. Todo eso era
 * fiction: no venia de ninguna consulta. Aqui cada numero viene de
 * `/api/v1/dashboard/*`.
 */
const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const esAsistente = hasRole(user?.role, [ASSISTANT]);
  const esMedico = hasRole(user?.role, [DOCTOR, SPECIALIST]);

  const [scope, setScope] = useState<DashboardScope | null>(null);
  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  const [hoy, setHoy] = useState<DashboardToday | null>(null);
  const [serie, setSerie] = useState<DashboardSerie | null>(null);
  const [workload, setWorkload] = useState<DashboardWorkload | null>(null);
  const [agenda, setAgenda] = useState<DashboardSchedule | null>(null);
  const [calendario, setCalendario] = useState<CalendarioMes | null>(null);
  const [citaAbierta, setCitaAbierta] = useState<AgendaCita | null>(null);
  const [diaSeleccionado, setDiaSeleccionado] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [diasSerie, setDiasSerie] = useState(14);
  // `null` = el mes actual. Se guardan por separado para que "anterior" y
  // "siguiente" funcionen desde cualquier mes, no solo desde el actual.
  const [mesVista, setMesVista] = useState<{ anio: number; mes: number } | null>(null);

  const cargar = useCallback(async () => {
    setIsLoading(true);
    try {
      // Todas las peticiones en paralelo: son 6 y ninguna depende de otra.
      // En cascada el panel tardaria 6x lo que necesita.
      const [s, k, t, se, w, a, c] = await Promise.all([
        dashboardApi.getScope(),
        dashboardApi.getKpis(),
        dashboardApi.getToday(),
        dashboardApi.getSerie(diasSerie),
        dashboardApi.getWorkload(),
        dashboardApi.getSchedule(),
        dashboardApi.getCalendario(mesVista?.anio, mesVista?.mes),
      ]);
      setScope(s);
      setKpis(k);
      setHoy(t);
      setSerie(se);
      setWorkload(w);
      setAgenda(a);
      setCalendario(c);
    } catch (error: any) {
      // 403 = el usuario no tiene rol de agenda. Es una situacion prevista, no
      // un fallo: se dice que es y no se muestra un error rojo generico.
      if (error?.response?.status === 403) {
        toast.error('Su rol no tiene acceso al panel operativo.');
      } else {
        toast.error('No se pudieron cargar los datos del panel.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [diasSerie, mesVista]);

  /** Cambia de mes y recarga solo el calendario, no todo el panel. */
  const moverMes = useCallback((delta: number) => {
    const hoy = new Date();
    const base = mesVista ?? { anio: hoy.getFullYear(), mes: hoy.getMonth() + 1 };
    let mes = base.mes + delta;
    let anio = base.anio;
    if (mes < 1) {
      mes = 12;
      anio -= 1;
    } else if (mes > 12) {
      mes = 1;
      anio += 1;
    }
    setMesVista({ anio, mes });
  }, [mesVista]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <Loader2 className="animate-spin mb-3" size={32} />
        <p className="text-sm">Cargando panel...</p>
      </div>
    );
  }

  // El titulo dice que se esta viendo, porque el alcance cambia por rol y una
  // pantalla sin etiqueta no deja claro si los numeros son propios o de la
  // clinica entera.
  const titulo = scope?.es_admin
    ? 'Panel de la clinica'
    : esMedico
      ? 'Mi agenda'
      : esAsistente
        ? 'Agenda de mis especialistas'
        : 'Panel';

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-medical-textMain">{titulo}</h2>
          <p className="text-sm text-medical-textMuted">
            {hoy
              ? `${hoy.cerradas} de ${hoy.total} citas resueltas hoy`
              : 'Resumen de la actividad clinica'}
          </p>
        </div>
        <button
          onClick={cargar}
          disabled={isLoading}
          className="p-2 text-slate-400 hover:text-medical-primary transition-colors disabled:opacity-50"
          title="Actualizar"
          aria-label="Actualizar datos"
        >
          <RefreshCw size={20} />
        </button>
      </div>

      {kpis && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            titulo="Citas hoy"
            valor={kpis.citas_hoy}
            icono={CalendarDays}
            colorIcono="bg-medical-primary"
            detalle={`${kpis.citas_hoy_confirmadas} confirmadas, ${kpis.citas_hoy_pendientes} por confirmar`}
          />
          <StatCard
            titulo="Atendidas este mes"
            valor={kpis.atendidas_mes}
            icono={CalendarCheck}
            colorIcono="bg-medical-personal"
            detalle={`${kpis.tasa_asistencia_pct}% de las citas resueltas`}
          />
          <StatCard
            titulo="Inasistencias"
            valor={kpis.inasistencias_mes}
            icono={UserX}
            colorIcono="bg-medical-danger"
            detalle={`${kpis.tasa_inasistencia_pct}% de las citas ya vencidas`}
          />
          <StatCard
            titulo="Esta semana"
            valor={kpis.citas_semana}
            icono={TrendingUp}
            colorIcono="bg-medical-visit"
            detalle={`${kpis.citas_mes} en lo que va de mes`}
          />
        </div>
      )}

      {/*
        Sin `items-stretch` ni alturas forzadas: cada card mide lo que necesita
        su contenido. Intentar igualarlos genera huecos en los dos sentidos: con
        18 citas la agenda crecia a 792px y dejaba 490px de blanco bajo "Estado
        del dia".

        Ahora las dos columnas terminan a alturas parecidas porque su contenido
        es parecido, no porque se fuerce nada. La agenda lleva `max-h` con
        scroll propio para que 40 citas no alarguen la pagina entera.
      */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8 items-start">
        {hoy && (
          <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-lg font-semibold text-medical-textMain mb-5">
              Estado del dia
            </h3>
            <DistribucionEstados resumen={hoy} />
          </div>
        )}

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-baseline justify-between mb-4">
            <h3 className="text-lg font-semibold text-medical-textMain">
              Agenda de hoy
            </h3>
            {agenda && agenda.total > 0 && (
              <span className="text-xs text-medical-textMuted">
                {agenda.total} {agenda.total === 1 ? 'cita' : 'citas'}
              </span>
            )}
          </div>
          {/* `overscroll-contain` evita que al llegar al final siga
              desplazando la pagina de detras. */}
          <div className="-mx-2 px-2 max-h-[26rem] overflow-y-auto overscroll-contain">
            {agenda && (
              <AgendaDelDia citas={agenda.citas} onSelectCita={setCitaAbierta} />
            )}
          </div>
          {agenda && agenda.total > 5 && (
            <p className="mt-3 pt-3 border-t border-slate-100 text-[11px] text-medical-textMuted flex items-center gap-1">
              <ChevronDown size={12} />
              Desplace para ver las {agenda.total} citas
            </p>
          )}
        </div>
      </div>

      {calendario && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <CalendarioMensual
            calendario={calendario}
            seleccionado={diaSeleccionado}
            onSeleccionar={setDiaSeleccionado}
            onMesAnterior={() => moverMes(-1)}
            onMesSiguiente={() => moverMes(1)}
          />
        </div>
      )}

      <DetalleCitaModal cita={citaAbierta} onClose={() => setCitaAbierta(null)} />

      {serie && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-semibold text-medical-textMain">
              Actividad por dia
            </h3>
            <div className="flex gap-1">
              {[7, 14, 30].map((opcion) => (
                <button
                  key={opcion}
                  onClick={() => setDiasSerie(opcion)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    diasSerie === opcion
                      ? 'bg-medical-primary text-white'
                      : 'bg-slate-100 text-medical-textMuted hover:bg-slate-200'
                  }`}
                >
                  {opcion} dias
                </button>
              ))}
            </div>
          </div>
          <SerieDiaria datos={serie.data} />
        </div>
      )}

      {workload && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 mb-5">
            <Users size={20} className="text-medical-primary" />
            <h3 className="text-lg font-semibold text-medical-textMain">
              Carga por medico
            </h3>
          </div>
          <CargaPorMedico datos={workload.data} />
        </div>
      )}

      {scope?.es_admin && (
        <p className="flex items-center gap-2 text-xs text-medical-textMuted">
          <Activity size={14} />
          Estas viendo toda la clinica. Los Especialistas y Asistentes ven
          unicamente las citas de su alcance.
        </p>
      )}
    </div>
  );
};

export default DashboardPage;
