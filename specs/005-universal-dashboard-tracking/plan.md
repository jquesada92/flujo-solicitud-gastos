# Plan técnico — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.4.0

## Diseño

La lectura compartida se implementa como una capacidad base resuelta por IAM, no como un bypass de frontend ni como un nombre de rol.

```text
current_user
   ↓
effective_permission_codes(user)
   ↓
requests:read baseline para usuario activo
   ↓
GET /api/expenses/dashboard
GET /api/expenses
```

Las acciones sobre una solicitud continúan siendo backend-authoritative. Para cancelación, la autoridad no deriva de `requests:create`: se calcula por propiedad de la solicitud o identidad de cuenta técnica protegida.

## IAM

`app/services/iam_service.py` define:

```text
BASELINE_PERMISSION_CODES = {requests:read}
```

Para usuarios activos:

```text
effective = baseline
          ∪ direct permissions
          ∪ direct-role permissions
          ∪ group-role permissions
```

Para cuentas técnicas, la política ambiental se combina con el baseline. Producción continúa limitada a `config:manage + requests:read` como permisos IAM; la cancelación es una facultad explícita de administración de ciclo de vida definida por identidad de `system_accounts`, no un permiso financiero heredable.

`permission_sources()` debe explicar el origen:

```text
Acceso base del producto para usuarios activos
```

`users_with_permission('requests:read')` debe devolver todos los usuarios activos.

## Rutas canónicas de seguimiento

Se agrega `app/api/tracking.py` y se registra antes de `expenses.py` legacy.

Motivo: el router legacy todavía contiene filtros basados en `UserRole.REQUESTER`. La ruta canónica evita que esa deuda limite la visibilidad mientras se retira el monolito legacy.

### `GET /api/expenses`

- requiere `requests:read`;
- no filtra por `requested_by` ni `UserRole`;
- conserva carga eager de aprobaciones, attachments, opciones y votos;
- conserva el conjunto operativo de estados visibles;
- presenta actor/nombres/eventos como el contrato existente;
- agrega `can_cancel` calculado por solicitud y usuario actual.

`can_cancel=true` únicamente cuando:

```text
status ∈ {QUOTATION_VOTING, SUBMITTED, PENDING_APPROVAL, NEEDS_REVISION, APPROVED}
AND (
  current_user.email == expense.requested_by
  OR current_user está registrado en system_accounts
)
```

La consulta de `system_accounts` se resuelve una vez por request de listado para evitar N+1.

### `GET /api/expenses/dashboard`

- requiere `requests:read`;
- expone métricas generales a todo usuario activo;
- calcula `pending_my_action` solo desde capacidades accionables:
  - `requests:approve` → aprobaciones/votaciones asignadas;
  - `requests:close` → solicitudes aprobadas pendientes de cierre;
- para votación usa `QuotationVotingInvitation` como población asignada, no todos los usuarios con permiso en abstracto.

## Cancelación canónica

Se agrega `app/api/cancellation_actions.py`, registrado antes de `expenses.py` legacy.

### `POST /api/expenses/{request_id}/cancel`

- requiere autenticación, no `requests:create`;
- localiza y bloquea la solicitud antes de cambiar estado;
- autoriza solo al solicitante original o a una cuenta en `system_accounts`;
- rechaza usuarios empresariales ajenos aunque tengan `requests:create`, `requests:approve` o `config:manage`;
- rechaza `CLOSED`, `CANCELLED` y `REJECTED`;
- permite `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION` y `APPROVED`;
- exige motivo de 3 a 1000 caracteres;
- expira aprobaciones abiertas;
- persiste estado, actor, timestamp y motivo.

La cuenta técnica se identifica por `system_accounts`, nunca por `UserRole.ADMIN`, email o cargo.

## Frontend

No se requiere una nueva variable de Vite.

El shell actual ya presenta **Inicio** y **Solicitudes** para usuarios autenticados. `current_user()` deriva temporalmente:

```text
can_view = requests:read
```

por lo que un usuario sin roles recibe `can_view=true` al autenticarse.

La tabla legacy ya contiene la acción de cancelación, pero antes infería visibilidad desde una lista de estados y `can_request`. Mientras esa tabla siga dentro del monolito, el transform de build sustituye únicamente ese guard por:

```text
x.can_cancel
```

El reemplazo usa un patrón semántico tolerante a whitespace y falla el build si no encuentra exactamente un guard, para evitar servir silenciosamente lógica antigua. La autoridad continúa en backend.

La consola IAM debe considerar `requests:read` como baseline y no como autoridad revocable; las asignaciones explícitas pueden existir por compatibilidad, pero no cambian el resultado efectivo.

## Compatibilidad legacy

Se mantiene temporalmente:

- `UserRole.REQUESTER/VIEWER/...` en la tabla `users`;
- `can_view` como alias transitorio del response model;
- rutas legacy en `expenses.py` detrás de routers canónicos;
- la implementación visual de `ExpenseTable` dentro de `main.jsx`.

Ninguno de esos elementos puede limitar la lectura base ni ampliar la facultad de cancelar solicitudes ajenas.

## Pruebas

`backend/tests/test_universal_tracking.py` debe verificar:

1. usuario activo sin asignaciones recibe `requests:read`;
2. `/api/auth/me` devuelve `can_view=true` y otros permisos falsos;
3. un REQUESTER puede ver una solicitud creada por otro usuario;
4. cualquier usuario activo puede cargar `/api/expenses/dashboard`;
5. `users_with_permission('requests:read')` contiene todos los usuarios activos;
6. lectura base no permite `/close` sin `requests:close`.

`backend/tests/test_request_cancellation.py` debe verificar:

1. el solicitante recibe `can_cancel=true` para su solicitud abierta;
2. otro usuario recibe `can_cancel=false` para esa solicitud;
3. un usuario ajeno con `requests:create` recibe 403 al intentar cancelarla;
4. el solicitante puede cancelar su MULTI_QUOTE durante `QUOTATION_VOTING`;
5. la cuenta técnica puede cancelar cualquier solicitud abierta;
6. ni la cuenta técnica puede cancelar una solicitud cerrada.

La suite IAM existente continúa verificando la política especial de cuenta técnica.

## Datos y migraciones

No se requiere migración de esquema. `requests:read` ya existe en el catálogo de permisos y los campos de cancelación ya forman parte de `expenses`.

La feature cambia resolución/autorización en runtime. No se deben crear asignaciones masivas redundantes de `requests:read` ni backfills IAM basados en flags legacy para implementar esta feature.

## Despliegue

1. CI backend/tests.
2. Build frontend y Docker.
3. Merge a `main`.
4. Render despliega backend; Alembic permanece en `20260817_0003` porque esta feature no agrega migración.
5. Vercel despliega frontend normal; no requiere variable adicional.
6. Smoke test con un usuario sin roles:
   - login;
   - Inicio visible;
   - dashboard carga;
   - Solicitudes muestra solicitudes de otros usuarios;
   - acciones no autorizadas siguen ocultas/403.
7. Smoke test de cancelación:
   - solicitante ve `Cancelar solicitud` en una solicitud abierta propia, incluida `QUOTATION_VOTING`;
   - usuario ajeno no ve la acción y obtiene 403 si fuerza el endpoint;
   - Administrador del sistema ve la acción en cualquier solicitud abierta;
   - motivo queda persistido tras cancelar.
