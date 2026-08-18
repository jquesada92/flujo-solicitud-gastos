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

Para cuentas técnicas, la política ambiental se combina con el baseline. Producción continúa limitada a `config:manage + requests:read`; no producción conserva acceso total de prueba.

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
- presenta actor/nombres/eventos como el contrato existente.

### `GET /api/expenses/dashboard`

- requiere `requests:read`;
- expone métricas generales a todo usuario activo;
- calcula `pending_my_action` solo desde capacidades accionables:
  - `requests:approve` → aprobaciones/votaciones asignadas;
  - `requests:close` → solicitudes aprobadas pendientes de cierre;
- para votación usa `QuotationVotingInvitation` como población asignada, no todos los usuarios con permiso en abstracto.

## Frontend

No se requiere una nueva variable de Vite.

El shell actual ya presenta **Inicio** y **Solicitudes** para usuarios autenticados. `current_user()` deriva temporalmente:

```text
can_view = requests:read
```

por lo que un usuario sin roles recibe `can_view=true` al autenticarse.

La consola IAM debe considerar `requests:read` como baseline y no como autoridad revocable; las asignaciones explícitas pueden existir por compatibilidad, pero no cambian el resultado efectivo.

## Compatibilidad legacy

Se mantiene temporalmente:

- `UserRole.REQUESTER/VIEWER/...` en la tabla `users`;
- `can_view` como alias transitorio del response model;
- rutas legacy en `expenses.py` detrás del router canónico.

Ninguno de esos elementos puede limitar la lectura base.

## Pruebas

`backend/tests/test_universal_tracking.py` debe verificar:

1. usuario activo sin asignaciones recibe `requests:read`;
2. `/api/auth/me` devuelve `can_view=true` y otros permisos falsos;
3. un REQUESTER puede ver una solicitud creada por otro usuario;
4. cualquier usuario activo puede cargar `/api/expenses/dashboard`;
5. `users_with_permission('requests:read')` contiene todos los usuarios activos;
6. lectura base no permite `/close` sin `requests:close`.

La suite IAM existente continúa verificando la política especial de cuenta técnica.

## Datos y migraciones

No se requiere migración de esquema. `requests:read` ya existe en el catálogo de permisos.

La feature cambia la resolución efectiva en runtime. No se deben crear asignaciones masivas redundantes de `requests:read` para cada usuario.

## Despliegue

1. CI backend/tests.
2. Build frontend y Docker sin cambios especiales.
3. Merge a `main`.
4. Render despliega backend con la nueva resolución IAM.
5. Vercel despliega frontend normal; no requiere variable adicional.
6. Smoke test con un usuario sin roles:
   - login;
   - Inicio visible;
   - dashboard carga;
   - Solicitudes muestra solicitudes de otros usuarios;
   - acciones no autorizadas siguen ocultas/403.
