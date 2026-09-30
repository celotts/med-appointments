import React, { useCallback, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /** Ancho maximo: `md` para un detalle, `lg` para un formulario. */
  tamano?: 'md' | 'lg' | 'xl';
}

/**
 * Modal base del proyecto.
 *
 * Lo que hace bien
 *
 * - `Escape` cierra.
 * - Clic en el fondo cierra, pero solo si el clic es en el fondo: si se
 *   comprueba `e.target === overlay`, un clic dentro del contenido no cierra.
 * - Bloquea el scroll del cuerpo mientras esta abierto.
 * - Baja el z-index del header con la clase `modal-open`, para que el modal
 *   quede por encima de todo.
 * - `role="dialog"` + `aria-modal="true"` + `aria-labelledby`: sin esto un
 *   lector de pantalla no anuncia que se abrio una ventana nueva.
 *
 * Trampa de foco
 *
 * Sin `focus-trap`, al pulsar Tab repetidamente el foco se sale del modal y
 * acaba en los botones de la pagina que hay detras, que siguen siendo
 * tabulables aunque esten tapados. Es el fallo de accesibilidad mas grave de
 * los modales y el que mas se olvida.
 *
 * Al abrir se guarda el elemento que tenia el foco y se le devuelve al cerrar,
 * para que el usuario no pierda el sitio: si abria el detalle de una cita,
 * al cerrarlo el foco vuelve a esa fila y no al principio de la pagina.
 */
const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, tamano = 'md' }) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contenidoRef = useRef<HTMLDivElement>(null);
  const focoPrevio = useRef<HTMLElement | null>(null);

  // Foco en el primer elemento interactivo del modal, no en el contenedor:
  // un contenedor con tabIndex=-1 announces el titulo pero no deja escribir
  // en ningun sitio, y en iOS los campos fuera de pantalla no abren el
  // teclado.
  const enfocarDentro = useCallback(() => {
    const raiz = contenidoRef.current;
    if (!raiz) return;
    const enfocables = raiz.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (enfocables.length > 0) {
      enfocables[0].focus();
    } else {
      raiz.focus();
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const alPulsar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const raiz = contenidoRef.current;
      if (!raiz) return;
      const enfocables = Array.from(
        raiz.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => el.offsetParent !== null);
      if (enfocables.length === 0) {
        e.preventDefault();
        return;
      }
      const primero = enfocables[0];
      const ultimo = enfocables[enfocables.length - 1];

      // Tab en el ultimo devuelve el foco al primero: el foco no sale del modal.
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };

    focoPrevio.current = document.activeElement as HTMLElement | null;
    document.addEventListener('keydown', alPulsar);
    document.body.style.overflow = 'hidden';
    document.body.classList.add('modal-open');
    // Tras el pintado: si se enfoca antes, el contenedor aun no tiene layout.
    const t = window.setTimeout(enfocarDentro, 50);

    return () => {
      document.removeEventListener('keydown', alPulsar);
      document.body.style.overflow = '';
      document.body.classList.remove('modal-open');
      window.clearTimeout(t);
      // Se devuelve el foco a donde estaba para no perder el sitio.
      focoPrevio.current?.focus?.();
    };
  }, [isOpen, onClose, enfocarDentro]);

  if (!isOpen) return null;

  const ancho = { md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-2xl' }[tamano];

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm transition-opacity"
      onClick={(e) => e.target === overlayRef.current && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        ref={contenidoRef}
        tabIndex={-1}
        className={`bg-white rounded-2xl shadow-2xl w-full ${ancho} overflow-hidden transform transition-all animate-in fade-in zoom-in-95 duration-200 m-4 focus:outline-none`}
      >
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <h3 id="modal-title" className="text-lg font-bold text-medical-textMain">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-200 hover:text-slate-600 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-medical-primary"
            aria-label="Cerrar"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-6 max-h-[70vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
};

export default Modal;
