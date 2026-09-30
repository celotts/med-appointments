import React from 'react';
import type { SeriePunto } from '../../api/dashboardApi';

interface Props {
  datos: SeriePunto[];
}

/**
 * Serie diaria como barras apiladas, en SVG puro.
 *
 * Sin libreria de graficas a proposito: el bundle no crece y estas series son
 * barras, no curvas. Una linea temporal real (tiempo de espera, duracion)
 * si necesitaria una, y cuando haga falta se agrega con autorizacion.
 *
 * ## Por que NO se usa `preserveAspectRatio="none"`
 *
 * Con `none`, el SVG se estira en X y en Y por separado para llenar el
 * contenedor. Las barras se deforman sin que se note, pero el TEXTO tambien:
 * las cifras del eje se aplastan horizontalmente y "23" se lee "|3". Es un
 * efecto sutil en una captura y evidente en uso real.
 *
 * Sin ese atributo, el grafico escala de forma uniforme y el texto mantiene
 * su proporcion. Se reserva margen izquierdo para las cifras del eje, de modo
 * que no caigan encima de la primera barra.
 *
 * Ver `docs/FRONTEND.md`.
 */

// Dimensiones del lienzo virtual. El SVG escala hacia arriba o hacia abajo de
// forma uniforme; `alto` incluye los margenes superior e inferior.
const ANCHO = 660;
const ALTO = 200;
// Margen izquierdo reservado a las cifras del eje. Sin el, la primera barra
// (que arranca en x=0) se solapa con los numeros.
const MARGEN_IZQ = 30;
const MARGEN_DER = 6;
const MARGEN_SUP = 10;
const MARGEN_INF = 24;

const SerieDiaria: React.FC<Props> = ({ datos }) => {
  if (!datos.length) {
    return (
      <p className="py-12 text-center text-sm text-slate-400 italic">
        Sin datos en el periodo seleccionado.
      </p>
    );
  }

  const maximo = Math.max(...datos.map((p) => p.total), 1);
  const anchoUtil = ANCHO - MARGEN_IZQ - MARGEN_DER;
  const alturaUtil = ALTO - MARGEN_INF - MARGEN_SUP;

  const separacion = anchoUtil / datos.length;
  const anchoBarra = Math.max(separacion * 0.6, 2);

  // Cuatro lineas de referencia: suficientes para leer magnitud sin recargar
  // el grafico de numeros.
  const lineas = [0, 0.5, 1].map((fraccion) => ({
    y: MARGEN_SUP + alturaUtil * (1 - fraccion),
    valor: Math.round(maximo * fraccion),
  }));

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        className="w-full h-auto"
        role="img"
        aria-label={`Citas por dia, maximo ${maximo} en ${datos.length} dias`}
      >
        {lineas.map((linea) => (
          <g key={linea.y}>
            <line
              x1={MARGEN_IZQ}
              x2={ANCHO - MARGEN_DER}
              y1={linea.y}
              y2={linea.y}
              stroke="#e2e8f0"
              strokeWidth={1}
            />
            {/* `text-anchor="end"` y `x` antes del margen: las cifras quedan a
                la izquierda de la rejilla y nunca encima de una barra. */}
            <text
              x={MARGEN_IZQ - 6}
              y={linea.y + 3}
              fontSize={10}
              fill="#94a3b8"
              textAnchor="end"
            >
              {linea.valor}
            </text>
          </g>
        ))}

        {datos.map((punto, indice) => {
          const x = MARGEN_IZQ + indice * separacion + (separacion - anchoBarra) / 2;
          const escala = (cantidad: number) => (cantidad / maximo) * alturaUtil;

          const hAtendidas = escala(punto.atendidas);
          const hCanceladas = escala(punto.canceladas);
          const hInasistencias = escala(punto.inasistencias);
          const hPendientes = Math.max(
            0,
            escala(punto.total) - hAtendidas - hCanceladas - hInasistencias
          );

          const base = MARGEN_SUP + alturaUtil;
          let cursor = base;

          const tramos = [
            { valor: hPendientes, clase: 'fill-slate-300' },
            { valor: hInasistencias, clase: 'fill-medical-danger' },
            { valor: hCanceladas, clase: 'fill-medical-warning' },
            { valor: hAtendidas, clase: 'fill-medical-personal' },
          ];

          return (
            <g key={punto.dia}>
              <title>
                {`${punto.dia}: ${punto.total} citas (${punto.atendidas} atendidas, ${punto.canceladas} canceladas, ${punto.inasistencias} inasistencias)`}
              </title>
              {tramos.map((tramo, i) => {
                if (tramo.valor <= 0) return null;
                cursor -= tramo.valor;
                return (
                  <rect
                    key={i}
                    x={x}
                    y={cursor}
                    width={anchoBarra}
                    height={tramo.valor}
                    className={tramo.clase}
                  />
                );
              })}
              {/* La fecha solo si cabe: con 30 dias, rotarla es mas legible que
                  apretar 30 numeros en 660px de ancho. */}
              {datos.length <= 16 && (
                <text
                  x={x + anchoBarra / 2}
                  y={ALTO - 8}
                  fontSize={10}
                  fill="#94a3b8"
                  textAnchor="middle"
                >
                  {punto.dia.slice(8)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-4 mt-3 text-xs text-medical-textMuted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-medical-personal" /> Atendidas
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-medical-warning" /> Canceladas
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-medical-danger" /> Inasistencias
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-slate-300" /> Pendientes
        </span>
        {datos.length > 16 && (
          <span className="text-slate-400">
            {datos.length} dias, del {datos[0].dia.slice(8)} al {datos[datos.length - 1].dia.slice(28)}
          </span>
        )}
      </div>
    </div>
  );
};

export default SerieDiaria;
