# Frontend

Convenciones de `front/`. Verificado el 2026-09-30.

## Stack

React 18 · TypeScript 5 · Vite 5 · Tailwind 3 · react-router 6 · axios ·
react-hook-form · react-hot-toast · lucide-react · i18next.

**No hay** ESLint, ni Prettier, ni framework de tests. Node 20 (según
`Dockerfile.front`). No los introduzcas sin pedirlo.

---

## Estructura

```
front/src/
├── main.tsx              # montaje
├── App.tsx               # BrowserRouter + Toaster
├── routes/AppRoutes.tsx  # 15 rutas bajo ProtectedRoute
├── pages/                # 15 páginas, una por módulo
├── components/
│   ├── common/           # DataTable, Modal, FilterButtons, Skeleton, ...
│   └── layout/           # MainLayout, Sidebar, Header, ProtectedRoute
├── api/                  # 17 módulos `xxxApi.ts` + axiosInstance + tokenStorage
├── auth/roles.ts         # roles canónicos (espejo de core/rbac.py)
├── contexts/             # AuthContext, UnsavedChangesContext
├── styles/index.css
└── types/env.d.ts
```

---

## Colores: usa los tokens

```tsx
className="bg-medical-primary text-medical-textMain border-medical-operation"
```

| Uso | Hex | Token |
|---|---|---|
| Consultas | `#2C5AA0` | `bg-medical-primary` |
| Operaciones | `#D22B2B` | `bg-medical-operation` |
| Visitas | `#F57C00` | `bg-medical-visit` |
| Personal | `#2E7D32` | `bg-medical-personal` |
| Texto principal | `#1E293B` | `text-medical-textMain` |
| Texto secundario | `#64748B` | `text-medical-textMuted` |
| Fondo página | `#F8FAFC` | `bg-medical-background` |

> **Trampa histórica:** el tema definía `medicalText.main` (que genera
> `text-medicalText-main`) mientras el código usaba `text-medical-textMain`.
> Tailwind no emitía las clases y **130+ estilos se perdían en silencio**.
> `tailwind.config.js` ahora define ambos nombres y `make verify-docs` falla si
> aparece una clase `medical-*` sin definir.

No escribas hex sueltos en JSX. Si necesitas un color nuevo, agrégalo al tema.

---

## Roles

```tsx
import { isAdmin, hasRole, DOCTOR, SPECIALIST, ASSISTANT } from '../auth/roles';

const admin = isAdmin(user?.role);
const medico = hasRole(user?.role, [DOCTOR, SPECIALIST]);
```

Nunca `user?.role === 'admin'`. Antes se comparaba contra `'admin'` y
`'super-admin'` en minúsculas, pero la BD guarda `SUPER_ADMIN`: la UI nunca
reconocía a un administrador y le ocultaba acciones ejecutables.

`hasRole()` normaliza igual que el backend (`super-admin`, `super_admin`,
`SUPERAdmin` → `SUPER_ADMIN`).

---

## Tokens

```ts
// front/src/api/tokenStorage.ts  ← única fuente de verdad
import { getAccessToken, setTokens, clearTokens } from '../api/tokenStorage';
```

> Antes `AuthContext` leía `auth_token` y `axiosInstance` leía `access_token`.
> Funcionaba solo porque el login escribía ambas por accidente, y `logout()`
> olvidaba borrar `access_token`, dejando un token vivo tras cerrar sesión.

No llames `localStorage` para tokens. No llames `localStorage` para nada fuera
de un módulo de almacenamiento dedicado.

---

## Cliente HTTP

Dos instancias, y está bien:

| Instancia | baseURL | Uso |
|---|---|---|
| `axiosInstance.ts` | `/api/v1` (relativa) | 14 de 17 módulos. Usa el proxy de Vite |
| `api.ts` | `http://localhost:5435` (absoluta) | Solo `authApi`, por el flujo de refresh |

En desarrollo, `vite.config.ts` hace proxy de `/api` → `VITE_API_BASE_URL` o
`http://localhost:5435`. Por eso `axiosInstance` usa una ruta relativa.

`axiosInstance` inyecta el token y, en `401`, limpia sesión y redirige a
`/login`. **No** repitas esa lógica en tus módulos.

---

## Convenciones de API

- Un archivo por entidad: `front/src/api/<entidad>Api.ts`.
- Exporta un objeto: `export const patientApi = { async getAll() {...} }`.
- Desenvuelve siempre: `return response.data`.
- Sin `try/catch` en la capa API. Los errores los maneja quien llama, con
  `toast.error(...)`.
- Tipos **inline** en el mismo archivo, no en `src/types/` (que solo tiene
  `env.d.ts`).

```ts
// Patrón canónico
export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export const patientApi = {
  async getAll(skip = 0, limit = 100) {
    const response = await axiosInstance.get(`/patients/?skip=${skip}&limit=${limit}`);
    return response.data;
  },
};
```

### Paginación

- `appointments`: paginada de verdad → `{items, total, page, page_size, total_pages}`
- Todo lo demás: `skip`/`limit`

No unifiques esto sin revisar los 15 módulos que dependen del comportamiento
actual.

---

## Estado

Context + hooks. Sin librería global.

```tsx
const { user, isAuthenticated, login, logout } = useAuth();
```

El estado de servidor vive en `useState` + `useEffect` dentro de cada página.
No hay caché compartida.

> `api/cache.ts` implementa una caché con TTL en localStorage pero **nadie lo
> importa**. O lo usas o lo borras; no lo dejes a medias.

---

## Formularios

`react-hook-form`:

```tsx
const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Cita>();
```

Errores: se muestran con `toast.error(...)`, no con errores de campo. Convención
del proyecto actual, no ideal, pero consistente.

---

## Componentes compartidos

Ya existen en `components/common/`:

| Componente | Para qué |
|---|---|
| `DataTable` | Tabla con paginación y orden |
| `Modal` | Diálogo modal |
| `FilterButtons` | Filtros por estado |
| `AppointmentActions` | Acciones según estado de cita |
| `Skeleton`, `TableSkeleton`, `CardSkeleton` | Estados de carga |
| `ErrorBoundary` | Captura de errores |
| `NotificationBell` | Campana de notificaciones |

> **No existe** un `Button`, `Input` ni `Card` compartido. El botón primario
> está copiado en 5 archivos y el input en ~30. Extraerlos es deuda
> worthwhile (ver `docs/PENDIENTES.md`).

---

## Convenciones de estilo

- **Comentarios y textos en español**
- Páginas con `p-8 overflow-y-auto`, tarjetas `bg-white rounded-2xl shadow-sm border border-slate-200`
- Iconos de `lucide-react` (inline solo en `DataTable`)
- Título de página `text-2xl font-bold`, sección `text-lg font-semibold`

---

## Límite de tamaño

**Máximo 250 líneas por módulo.** El archivo original pedía 8 líneas por
componente; las 15 páginas lo violaban (la mayor, `AppointmentsPage.tsx`, tenía
793). Ese límite era inalcanzable y por eso no significaba nada. 250 sí es
exigente.

Al pasarte, extrae componentes, hooks o constantes. `AppointmentsPage.tsx` es el
caso más urgente: lista, formulario, modal de reagendamiento y filtros de
reagendamiento por IA están en un solo archivo.

---

## i18n: actualmente no se usa

`i18n.ts` inicializa i18next con 13 claves (`es` con fallback `en`), pero
**ningún componente llama a `useTranslation()`**. Todo el texto visible es
español hardcodeado en el JSX.

No escribas `t('...')` esperando que funcione: la clave no existe en ningún sitio.
O traduces de verdad (y mueves las claves a archivos JSON), o dejas el texto
hardcodeado como está el resto. Ver `docs/PENDIENTES.md`.

---

## Antes de entregar

```bash
cd front
npm run typecheck     # tsc --noEmit: debe salir limpio
npm run build         # debe completar sin errores
```

`strict: true`, `noUnusedLocals: true` y `noUnusedParameters: true` están
activos: un import sin usar **rompe la compilación**.