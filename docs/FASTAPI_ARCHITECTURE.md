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

Fuentes:

```text
baseline requests:read
permiso directo
rol directo
Grupo → Rol → Permiso
Cargo → Rol → Permiso
```

Permisos operativos: `requests:read`, `requests:create`, `requests:approve`, `config:manage`.

`requests:close` queda como registro legacy inactivo desde migración `0005`; no autoriza endpoints financieros.

### Cuenta técnica

Producción:

```text
IAM máximo = requests:read + config:manage
```

No participa en aprobación/votación. Excepciones administrativas por recurso:

```text
cancelar
corregir / reenviar
gestionar cierre/factura
```

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

Servicio:

```text
services/closure_service.py
```

API:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

Solo solicitante crea/cambia/revoca. `can_delegate_close` se expone por solicitud.

Una delegación activa por solicitud se garantiza con índice parcial; cambiar delegado revoca y hace `flush()` antes de insertar la nueva fila.

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
APPROVAL_DECISION
= requests:approve + Approval.PENDING + PENDING_APPROVAL

QUOTATION_VOTE
= requests:approve + invitación vigente + QUOTATION_VOTING + sin voto

CORRECT_REQUEST
= NEEDS_REVISION + requested_by == current_user.email

CLOSE_REQUEST
= APPROVED + (requester OR active_closure_delegate)
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

Persistencia conserva actor/timestamp/comentario.

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

Mientras `ExpenseTable` viva en `main.jsx`, `vite.config.js` consume capacidades backend mediante bridges:

```text
x.can_cancel
x.can_correct
x.can_close
x.can_delegate_close
```

La autorización siempre queda en backend. El `canClose={true}` físicamente presente en source legacy no es autoridad del bundle transformado y debe retirarse cuando se modularice `ExpenseTable`.

Los bridges temporales no deben depender de indentación o saltos de línea exactos del monolito. Para la inserción de **Delegar cierre/factura**, Vite usa un ancla regex tolerante a LF/CRLF y whitespace variable, pero exige exactamente una coincidencia de `row-actions → x.can_correct`; cero o múltiples coincidencias abortan el build de forma explícita para evitar transformar código ambiguo.

## Response models

`UserOut.permission_codes` expone permisos IAM efectivos y aliases UX legacy temporales.

`ExpenseOut` expone:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

No forman parte de `permission_codes`.

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
```

`0005` crea `expense_closure_delegations`, índice de una delegación activa y marca `requests:close` inactivo/legacy.

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
test_migrations.py
test_container_portability.py
```

Feature 008 exige probar requester/Admin/delegado, tercero con `requests:close` legacy negado, revocación, una delegación activa, `CLOSE_REQUEST` requester/delegado y que el bridge Vite de delegación tolere diferencias de formato sin perder el fail-fast de unicidad.

Mientras GitHub Actions no tenga cuota, backend tests + `npm run build` + Docker build/smoke son gates locales obligatorios.

## Deuda legacy explícita

Persisten temporalmente `api/expenses.py`, `api/users.py`, `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `main.jsx`, `domain-normalization.js`, bridges Vite y `requests:close` inactivo. Ninguno es autoridad nueva.

Deuda funcional separada: fórmula completa quorum/mayoría APPROVED/REJECTED, empate de cotizaciones, edición estructural MULTI_QUOTE y outbox/retry persistente.
