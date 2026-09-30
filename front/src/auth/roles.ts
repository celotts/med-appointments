/**
 * Roles: fuente unica de verdad en el frontend.
 *
 * Antes cada componente comparaba strings literales:
 *   user?.role === 'admin' || user?.role === 'super-admin'
 * Mientras la BD guarda SUPER_ADMIN / ADMIN / DOCTOR / SPECIALIST /
 * ASSISTANT / PATIENT. La comparacion nunca coincidia, asi que a un
 * administrador real le ocultaban acciones que si podia ejecutar.
 *
 * Este modulo replica la normalizacion de backend/app/core/rbac.py.
 * Si cambias un rol aqui, cambialo tambien alla.
 */

export const SUPER_ADMIN = 'SUPER_ADMIN';
export const ADMIN = 'ADMIN';
export const DOCTOR = 'DOCTOR';
export const SPECIALIST = 'SPECIALIST';
export const ASSISTANT = 'ASSISTANT';
export const PATIENT = 'PATIENT';

/** Roles con permisos de administracion de la clinica. */
export const ADMIN_ROLES = [SUPER_ADMIN, ADMIN] as const;

/**
 * Roles que llevan la agenda sin ser administradores: el especialista y el
 * asistente. Es el conjunto que consume el dashboard operativo.
 *
 * Espejo de `AGENDA_ROLES` en backend/app/core/rbac.py.
 */
export const AGENDA_ROLES = [DOCTOR, SPECIALIST, ASSISTANT] as const;

/** Alias historicos que se normalizan al rol canonico. */
const ALIASES: Record<string, string> = {
  SUPERADMIN: SUPER_ADMIN,
  ROOT: SUPER_ADMIN,
  SUPERUSUARIO: SUPER_ADMIN,
  SECRETARIA: ASSISTANT,
  RECEPCION: ASSISTANT,
  RECEPCIONISTA: ASSISTANT,
  MEDICO: DOCTOR,
};

/**
 * Normaliza un nombre de rol a su forma canonica en mayusculas.
 * Acepta cualquier variante: 'super-admin', 'super_admin', 'SuperAdmin'.
 */
export function normalizeRole(role: string | null | undefined): string {
  if (!role) return '';
  const raw = role
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  if (!raw) return '';
  return ALIASES[raw] ?? raw;
}

/** Devuelve true si el rol del usuario esta en la lista permitida. */
export function hasRole(
  role: string | null | undefined,
  allowed: readonly string[]
): boolean {
  const actual = normalizeRole(role);
  if (!actual) return false;
  return allowed.some((permitido) => normalizeRole(permitido) === actual);
}

/** Atajo: el usuario es administrador de la clinica. */
export function isAdmin(role: string | null | undefined): boolean {
  return hasRole(role, ADMIN_ROLES);
}

/** Atajo: el usuario opera clinicamente (medico, especialista o asistente). */
export function isClinical(role: string | null | undefined): boolean {
  return hasRole(role, [SUPER_ADMIN, ADMIN, DOCTOR, SPECIALIST, ASSISTANT]);
}