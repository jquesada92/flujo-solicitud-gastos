# Plan técnico — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.5.0

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

Las acciones personales del Inicio se resuelven en dos niveles:

```text
IAM efectivo
   ↓
¿el usuario posee la capacidad general?
   ↓
asignación/estado concreto del workflow
   ↓
acción pendiente para ese usuario
```

Por ejemplo, `requests:approve` habilita la capacidad de aprobar, pero una solicitud solo aparece como **Responder aprobación** cuando existe un `Approval.PENDING` asignado al correo del usuario actual.

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
          ∪ position-role permissions
```

Para cuentas técnicas, la política ambiental se combina con el baseline. Producción continúa limitada a `config:manage + requests:read` como permisos IAM; la cancelación es una facultad explícita de administración de ciclo de vida definida por identidad de `system_accounts`, no un permiso financiero heredable.

`permission_sources()` debe explicar el origen:

```text
Acceso base del producto para usuarios activos
```

`users_with_permission('requests:read')` debe devolver todos los usuarios activos.

## Rutas canónicas de seguimiento

`app/api/tracking.py` se registra antes de `expenses.py` legacy.

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
- usa `pending_action_service.py` para resolver acciones personales;
- `pending_my_action` cuenta acciones concretas vigentes, no solo solicitudes;
- cada `pending_item` incluye códigos de acción backend-authoritative;
- limita la lista visual inicial a ocho solicitudes, manteniendo el total de acciones independiente.

Acciones actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Resolver de acciones personales

Se agrega `app/services/pending_action_service.py`.

`pending_actions_by_expense(db, user)` combina permisos efectivos y estado/asignación concreta:

### `APPROVAL_DECISION`

Requiere:

- `requests:approve` efectivo;
- `Approval.status=PENDING`;
- `approver_email == current_user.email`;
- solicitud todavía en `PENDING_APPROVAL`.

### `QUOTATION_VOTE`

Requiere:

- `requests:approve` efectivo;
- invitación `QuotationVotingInvitation` para `current_user.id`;
- solicitud en `QUOTATION_VOTING`;
- ausencia de `QuotationVote` del usuario para esa solicitud.

### `CORRECT_REQUEST`

Requiere:

- `requests:create` efectivo;
- solicitud en `NEEDS_REVISION`;
- `requested_by == current_user.email`.

### `CLOSE_REQUEST`

Requiere:

- `requests:close` efectivo;
- solicitud en `APPROVED`.

El servicio acepta opcionalmente `expense_ids` para revalidar una solicitud concreta sin calcular toda la bandeja.

## API contextual de acciones

Se agrega `app/api/my_actions.py` y se registra antes del router legacy.

### `GET /api/expenses/{request_id}/my-actions`

- requiere `requests:read`;
- recarga la solicitud y sus soportes/opciones;
- vuelve a ejecutar `pending_actions_by_expense()` para el usuario actual;
- devuelve únicamente acciones todavía vigentes;
- devuelve el detalle requerido por el modal;
- no expone tokens bearer de correo.

### `POST /api/expenses/{request_id}/approval-decision`

- requiere `requests:approve`;
- localiza y bloquea la solicitud;
- rechaza autoaprobación;
- exige que exista un `Approval.PENDING` asignado al usuario actual;
- reutiliza `approval_engine.apply_decision()`;
- permite `APPROVED`, `REJECTED` y `REVISION_REQUESTED` con las mismas reglas del motor existente.

Las demás acciones reutilizan endpoints canónicos existentes:

```text
POST /api/expenses/{request_id}/quotation-vote
POST /api/expenses/{request_id}/close
```

La corrección reutiliza el editor canónico de Solicitudes; el modal ofrece **Abrir para corregir / reenviar**.

## Cancelación canónica

`app/api/cancellation_actions.py` se registra antes de `expenses.py` legacy.

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

Se agrega:

```text
frontend/src/home-dashboard.jsx
frontend/src/home-dashboard.css
```

`HomeDashboard` pasa a ser un componente modular. Mientras `main.jsx` conserve su implementación histórica, `vite.config.js` elimina la función legacy completa entre:

```text
function HomeDashboard(...)
function App()
```

e importa el componente modular. No se parchean handlers internos por coincidencias de whitespace.

### Comportamiento

- **Ver todas** continúa ejecutando `onOpenRequests` y navega a Solicitudes.
- una fila de `pending_items` ejecuta `openAction(item)`;
- `openAction` consulta `/{request_id}/my-actions`;
- el modal muestra resumen de la solicitud y únicamente controles vigentes;
- antes de cada mutación la autorización se vuelve a comprobar en backend;
- después de una mutación se recargan en paralelo dashboard + detalle contextual;
- si la acción ya fue respondida desde otro canal, el modal muestra que ya no quedan acciones pendientes.

Controles:

- aprobación: comentario + Rechazar / Solicitar corrección / Aprobar;
- votación: opciones, soportes y botón de voto por opción;
- cierre: factura + notas + cerrar;
- corrección: navegación explícita al editor de Solicitudes.

El modal es accesible como `role=dialog`, `aria-modal=true`, cierra con Escape y soporta layout móvil.

La tabla legacy de Solicitudes continúa consumiendo `can_cancel` para cancelación hasta su modularización.

## Compatibilidad legacy

Se mantiene temporalmente:

- `UserRole.REQUESTER/VIEWER/...` en la tabla `users`;
- `can_view` como alias transitorio del response model;
- rutas legacy en `expenses.py` detrás de routers canónicos;
- partes de `ExpenseTable` dentro de `main.jsx`;
- definición histórica de `HomeDashboard` dentro de `main.jsx`, eliminada del bundle por la extracción modular de Vite.

Ninguno de esos elementos puede limitar la lectura base, ampliar cancelación ni determinar qué acción personal corresponde al usuario.

## Pruebas

`backend/tests/test_universal_tracking.py` verifica lectura universal.

`backend/tests/test_request_cancellation.py` verifica cancelación por solicitante/cuenta técnica.

`backend/tests/test_pending_actions.py` verifica:

1. aprobación pendiente aparece como `APPROVAL_DECISION`;
2. el detalle contextual devuelve la misma acción;
3. la aprobación puede registrarse desde el endpoint autenticado por request sin exponer token de correo;
4. después de responder, `my-actions` queda vacío si no surge otra tarea;
5. una invitación MULTI_QUOTE no respondida aparece como `QUOTATION_VOTE` y devuelve opciones;
6. `NEEDS_REVISION` propia aparece como `CORRECT_REQUEST`;
7. `APPROVED` aparece como `CLOSE_REQUEST` solo a quien tenga `requests:close`.

`backend/tests/test_frontend_dashboard_contract.py` protege:

- click de fila → `openAction(item)`;
- presencia del modal contextual;
- los cuatro códigos actuales;
- endpoints usados por aprobación/voto/cierre;
- revalidación posterior a mutación;
- extracción completa del `HomeDashboard` legacy durante build.

## Datos y migraciones

El modal contextual y el resolver de acciones no requieren columnas nuevas.

La rama contiene además Feature 006, cuya migración `20260818_0004_position_role_inheritance.py` es independiente de este cambio. La cadena global de la rama es:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

No crear un backfill adicional para las acciones pendientes.

## Despliegue

1. Ejecutar localmente backend tests porque el límite de GitHub Actions está agotado.
2. Ejecutar `npm run build` del frontend.
3. Construir imágenes Docker localmente.
4. Probar en Docker:
   - iniciar sesión como usuario con aprobación pendiente;
   - seleccionar una fila en **Acciones pendientes**;
   - confirmar apertura del modal, no navegación inmediata a Solicitudes;
   - aprobar/rechazar/solicitar corrección y verificar que la acción desaparezca o cambie;
   - probar una invitación MULTI_QUOTE y voto;
   - probar cierre para un usuario con `requests:close`.
5. Feature 006 requiere además smoke de Alembic `0004` antes de producción.
6. Merge a `main` solo después de esas validaciones locales mientras CI remoto no esté disponible.
