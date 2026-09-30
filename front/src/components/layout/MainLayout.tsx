import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAuth } from '../../contexts/AuthContext';
import { mensajeDeCierre } from '../../contexts/AuthContext';

/**
 * Contenedor principal.
 *
 * ## Por que el menu es un cajon y no una columna fija
 *
 * El sidebar medía `w-64` (256px) fijo con `p-8` de padding: en un movil de
 * 375px quedaban 119px de contenido, menos de lo que ocupa un boton. No habia
 * forma de plegarlo, asi que en telefono la aplicacion era inservible.
 *
 * Ahora el sidebar es fijo solo a partir de `lg` (1024px). Por debajo es un
 * cajon que se abre encima del contenido, con tres detalles que suelen
 * olvidarse y convierten un drawer en una trampa:
 *
 * 1. Se cierra al navegar. Un menu que no se cierra al pulsar deja al usuario
 *    esperando una pantalla que no llega.
 * 2. Se cierra con Escape. Es la unica forma de cerrarlo sin raton.
 * 3. Bloquea el scroll del fondo. Un drawer sobre un cuerpo que sigue
 *    desplazandose se percibe como roto.
 *
 * El fondo se marca como `aria-hidden` mientras el cajon esta abierto, para
 * que un lector de pantalla no lea el contenido que queda tapado.
 */
const MainLayout: React.FC = () => {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const location = useLocation();
  const { motivoCierre } = useAuth();

  // Se cierra al cambiar de ruta.
  useEffect(() => {
    setMenuAbierto(false);
  }, [location.pathname]);

  // Escape cierra el cajon.
  useEffect(() => {
    if (!menuAbierto) return;
    const alPulsar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuAbierto(false);
    };
    document.addEventListener('keydown', alPulsar);
    return () => document.removeEventListener('keydown', alPulsar);
  }, [menuAbierto]);

  // Bloquea el scroll del fondo mientras el cajon esta abierto.
  useEffect(() => {
    document.body.style.overflow = menuAbierto ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuAbierto]);

  // Sesion caducada: se bloquea la pagina sin recargar el navegador. Perder
  // los datos ya en pantalla es justo lo que se pide: la pagina abierta deja
  // de ser usable y el usuario debe volver a autenticarse.
  const cerrada = mensajeDeCierre(motivoCierre);
  if (cerrada) {
    return <SesionCerrada mensaje={cerrada} />;
  }

  return (
    <div className="min-h-screen bg-medical-background flex">
      {/* Capa oscura: solo en movil, y solo si el cajon esta abierto. */}
      {menuAbierto && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMenuAbierto(false)}
          aria-hidden="true"
        />
      )}

      <div
        className={`
          fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-out
          lg:static lg:translate-x-0 lg:z-auto
          ${menuAbierto ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <Sidebar alNavegar={() => setMenuAbierto(false)} />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <Header alAbrirMenu={() => setMenuAbierto(true)} menuAbierto={menuAbierto} />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

/**
 * Pantalla de sesion cerrada.
 *
 * Es un `full-screen` opaco, no un overlay: nada de lo que hubiera debajo
 * queda accesible, ni con el teclado ni con el inspector.
 */
const SesionCerrada: React.FC<{ mensaje: string }> = ({ mensaje }) => {
  const { logout } = useAuth();
  return (
    <div className="min-h-screen bg-medical-background flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 max-w-md w-full text-center">
        <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-7 h-7 text-amber-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.69-1.33-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z"
            />
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-medical-textMain mb-2">
          Sesion cerrada
        </h1>
        <p className="text-sm text-medical-textMuted mb-6">{mensaje}</p>
        <button
          onClick={logout}
          className="w-full px-4 py-2.5 text-sm font-semibold text-white rounded-lg bg-medical-primary hover:opacity-90 transition-opacity"
        >
          Volver a iniciar sesion
        </button>
      </div>
    </div>
  );
};

export default MainLayout;
