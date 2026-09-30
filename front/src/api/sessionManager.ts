/**
 * Manejo de sesion: un unico lugar decide cuando caduca.
 *
 * ## El problema que resuelve
 *
 * Cada modulo hacia su propia version de "el token caduco": el interceptor de
 * axios hacia `window.location.href = '/login'`, `AuthContext` hacia un
 * `setInterval` de 30 s, y `login.ts` hacia nada. Con varias peticiones en
 * vuelo (el panel hace 6 a la vez), cada una recibia su 401 y cada una
 * recargaba la pagina: seis recargas y seis avisos.
 *
 * Aqui se centraliza: `expire()` es idempotente, notifica a los suscriptores
 * una sola vez y el componente que decide que se ve es `AuthContext`. Un solo
 * lugar, un solo aviso, una sola transicion.
 *
 * ## Orden de las tres barreras
 *
 * 1. `tokenStorage.isTokenExpired()` — antes de SENDING, en local. Avisa al
 *    instante y sin gastar red.
 * 2. El interceptor de axios responde 401 — el servidor siempre es la fuente
 *    de verdad: un token puede seguir vigente en el reloj del navegador y
 *    haber sido revocado en la BD.
 * 3. `expire()` — el unico que limpia y notifica.
 *
 * Ver `docs/SEGURIDAD.md`.
 */

type MotivoExpulsion = 'expirado' | 'revocado' | 'invalido';

interface Suscriptor {
  (motivo: MotivoExpulsion): void;
}

let sospechoso: Suscriptor | null = null;
let yaExpulsado = false;

/**
 * Cierra la sesion y avisa a quien este escuchando.
 *
 * Idempotente: llamarla dos veces por el mismo motivo no duplica el aviso ni
 * la transicion de estado. Sin esto, seis peticiones que fallan a la vez
 * producen seis avisos.
 */
export function expire(motivo: MotivoExpulsion = 'expirado'): void {
  if (yaExpulsado) return;
  yaExpulsado = true;

  try {
    sospechoso?.(motivo);
  } catch (error) {
    // Un suscriptor que falla no debe impedir que los demas se enteren.
    console.error('Error notificando la expiracion de sesion', error);
  }
}

/** Marca la sesion como viva. La llama el login y el desbloqueo manual. */
export function revivir(): void {
  yaExpulsado = false;
}

/**
 * Registra al unico suscriptor. Devuelve la funcion para darlo de baja.
 *
 * Se admite uno solo a proposito: dosuscripciones significan dos fuentes de
 * verdad sobre el mismo estado.
 */
export function suscribir(fn: Suscriptor): () => void {
  sospechoso = fn;
  return () => {
    if (sospechoso === fn) sospechoso = null;
  };
}

/** Utiles para diagnostico y para los tests. */
export function estaExpulsado(): boolean {
  return yaExpulsado;
}
