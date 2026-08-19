# Seguimiento universal, acciones pendientes y capacidades por recurso

## Objetivo

Todo usuario activo puede consultar dashboard y solicitudes para seguimiento. La lectura compartida no convierte las acciones mutables en universales.

```text
información compartida
vs
acciones concretas del usuario
vs
capacidades/delegaciones por recurso
```

## Baseline

```text
active user
→ requests:read
→ GET /api/expenses/dashboard
→ GET /api/expenses
```

## Dashboard

Los KPIs superiores son informativos:

```text
Acciones que requieren mi atención
Solicitudes en proceso
Cerradas en 24 horas
```

No son botones.

```text
fila de Acciones pendientes → modal contextual
Ver todas                    → Solicitudes
```

## Tareas contextuales

`pending_action_service.py` resuelve:

### `APPROVAL_DECISION`

`requests:approve` + `Approval.PENDING` asignado + `PENDING_APPROVAL`.

### `QUOTATION_VOTE`

`requests:approve` + invitación vigente + `QUOTATION_VOTING` + sin voto.

### `CORRECT_REQUEST`

```text
NEEDS_REVISION
AND requested_by == current_user.email
```

La tarea pertenece al solicitante original.

### `CLOSE_REQUEST`

```text
APPROVED
AND (
  requested_by == current_user.email
  OR delegación de cierre activa para current_user
)
```

No depende de `requests:close`.

El Administrador del sistema puede cerrar por excepción administrativa desde Solicitudes, pero no recibe todas las solicitudes aprobadas como tareas personales.

## Modal contextual

Al seleccionar una fila:

```text
GET /api/expenses/{request_id}/my-actions
```

El backend revalida tareas y el modal muestra únicamente las vigentes.

### Aprobación

```text
Aprobar
Rechazar
Enviar a revisión
```

Enviar a revisión exige comentario mínimo de 3 caracteres y usa `POST /api/expenses/{request_id}/approval-decision`.

Una revisión válida:

```text
aprobación actual    → REVISION_REQUESTED
solicitud            → NEEDS_REVISION
otras PENDING/WAITING → EXPIRED
solicitante          → CORRECT_REQUEST
```

### Votación

`QUOTATION_VOTE` permite revisar opciones/soportes y votar.

### Cierre

`CLOSE_REQUEST` permite subir factura, notas y cerrar; solo aparece para solicitante o delegado activo.

### Corrección

`CORRECT_REQUEST` abre la solicitud propia para corregir/reenviar.

## Después de una acción

El frontend recarga dashboard + `my-actions`; una tarea atendida desde correo/otra sesión deja de mostrarse.

## Lista de solicitudes

`GET /api/expenses` no filtra por requester y devuelve:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

### `can_cancel`

Solicitante original o Administrador del sistema, en estados cancelables.

### `can_correct`

Solicitante original o Administrador del sistema, en estados corregibles.

### `can_close`

```text
APPROVED/CLOSED
AND (solicitante OR system_accounts OR delegado activo)
```

### `can_delegate_close`

Solo el solicitante original puede administrar la delegación de esa solicitud.

## Delegación de cierre/factura

API:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

Solo el solicitante crea/cambia/revoca. Una única delegación activa por solicitud; cambiar/revocar conserva historial.

El delegado:

- debe ser activo;
- no puede ser el solicitante;
- no puede ser `system_accounts`;
- obtiene autoridad únicamente sobre esa solicitud.

Ver `docs/CLOSURE_DELEGATION.md`.

## Cancelación

Cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`.

No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

`POST /api/expenses/{request_id}/cancel` exige motivo.

## Corrección

Corregibles por solicitante/Admin: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`, `REJECTED`.

No corregibles: `CLOSED`, `CANCELLED`.

`PUT /api/expenses/{request_id}/resubmit` vuelve a autorizar en backend.

## Administrador del sistema en producción

IAM máximo:

```text
requests:read
config:manage
```

No participa en aprobación/votación. Cancelar, corregir y gestionar cierre/factura son excepciones administrativas por recurso basadas en `system_accounts`.

## Frontend

Componentes:

```text
frontend/src/home-dashboard.jsx
frontend/src/home-dashboard.css
frontend/src/closure-delegation.jsx
```

Mientras `ExpenseTable` siga legacy, Vite mantiene bridges para:

```text
x.can_cancel
x.can_correct
x.can_close
x.can_delegate_close
```

La autorización sigue en backend.

## Pruebas

Cobertura relevante:

```text
test_universal_tracking.py
test_request_cancellation.py
test_pending_actions.py
test_multi_quote_revision.py
test_closure_delegation.py
test_frontend_dashboard_contract.py
test_frontend_closure_contract.py
```

Debe demostrar lectura universal, tareas personales correctas, revisión inmediata, corrección/cancelación por recurso, cierre requester/Admin/delegado y revocación de delegación.

Mientras GitHub Actions no tenga cuota, backend tests, `npm run build` y Docker build/smoke son gates locales obligatorios.
