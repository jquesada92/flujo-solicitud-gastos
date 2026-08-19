# Plan técnico — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.6.0

## Diseño

La lectura compartida se resuelve mediante el baseline `requests:read`. Las mutaciones siguen siendo backend-authoritative y pueden depender de permisos IAM o de reglas explícitas por recurso.

```text
current_user
   ↓
effective_permission_codes(user)
   ↓
requests:read baseline
   ↓
GET /api/expenses/dashboard
GET /api/expenses
```

## IAM y capacidades por recurso

Para usuarios activos:

```text
effective = baseline
          ∪ direct permissions
          ∪ direct-role permissions
          ∪ group-role permissions
          ∪ position-role permissions
```

La lista expone además capacidades calculadas por solicitud:

```text
can_cancel
can_correct
```

Ambas son reglas por recurso. `can_correct` no deriva de `requests:create`.

### `can_cancel`

```text
status ∈ {QUOTATION_VOTING, SUBMITTED, PENDING_APPROVAL, NEEDS_REVISION, APPROVED}
AND (requester OR system_accounts)
```

### `can_correct`

```text
status ∈ {QUOTATION_VOTING, SUBMITTED, PENDING_APPROVAL, NEEDS_REVISION, APPROVED, REJECTED}
AND (requester OR system_accounts)
```

## `GET /api/expenses`

`tracking.py`:

- requiere `requests:read`;
- no filtra por solicitante ni `UserRole`;
- carga relaciones necesarias para seguimiento;
- calcula `can_cancel` y `can_correct` por solicitud;
- resuelve `system_accounts` una vez por request para evitar N+1.

## `GET /api/expenses/dashboard`

- requiere `requests:read`;
- expone métricas generales;
- usa `pending_action_service.py` para tareas personales;
- `pending_my_action` cuenta acciones concretas;
- cada `pending_item` incluye códigos de acción;
- la lista visual inicial se limita a ocho solicitudes.

Acciones actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Resolver de acciones personales

### `APPROVAL_DECISION`

Requiere `requests:approve` + `Approval.PENDING` asignado al correo del usuario + solicitud `PENDING_APPROVAL`.

Puede ejecutar:

```text
APPROVED
REJECTED
REVISION_REQUESTED
```

`REVISION_REQUESTED` se presenta como **Enviar a revisión** y requiere comentario mínimo de 3 caracteres.

Feature 007 establece que una sola revisión válida interrumpe inmediatamente la ronda:

```text
approval → REVISION_REQUESTED
request  → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester → CORRECT_REQUEST
```

No se espera mayoría para enviar a revisión.

### `QUOTATION_VOTE`

Requiere `requests:approve`, invitación vigente para el usuario, estado `QUOTATION_VOTING` y ausencia de voto vigente.

### `CORRECT_REQUEST`

Requiere únicamente:

```text
Expense.status == NEEDS_REVISION
AND Expense.requested_by == current_user.email
```

No depende de `requests:create`: es una tarea por propiedad. El Administrador del sistema puede corregir solicitudes ajenas desde la lista mediante `can_correct`, pero no recibe automáticamente esta tarea personal.

### `CLOSE_REQUEST`

Requiere `requests:close` + solicitud `APPROVED`.

## API contextual

### `GET /api/expenses/{request_id}/my-actions`

Revalida permiso + asignación + estado y devuelve únicamente acciones todavía vigentes.

### `POST /api/expenses/{request_id}/approval-decision`

- requiere `requests:approve`;
- exige `Approval.PENDING` asignado al usuario;
- evita autoaprobación;
- reutiliza `approval_engine.apply_decision()`;
- **Enviar a revisión** exige comentario y se procesa como interrupción inmediata.

Voto/cierre reutilizan endpoints canónicos existentes.

## Frontend

`frontend/src/home-dashboard.jsx` es el componente canónico.

Comportamiento:

```text
KPI superior          → información solamente
Fila acción pendiente → modal contextual
Ver todas             → Solicitudes
```

Los KPIs son `article`, no botones.

El modal:

- aprobación: Rechazar / **Enviar a revisión** / Aprobar;
- deshabilita **Enviar a revisión** mientras `comment.trim().length < 3`;
- votación: opciones/soportes + voto;
- cierre: factura/notas;
- corrección: abre el editor para el solicitante.

El wording **Enviar a revisión** vive directamente en `home-dashboard.jsx`; no depende de un transform de Vite.

Mientras `ExpenseTable` siga en `main.jsx`, Vite mantiene solo bridges temporales para `can_cancel`, `can_correct` y montaje del formulario modular.

## Cancelación y corrección

`cancellation_actions.py` y `revision_actions.py` son rutas canónicas por recurso.

- cancelación: requester/System Admin;
- corrección: requester/System Admin;
- `requests:create` no habilita cancelación ni corrección de solicitudes ajenas.

## Pruebas

`test_pending_actions.py` cubre:

- aprobación contextual;
- revisión inmediata en ronda MAJORITY;
- comentario obligatorio;
- expiración de otros aprobadores;
- handoff `CORRECT_REQUEST` al solicitante;
- invitación MULTI_QUOTE;
- cierre contextual.

`test_frontend_dashboard_contract.py` protege:

- fila → modal;
- KPIs no interactivos;
- **Enviar a revisión** directo en source + comentario mínimo;
- `x.can_correct`/`x.can_cancel` en el bridge legacy;
- revalidación posterior a mutación.

## Datos/migraciones

Feature 005/007 no requieren migración nueva. La cadena global sigue:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

## Validación local mientras Actions no tenga cuota

```powershell
cd backend
python -m unittest tests.test_pending_actions -v
python -m unittest tests.test_frontend_dashboard_contract -v
python -m unittest discover -s tests -v
cd ..

cd frontend
npm run build
cd ..

docker compose build --no-cache
docker compose up -d
```

Pruebas manuales adicionales de Feature 007:

1. aprobador ajeno no ve **Corregir / reenviar**;
2. aprobador usa **Enviar a revisión** con comentario;
3. solicitud pasa a `NEEDS_REVISION` inmediatamente;
4. solicitante recibe la tarea `CORRECT_REQUEST`;
5. otros aprobadores dejan de tener acción vigente.
