# Modelo IAM configurable

## Objetivo

Permitir que cada organización configure acceso sin hardcodear nombres, cargos o correos y distinguir claramente **permisos IAM** de **capacidades por recurso** y **tareas contextuales**.

## Modelo

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ baseline requests:read
```

Persistencia:

```text
permissions
roles
role_permissions
user_groups
group_members
group_roles
user_role_assignments
user_permissions
positions
user_positions
position_roles
system_accounts
```

## Permisos atómicos

```text
requests:read
requests:create
requests:approve
requests:close
config:manage
```

Para usuario activo:

```text
effective_permissions =
    {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
```

`requests:read` es baseline. Para permisos mutables configurables, ausencia de ALLOW implica DENY.

## Grupo y Cargo

Cargo/Posición puede heredar Roles, pero su nombre no autoriza.

```text
Cargo Tesorero → Rol Aprobador → requests:approve
```

Correcto: resolver relaciones persistidas.

Prohibido:

```python
if user.title == 'TESORERO':
    allow_approve()
```

Grupo y Cargo son fuentes independientes y acumulativas.

## Fuentes visibles

`permission_sources()` puede explicar:

```text
Acceso base del producto
Asignación directa
Rol directo: Comprador
Grupo Junta Directiva → Aprobador
Cargo Tesorero → Aprobador
```

## Capacidades por recurso no son permisos IAM

### Cancelación

```text
can_cancel(expense, user) =
    estado cancelable
    AND (requester OR system_accounts)
```

### Corrección

```text
can_correct(expense, user) =
    estado corregible
    AND (requester OR system_accounts)
```

Por tanto:

- `requests:create` permite crear nuevas solicitudes, no editar solicitudes ajenas;
- `requests:approve` no permite corregir solicitudes ajenas;
- `config:manage` no permite corregir/cancelar solicitudes ajenas;
- Grupo/Rol/Cargo no amplían estas reglas por recurso;
- frontend consume `can_cancel`/`can_correct`, pero backend siempre vuelve a autorizar.

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

Estados no corregibles:

```text
CLOSED
CANCELLED
```

## Tareas contextuales no son permisos IAM

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

se derivan de permiso + asignación + estado.

### `APPROVAL_DECISION`

```text
requests:approve
+ Approval.PENDING asignado
+ PENDING_APPROVAL
```

### `QUOTATION_VOTE`

```text
requests:approve
+ invitación vigente
+ QUOTATION_VOTING
+ sin voto
```

### `CORRECT_REQUEST`

```text
NEEDS_REVISION
+ requested_by == current_user.email
```

No requiere `requests:create`: la tarea de corrección pertenece al solicitante original.

### `CLOSE_REQUEST`

```text
requests:close
+ APPROVED
```

`pending_action_service.py` resuelve estas tareas y `GET /api/expenses/{request_id}/my-actions` las revalida.

## Enviar a revisión tampoco es un permiso nuevo

**Enviar a revisión** es una decisión disponible dentro de una `APPROVAL_DECISION` ya asignada al usuario.

Requiere:

```text
requests:approve
+ Approval.PENDING asignado
+ comentario >= 3 caracteres
```

Una `REVISION_REQUESTED` válida interrumpe el flujo inmediatamente:

```text
request → NEEDS_REVISION
otros pasos PENDING/WAITING → EXPIRED
requester → CORRECT_REQUEST
```

El aprobador no adquiere `can_correct` por enviar la solicitud a revisión.

## `TECHNICAL_ADMIN`

Identidad persistida en `system_accounts`.

### Producción

IAM efectivo máximo:

```text
config:manage
requests:read
```

Se filtran `requests:create`, `requests:approve`, `requests:close` aunque lleguen por Grupo/Cargo/Rol/directo.

No participa en poblaciones financieras ni recibe tareas financieras.

Excepciones administrativas por recurso:

```text
can_cancel
can_correct
```

Estas excepciones no cambian sus permisos IAM.

### No producción

Para `ENVIRONMENT != production`, obtiene todos los permisos atómicos activos para pruebas E2E y puede participar en workflows salvo exclusiones intrínsecas.

## Consola autoritativa

**Configuración → Accesos** administra IAM canónico.

La pantalla legacy `AccessProfile`, `users.title`, `can_*` y `BOARD_CODES` puede existir como compatibilidad/migración, pero no autoriza runtime.

## Migración 0004

```text
20260818_0004_position_role_inheritance.py
```

crea `position_roles` e importa una sola vez configuración legacy hacia `Position → Role → Permission`, excluyendo cuentas técnicas de asignaciones organizacionales migradas.

Después del upgrade, runtime sigue usando IAM canónico.

Feature 007 (Enviar a revisión + propiedad de corrección) no agrega permiso ni migración nueva.

## Pruebas mínimas

- permiso directo;
- Rol directo;
- Grupo → Rol;
- Cargo → Rol;
- Cargo inactivo;
- fuentes efectivas;
- `users_with_permission()` con Grupo/Cargo;
- política técnica producción/no-producción;
- `can_cancel` requester/Admin;
- `can_correct` requester/Admin;
- tercero con `requests:create/approve/config` no corrige ajena;
- `CORRECT_REQUEST` solo al solicitante;
- `REVISION_REQUESTED` no otorga edición al aprobador.
