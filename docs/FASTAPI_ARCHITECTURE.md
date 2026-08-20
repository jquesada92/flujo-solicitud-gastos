# Arquitectura FastAPI

## Application factory

`app/application.py` crea aplicación, middleware, lifespan mínimo, health endpoint y routers. `app/main.py` permanece como alias de compatibilidad.

Dominios/rutas canónicas relevantes:

```text
request_actions.py       → creación
revision_actions.py      → corregir / reenviar
cancellation_actions.py  → cancelación
closure_delegation.py    → delegación cierre/factura
quotation_actions.py     → votación
document_actions.py      → documentos
financial_actions.py     → factura / cierre
my_actions.py            → acciones contextuales
tracking.py              → dashboard + seguimiento
position_access.py       → Cargo → Rol
areas.py                 → configuración Área/Categoría
```

## Capas

```text
api/       HTTP/dependencias/status codes
schemas/   contratos Pydantic
services/  reglas de negocio reutilizable
models/    persistencia SQLAlchemy
core/      Settings, DB, seguridad, rate limiting
```

SQLAlchemy es síncrono; rutas con I/O bloqueante usan `def` para el threadpool de FastAPI.

## Settings y ambiente

`ENVIRONMENT=production` gobierna la segregación funcional. `RENDER=true` puede influir en hardening del runtime, pero no sustituye `ENVIRONMENT=production` para autorización.

## IAM

Fuentes configurables:

```text
baseline requests:read
permiso directo
rol directo
Grupo → Rol → Permiso
Cargo → Rol → Permiso
```

Permisos vigentes:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage  # system-only
```

`requests:close` queda como registro legacy inactivo desde `0005`.

### `config:manage`

`iam_service.SYSTEM_ONLY_PERMISSION_CODES` contiene `config:manage`.

Para usuarios ordinarios una asignación de ese código no produce permiso efectivo.

### `config:read`

Permite GET/HEAD de Configuración según los routers autorizados, pero no satisface mutaciones.

El frontend usa este permiso para Accesos/Áreas/Reglas/Auditoría en modo solo lectura.

### `areas:manage`

Protege mutaciones de `/api/areas` y relaciones Área ↔ Categoría.

## Accesos como superficie única

La administración de Usuarios, Grupos, Roles, Permisos y Cargos se concentra en:

```text
Configuración → Accesos
```

Usuarios/Personas y Organigrama no son pantallas independientes de la arquitectura objetivo.

Las APIs IAM permanecen; la consolidación es de superficie y navegación, no una eliminación del modelo persistido.

## Cuenta técnica

Se identifica por `system_accounts` y se expone mediante `is_system_account`.

Producción:

```text
requests:read
areas:manage
config:read
config:manage
```

No participa en aprobación/votación. Conserva excepciones administrativas por recurso para cancelar, corregir y gestionar cierre/factura.

## Capacidades por recurso

```text
can_cancel
= estado cancelable AND (requester OR system_accounts)

can_correct
= estado corregible AND (requester OR system_accounts)

can_close
= status ∈ {APPROVED, CLOSED}
  AND (requester OR system_accounts OR active_closure_delegate)

can_delegate_close
= requester original
```

No son permisos IAM.

## Seguimiento universal

`tracking.py` expone:

```text
GET /api/expenses
GET /api/expenses/dashboard
```

ambos bajo `requests:read` y con capacidades por recurso calculadas por actor.

## Resolver de acciones personales

```text
APPROVAL_DECISION = requests:approve + Approval.PENDING + PENDING_APPROVAL
QUOTATION_VOTE    = requests:approve + invitación vigente + QUOTATION_VOTING + sin voto
CORRECT_REQUEST   = NEEDS_REVISION + requester
CLOSE_REQUEST     = APPROVED + (requester OR active_closure_delegate)
```

## Enviar a revisión

`REVISION_REQUESTED` se procesa antes de mayoría y requiere comentario >= 3.

```text
Approval → REVISION_REQUESTED
Expense  → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester → CORRECT_REQUEST
```

## Invariant SIMPLE/MULTI_QUOTE

Corrección no cambia el tipo:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

## Contrato Área + Categoría

Nuevo código backend usa:

```text
expense_area
expense_category
```

Pydantic puede aceptar aliases legacy temporalmente para rollout, pero serialización/persistencia canónica usa los nombres nuevos.

Alembic `0008` renombra las columnas físicas de `expenses`.

## Frontend modular / bridges legacy

Componentes relevantes:

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/closure-delegation.jsx
frontend/src/iam-admin.jsx
frontend/src/access-navigation-bridge.js
frontend/src/config-readonly.js
frontend/src/classification-admin.js
```

Mientras partes de `main.jsx` sigan legacy, `vite.config.js` puede aplicar bridges fail-fast.

### Navegación de Accesos

Accesos se monta con `#access-management`.

`access-navigation-bridge.js` se carga antes de `main.jsx` y escucha la topbar en capture phase para retirar el hash antes de que React procese el destino.

Debe cubrir incluso el caso donde el destino ya sea la pestaña subyacente activa.

Abrir/cerrar únicamente el dropdown Configuración no abandona Accesos; seleccionar una opción navegable sí.

## Response models

`UserOut` expone:

```text
permission_codes
is_system_account
```

Los aliases `can_*` de sesión pueden permanecer temporalmente, pero no son autoridad backend.

`ExpenseOut` expone capacidades por recurso.

## Alembic

Cadena vigente:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

```text
0006 → areas:manage
0007 → config:read
0008 → expense_area / expense_category
```

El entrypoint ejecuta:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Una base con `alembic_version` apuntando a una revisión inexistente debe resolverse sincronizando la cadena correcta, no ocultando el problema con `stamp`.

## Testing

Contratos mínimos:

- autorización por permisos efectivos;
- `config:read` sin mutaciones;
- `config:manage` system-only;
- `areas:manage` aislado;
- capacidades por recurso;
- migraciones 0000→0008;
- `expense_area` / `expense_category` en API/ORM/DB;
- build Vite;
- navegación de topbar desde Accesos;
- `test_access_navigation_bridge.py`.
