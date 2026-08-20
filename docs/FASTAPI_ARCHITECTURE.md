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

Persistencia PostgreSQL:

```text
DATABASE_URL=<conexión a database ph_torre_delta>
DATABASE_SCHEMA=administracion
```

`DATABASE_SCHEMA` se valida como identificador PostgreSQL seguro. `public`, `information_schema` y schemas `pg_*` no son valores válidos para la aplicación.

## SQLAlchemy y schema

Para PostgreSQL:

- `Base.metadata` usa `MetaData(schema=DATABASE_SCHEMA)`;
- la conexión restringe `search_path` al schema configurado;
- consultas ORM quedan dirigidas a `administracion` sin prefijos hardcodeados en cada servicio.

Para SQLite de unit tests, el metadata permanece sin schema.

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

`requests:close` permanece como registro legacy **inactivo**. No autoriza cierre/factura.

### `config:manage`

`iam_service.SYSTEM_ONLY_PERMISSION_CODES` contiene `config:manage`. Para usuarios ordinarios una asignación de ese código no produce permiso efectivo.

### `config:read`

Permite GET/HEAD de Configuración según los routers autorizados, pero no satisface mutaciones.

### `areas:manage`

Protege mutaciones de `/api/areas` y relaciones Área ↔ Categoría.

La baseline limpia crea `area-manager` y `configuration-viewer` como roles reutilizables, sin asignarlos a Cargos/Grupos por nombre.

## Accesos como superficie única

La administración de Usuarios, Grupos, Roles, Permisos y Cargos se concentra en:

```text
Configuración → Accesos
```

Usuarios/Personas y Organigrama no son pantallas independientes de la arquitectura objetivo.

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

La baseline `20260820_0001_initial_schema.py` crea las columnas canónicas directamente. No existe una migración vigente de renombre de columnas históricas.

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

Abrir/cerrar únicamente el dropdown Configuración no abandona Accesos; seleccionar una opción navegable sí.

## Response models

`UserOut` expone:

```text
permission_codes
is_system_account
```

Los aliases `can_*` de sesión pueden permanecer temporalmente, pero no son autoridad backend. `ExpenseOut` expone capacidades por recurso.

## Alembic: baseline limpia

La historia vigente contiene una sola raíz:

```text
20260820_0001_initial_schema
```

La cadena histórica `0000 → 0008` fue retirada de la rama operativa al reiniciar la base.

`backend/alembic/env.py`:

- crea `administracion` si falta;
- establece `search_path` al schema configurado;
- usa `version_table_schema=DATABASE_SCHEMA`;
- restringe discovery/autogenerate al mismo schema.

La baseline aborta si `administracion` ya contiene tablas de aplicación. No mueve, copia, renombra ni backfillea datos antiguos.

El entrypoint ejecuta:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Una vez desplegada `20260820_0001`, cualquier cambio físico posterior requiere una nueva revisión Alembic.

## Testing

Contratos mínimos:

- autorización por permisos efectivos;
- `config:read` sin mutaciones;
- `config:manage` system-only;
- `areas:manage` aislado;
- capacidades por recurso;
- única baseline `20260820_0001`;
- `DATABASE_SCHEMA=administracion` y rechazo de schemas de sistema;
- `expense_area` / `expense_category` en API/ORM/DB;
- `alembic_version` bajo `administracion` en PostgreSQL;
- ausencia de tablas de aplicación nuevas en `public`;
- build Vite;
- navegación de topbar desde Accesos.
