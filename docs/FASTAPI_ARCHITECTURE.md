# Arquitectura FastAPI

## Application factory

`app/application.py` crea la aplicación, middleware, lifespan mínimo, health endpoint y routers. `app/main.py` es alias de compatibilidad.

Las rutas canónicas se registran antes de handlers legacy equivalentes:

```text
request_actions.py      → creación
revision_actions.py     → corregir / reenviar
cancellation_actions.py → cancelación
quotation_actions.py    → votación
document_actions.py     → documentos
financial_actions.py    → factura / cierre
my_actions.py           → acciones contextuales
tracking.py             → dashboard + seguimiento
position_access.py      → Cargo → Rol
```

## Capas

```text
api/       HTTP/dependencias/status codes
schemas/   contratos Pydantic
services/  reglas de negocio reutilizables
models/    persistencia SQLAlchemy
core/      Settings, DB, seguridad, rate limiting
```

SQLAlchemy es síncrono; rutas canónicas que hacen I/O bloqueante usan `def` para ejecutarse en threadpool.

## Settings y ambiente

`core/config.py` usa `pydantic-settings`.

```text
is_production_environment
→ solo ENVIRONMENT=production
→ gobierna segregación funcional

is_production
→ producción/runtime alojado con hardening
→ gobierna secretos/CORS
```

`RENDER=true` no sustituye `ENVIRONMENT=production` para autorización.

## IAM

`require_permission(code)` consulta `iam_service.has_permission()`.

Fuentes para usuarios activos:

```text
baseline requests:read
permiso directo
rol directo
Grupo → Rol → Permiso
Cargo → Rol → Permiso
```

`users_with_permission()` usa la misma resolución para poblaciones de workflow.

El nombre de un Cargo nunca se compara para autorizar.

### Cuenta técnica

```text
ENVIRONMENT=production
→ IAM efectivo máximo: requests:read + config:manage

ENVIRONMENT!=production
→ todos los permisos atómicos activos
```

Producción filtra permisos financieros incluso si llegan por Grupo/Cargo/Rol/directo.

Además existen excepciones por recurso para la cuenta protegida en `system_accounts`:

```text
cancelar solicitud abierta
corregir / reenviar solicitud corregible
```

No son permisos financieros IAM.

## Capacidades por recurso

### Cancelación

`cancellation_actions.py` implementa:

```text
POST /api/expenses/{request_id}/cancel
```

Autoriza:

```text
status cancelable
AND (requester OR system_accounts)
```

`tracking.py` expone `can_cancel` para UX; el endpoint vuelve a validar.

### Corrección

`revision_actions.py` implementa:

```text
PUT /api/expenses/{request_id}/resubmit
```

No usa `require_permission('requests:create')` para editar una solicitud existente. Usa:

```text
current_user
→ can_correct_expense(db, expense, user)
```

`can_correct=true` solo si:

```text
status corregible
AND (current_user.email == requested_by OR current_user ∈ system_accounts)
```

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

No corregibles:

```text
CLOSED
CANCELLED
```

Un tercero con `requests:create`, `requests:approve` o `config:manage` recibe 403.

`tracking.py` devuelve `ExpenseOut.can_correct` por solicitud.

## Seguimiento universal

`tracking.py` registra:

```text
GET /api/expenses
GET /api/expenses/dashboard
```

Ambos requieren `requests:read`, cuyo resolver incluye baseline para usuarios activos.

El listado no filtra por requester.

## Resolver de acciones personales

`pending_action_service.py` combina permisos, asignación y estado.

```text
APPROVAL_DECISION
= requests:approve
+ Approval.PENDING asignado
+ Expense.PENDING_APPROVAL

QUOTATION_VOTE
= requests:approve
+ invitación vigente
+ QUOTATION_VOTING
+ sin voto

CORRECT_REQUEST
= Expense.NEEDS_REVISION
+ requested_by == current_user.email

CLOSE_REQUEST
= requests:close
+ Expense.APPROVED
```

`CORRECT_REQUEST` es por propiedad; **no requiere `requests:create`**. El Admin del sistema puede corregir administrativamente una solicitud ajena, pero no recibe automáticamente esa tarea personal.

## API contextual

`my_actions.py` expone:

```text
GET  /api/expenses/{request_id}/my-actions
POST /api/expenses/{request_id}/approval-decision
```

`GET my-actions` revalida tareas antes de mostrarlas.

`POST approval-decision`:

1. requiere `requests:approve`;
2. localiza/bloquea solicitud;
3. niega autoaprobación;
4. localiza `Approval.PENDING` del usuario;
5. delega en `approval_engine.apply_decision()`.

No expone tokens bearer de correo al frontend autenticado.

## Enviar a revisión

`approval_engine.apply_decision()` trata `REVISION_REQUESTED` **antes** de evaluar mayoría.

Comentario obligatorio: `len(comment.strip()) >= 3`.

Secuencia:

```text
Approval actual.status = REVISION_REQUESTED
Expense.status         = NEEDS_REVISION
record STEP_REVISION_REQUESTED
expire otras PENDING/WAITING
commit
send_final_notification(requester)
```

Es una interrupción inmediata, no una decisión que espere threshold de mayoría.

Persistencia/auditoría conserva:

- aprobador actor;
- timestamp;
- comentario;
- transición;
- expiración de otros pasos.

Después, `pending_action_service.py` crea `CORRECT_REQUEST` únicamente para el solicitante original.

Aprobar/Rechazar conservan la lógica de mayoría existente y su deuda funcional respecto a la fórmula constitucional completa.

## Invariant SIMPLE/MULTI_QUOTE

`revision_actions.py` reconoce MULTI_QUOTE por evidencia durable:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Cambio real de tipo durante resubmit devuelve 409.

Una MULTI_QUOTE corregida:

- conserva IDs de opciones/attachments;
- puede editar contenido sin cambiar cantidad;
- genera `flow_id` nuevo;
- limpia votos vigentes;
- reemplaza invitaciones;
- conserva eventos históricos;
- vuelve a `QUOTATION_VOTING`;
- crea participantes con `users_with_permission('requests:approve')`;
- **excluye `expense.requested_by`**, no el actor que ejecutó la corrección.

Esto evita que una corrección administrativa incluya accidentalmente al solicitante en su propia votación.

## Frontend modular / bridges legacy

Componentes canónicos:

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/iam-admin.jsx
```

`home-dashboard.jsx` contiene directamente:

```text
Enviar a revisión
comment.trim().length < 3
```

No depende de un transform de wording.

Mientras `main.jsx` conserve `ExpenseTable`, `vite.config.js` mantiene bridges mínimos para:

```text
x.can_cancel
x.can_correct
canCreate || revision
```

La autorización sigue estando en backend.

## Response models

`UserOut`:

```text
permission_codes
can_request / can_approve / can_view / can_configure / can_close  # aliases UX legacy
```

`ExpenseOut`:

```text
can_cancel
can_correct
```

Estas capacidades por recurso no forman parte de `permission_codes`.

`PositionOut` incluye `role_ids`.

## API de Cargos

```text
GET    /api/iam/positions
PUT    /api/iam/positions/{position_id}/roles/{role_id}
DELETE /api/iam/positions/{position_id}/roles/{role_id}
```

Mutaciones requieren `config:manage` y no aceptan Roles técnicos `system_managed`.

## Lifespan y migraciones

Lifespan no ejecuta DDL/backfills/seeds.

Topología Alembic:

```text
20260817_0000 application baseline
→ 20260817_0001 configurable IAM
→ 20260817_0002 system accounts
→ 20260817_0003 MULTI_QUOTE request_type repair
→ 20260818_0004 position role inheritance
```

Feature 007 no agrega migración.

`0004` importa una sola vez configuración legacy `access_profiles/users.title` hacia IAM canónico y luego runtime deja de depender de esos flags/nombres.

Entry point:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## Portabilidad Docker

- `.gitattributes`: `*.sh text eol=lf`.
- Dockerfile elimina `\r` defensivamente.
- Compose espera healthcheck backend antes de Nginx.
- bootstrap se ejecuta como módulo.

## Passwords/sesiones

- Argon2 con `pwdlib.PasswordHash.recommended()` para hashes nuevos.
- PBKDF2 legacy se verifica y actualiza a Argon2 tras login correcto.
- JWT con expiración absoluta.
- timeout por inactividad.
- `session_version` para revocación.

## Testing

Cobertura relevante:

```text
test_iam_api.py
test_position_role_inheritance.py
test_universal_tracking.py
test_request_cancellation.py
test_pending_actions.py
test_multi_quote_revision.py
test_frontend_dashboard_contract.py
test_migrations.py
test_container_portability.py
```

Feature 007 exige comprobar:

- tercero no puede resubmit;
- solicitante/Admin sí pueden;
- `can_correct` correcto;
- revisión inmediata en ronda MAJORITY;
- comentario obligatorio;
- otros pasos expiran;
- `CORRECT_REQUEST` llega al solicitante;
- el solicitante original queda excluido de una nueva ronda MULTI_QUOTE.

Mientras GitHub Actions no tenga cuota, backend tests + `npm run build` + Docker build/smoke son gates locales obligatorios. Un run bloqueado por cuota no cuenta como CI verde.

## Deuda legacy explícita

Persisten temporalmente:

```text
api/expenses.py legacy
api/users.py legacy
UserRole
can_*
AccessProfile
BOARD_CODES
main.jsx monolítico
domain-normalization.js
bridges Vite
```

No son arquitectura objetivo ni autoridad de autorización.

Deuda funcional separada:

- fórmula completa quorum/mayoría APPROVED/REJECTED;
- empate de cotizaciones;
- edición estructural de opciones MULTI_QUOTE;
- outbox/retry persistente de correo.

`REVISION_REQUESTED` ya no es deuda: su semántica vigente es interrupción inmediata con handoff al solicitante.
