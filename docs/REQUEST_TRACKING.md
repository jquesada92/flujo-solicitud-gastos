# Seguimiento universal, acciones pendientes, revisión y capacidades por recurso

## Objetivo

Todo usuario activo puede consultar dashboard y solicitudes para seguimiento. La lectura compartida no convierte acciones mutables en universales.

```text
información compartida
vs
acciones concretas del usuario
vs
capacidades por recurso
```

## Baseline

```text
active user
→ requests:read
→ GET /api/expenses/dashboard
→ GET /api/expenses
```

Los permisos mutables siguen siendo configurables por asignación directa, Rol directo, Grupo → Rol o Cargo → Rol.

## Dashboard

Los KPIs superiores son informativos:

```text
Acciones que requieren mi atención
Solicitudes en proceso
Cerradas en 24 horas
```

No son botones ni ejecutan navegación.

```text
fila de Acciones pendientes → modal contextual
Ver todas                    → Solicitudes
```

## Tareas contextuales

`backend/app/services/pending_action_service.py` resuelve:

### `APPROVAL_DECISION`

`requests:approve` + `Approval.PENDING` asignado al usuario + solicitud `PENDING_APPROVAL`.

### `QUOTATION_VOTE`

`requests:approve` + invitación vigente + `QUOTATION_VOTING` + sin voto vigente.

### `CORRECT_REQUEST`

```text
solicitud NEEDS_REVISION
AND requested_by == current_user.email
```

No depende de `requests:create`. La tarea pertenece al solicitante original.

### `CLOSE_REQUEST`

`requests:close` + solicitud `APPROVED`.

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

**Enviar a revisión** exige comentario mínimo de 3 caracteres. El botón permanece deshabilitado sin comentario válido y el backend vuelve a validarlo.

La decisión usa:

```text
POST /api/expenses/{request_id}/approval-decision
```

sin exponer el token bearer de los enlaces de correo.

### Enviar a revisión

`REVISION_REQUESTED` es una interrupción inmediata del flujo:

```text
aprobación actual      → REVISION_REQUESTED
solicitud               → NEEDS_REVISION
otras PENDING/WAITING   → EXPIRED
solicitante             → CORRECT_REQUEST
```

No espera mayoría. El comentario, actor y timestamp quedan auditados y el solicitante recibe el comentario por notificación.

Los otros aprobadores dejan de tener acción vigente.

### Votación

```text
QUOTATION_VOTE
→ revisar opciones/soportes
→ votar una opción
```

### Cierre

```text
CLOSE_REQUEST
→ factura
→ notas
→ cerrar
```

### Corrección

```text
CORRECT_REQUEST
→ Abrir para corregir / reenviar
```

La tarea aparece al solicitante original. El Administrador del sistema puede corregir administrativamente desde Solicitudes mediante `can_correct`, pero no recibe automáticamente la tarea personal de solicitudes ajenas.

## Después de una acción

El frontend recarga:

```text
GET /api/expenses/dashboard
GET /api/expenses/{request_id}/my-actions
```

Una tarea atendida desde correo/otra sesión deja de mostrarse como ejecutable.

## Lista de solicitudes

`GET /api/expenses` no filtra por requester y devuelve capacidades por recurso:

```json
{
  "can_cancel": true,
  "can_correct": true
}
```

### `can_cancel`

Solo solicitante original o Administrador del sistema, en estados cancelables.

### `can_correct`

Solo solicitante original o Administrador del sistema, en estados corregibles.

`requests:create`, `requests:approve`, `config:manage`, Grupo, Rol o Cargo no permiten editar una solicitud ajena.

## Cancelación

Cancelables:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
```

No cancelables:

```text
CLOSED
CANCELLED
REJECTED
```

Endpoint:

```text
POST /api/expenses/{request_id}/cancel
```

Exige motivo y persiste actor/timestamp/razón.

## Corrección

Corregibles por solicitante/Admin:

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

Endpoint:

```text
PUT /api/expenses/{request_id}/resubmit
```

vuelve a autorizar en backend y mantiene invariants SIMPLE/MULTI_QUOTE.

## Administrador del sistema en producción

IAM efectivo:

```text
requests:read
config:manage
```

No participa en aprobación/votación/cierre. Cancelar y corregir son excepciones administrativas por recurso basadas en `system_accounts`, no permisos financieros.

## Frontend

Componentes:

```text
frontend/src/home-dashboard.jsx
frontend/src/home-dashboard.css
```

**Enviar a revisión** y la validación mínima de comentario viven directamente en el source modular.

Mientras `ExpenseTable` siga legacy, Vite mantiene bridges para:

```text
x.can_cancel
x.can_correct
canCreate || revision
```

No debe parchear wording/handlers internos del Dashboard.

## Accesibilidad

- KPIs informativos no entran al tab order como botones.
- Modal usa `role="dialog"` y `aria-modal="true"`.
- Escape cierra cuando no hay una mutación ocupada.

## Pruebas

Cobertura principal:

```text
test_universal_tracking.py
test_request_cancellation.py
test_pending_actions.py
test_frontend_dashboard_contract.py
test_multi_quote_revision.py
```

Debe demostrar:

- lectura universal;
- KPIs informativos;
- fila → modal;
- `my-actions` backend-authoritative;
- revisión inmediata con comentario y expiración de pares;
- `CORRECT_REQUEST` al solicitante;
- tercero sin `can_correct`;
- solicitante/Admin con capacidad de corrección;
- cancelación por solicitante/Admin;
- revalidación posterior a mutación.

Mientras GitHub Actions no tenga cuota, backend tests, `npm run build` y Docker build/smoke son gates locales obligatorios.
