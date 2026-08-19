# Arquitectura FastAPI

## Application factory

`app/application.py` crea aplicación, middleware, lifespan mínimo, health endpoint y routers. `app/main.py` es alias de compatibilidad.

Rutas canónicas antes de handlers legacy:

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

SQLAlchemy es síncrono; rutas con I/O bloqueante usan `def` para threadpool de FastAPI.

## Settings y ambiente

`is_production_environment` depende solo de `ENVIRONMENT=production` y gobierna segregación funcional. `is_production` puede incluir runtime alojado para hardening. `RENDER=true` no sustituye `ENVIRONMENT=production`.

## IAM

`require_permission(code)` usa `iam_service.has_permission()`.

Fuentes configurables:

```text
baseline requests:read
permiso directo
rol directo
Grupo → Rol → Permiso
Cargo → Rol → Permiso
```

Permisos operativos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:manage  # system-only
```

`requests:close` queda como registro legacy inactivo desde migración `0005`; no autoriza endpoints financieros.

### Frontera system-only

`iam_service.SYSTEM_ONLY_PERMISSION_CODES` contiene `config:manage`.

Para usuarios ordinarios:

```text
effective = unrestricted_permissions - {config:manage} + baseline
```

Por tanto una relación legacy/directa/Grupo/Cargo con `config:manage` no eleva a un usuario ordinario.

`users_with_permission('config:manage')` también ignora esas relaciones y resuelve únicamente `system_accounts` cuando la política del ambiente lo permite.

### Gestión de Áreas

`areas:manage` sí es configurable por IAM y protege mutaciones de `/api/areas`.

La lectura activa necesaria para clasificar/consultar solicitudes permanece autenticada; `include_inactive=true` y mutaciones requieren `areas:manage`.

### Cuenta técnica

Producción:

```text
IAM máximo = requests:read + areas:manage + config:manage
```

No participa en aprobación/votación. Excepciones administrativas por recurso:

```text
cancelar
corregir / reenviar
gestionar cierre/factura
```

`UserOut.is_system_account` se calcula desde `system_accounts` y se expone a login/`/auth/me` para UX; no sustituye validación backend.

## Capacidades por recurso

### Cancelación

`POST /api/expenses/{request_id}/cancel` valida estado + `(requester OR system_accounts)`. `tracking.py` expone `can_cancel`.

### Corrección

`PUT /api/expenses/{request_id}/resubmit` usa `current_user → can_correct_expense()`.

```text
can_correct = estado corregible AND (requester OR system_accounts)
```

No depende de `requests:create`.

### Cierre/factura

`financial_actions.py` implementa:

```text
POST /api/expenses/{request_id}/close
PUT  /api/expenses/{request_id}/invoice
```

Ambos autentican con `current_user` y llaman:

```text
can_manage_closure(db, expense, user)
```

Regla:

```text
status ∈ {APPROVED, CLOSED}
AND (requester OR system_accounts OR active_closure_delegate)
```

No se usa `require_permission('requests:close')`.

`tracking.py` expone `ExpenseOut.can_close`.

### Delegación de cierre/factura

Modelo:

```text
models/closure.py
ExpenseClosureDelegation
```

API:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

Solo solicitante crea/cambia/revoca. `can_delegate_close` se expone por solicitud.

## Seguimiento universal

`tracking.py` registra:

```text
GET /api/expenses
GET /api/expenses/dashboard
```

Ambos requieren baseline `requests:read`. El listado no filtra por requester y expone:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

## Resolver de acciones personales

`pending_action_service.py`:

```text
APPROVAL_DECISION = requests:approve + Approval.PENDING + PENDING_APPROVAL
QUOTATION_VOTE    = requests:approve + invitación vigente + QUOTATION_VOTING + sin voto
CORRECT_REQUEST   = NEEDS_REVISION + requested_by == current_user.email
CLOSE_REQUEST     = APPROVED + (requester OR active_closure_delegate)
```

El Administrador del sistema conserva facultad de cierre desde Solicitudes, pero no recibe todas las solicitudes como tareas personales.

## API contextual

`my_actions.py`:

```text
GET  /api/expenses/{request_id}/my-actions
POST /api/expenses/{request_id}/approval-decision
```

`my-actions` revalida antes de mostrar. Aprobación autenticada no expone tokens bearer de correo.

## Enviar a revisión

`approval_engine.apply_decision()` trata `REVISION_REQUESTED` antes de mayoría. Comentario >= 3.

```text
Approval → REVISION_REQUESTED
Expense  → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester → CORRECT_REQUEST
```

## Invariant SIMPLE/MULTI_QUOTE

`revision_actions.py` reconoce MULTI_QUOTE por `request_type`, `QUOTATION_VOTING` o 2+ opciones. Cambio real devuelve 409. Corrección MULTI_QUOTE genera nueva ronda y excluye `expense.requested_by`, no al actor administrativo.

## Frontend modular / bridges legacy

Componentes:

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/closure-delegation.jsx
frontend/src/iam-admin.jsx
```

Mientras partes de `main.jsx` sigan legacy, `vite.config.js` aplica bridges que consumen backend authoritative.

Acciones por solicitud:

```text
x.can_cancel
x.can_correct
x.can_close
x.can_delegate_close
```

Configuración:

```text
isSystemAdmin = user.is_system_account === true
canManageAreas = isSystemAdmin OR permission_codes contains areas:manage

Usuarios/Organigrama/Accesos/Reglas/Audit → isSystemAdmin
Áreas                                  → canManageAreas
```

`iam-admin.jsx` solo inyecta Accesos dentro de un menú marcado `data-system-admin=true`.

Los bridges temporales no deben depender de indentación o saltos de línea exactos. La inserción de delegación usa regex tolerante a LF/CRLF y exige exactamente una coincidencia.

## Response models

`UserOut` expone:

```text
permission_codes
is_system_account
can_* aliases legacy temporales
```

`ExpenseOut` expone:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

Las capacidades por recurso no forman parte de `permission_codes`.

## API de Cargos

```text
GET    /api/iam/positions
PUT    /api/iam/positions/{position_id}/roles/{role_id}
DELETE /api/iam/positions/{position_id}/roles/{role_id}
```

El nombre del Cargo nunca autoriza.

## Lifespan y migraciones

Lifespan no ejecuta DDL/backfills/seeds.

Topología:

```text
20260817_0000 application baseline
→ 20260817_0001 configurable IAM
→ 20260817_0002 system accounts
→ 20260817_0003 MULTI_QUOTE request_type repair
→ 20260818_0004 position role inheritance
→ 20260818_0005 closure delegation
→ 20260818_0006 area management permission
```

`0005` crea delegaciones y retira `requests:close` como autoridad.

`0006` crea `areas:manage`, el Rol neutral `Gestor de áreas` y actualiza la descripción de `config:manage`; no asigna permisos por nombres organizacionales.

Entry point:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## Portabilidad Docker

- `*.sh text eol=lf`.
- Docker normaliza CRLF defensivamente.
- Compose espera healthcheck backend antes de Nginx.
- bootstrap como módulo.

## Passwords/sesiones

Argon2 para hashes nuevos; PBKDF2 legacy se actualiza tras login; JWT con expiración absoluta, timeout por inactividad y `session_version`.

## Testing

Cobertura relevante:

```text
test_iam_api.py
test_position_role_inheritance.py
test_universal_tracking.py
test_request_cancellation.py
test_pending_actions.py
test_multi_quote_revision.py
test_closure_delegation.py
test_frontend_dashboard_contract.py
test_frontend_closure_contract.py
test_frontend_configuration_access.py
test_migrations.py
test_container_portability.py
```

Feature 009 exige probar `areas:manage` ordinario, `config:manage` system-only, `is_system_account`, separación visual del menú y topología `0006`.

Mientras GitHub Actions no tenga cuota, backend tests + `npm run build` + Docker build/smoke son gates locales obligatorios.

## Deuda legacy explícita

Persisten temporalmente `api/expenses.py`, `api/users.py`, `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `main.jsx`, `domain-normalization.js`, bridges Vite y `requests:close` inactivo. Ninguno es autoridad nueva.

La pantalla IAM todavía puede mostrar registros legacy/configuración que runtime filtra; `config:manage` es system-only aunque una relación histórica lo referencie.

Deuda funcional separada: fórmula completa quorum/mayoría APPROVED/REJECTED, empate de cotizaciones, edición estructural MULTI_QUOTE y outbox/retry persistente.
