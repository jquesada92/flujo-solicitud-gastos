# Modelo IAM configurable

## Objetivo

Permitir que cada organización configure su estructura de acceso desde la interfaz gráfica sin hardcodear nombres, cargos o correos en el backend.

## Conceptos

### Usuario

Cuenta autenticable del sistema.

### Grupo

Conjunto configurable de usuarios con una responsabilidad común. Puede heredar uno o más Roles. Ejemplos como `Junta Directiva`, `Finance` o `Procurement` son datos del cliente, no conceptos del código.

### Rol

Conjunto reutilizable de permisos. El mismo Rol puede asignarse a Grupos, Cargos o directamente a Usuarios.

### Permiso

Capacidad atómica implementada por el producto. El permiso autoriza; el nombre de rol/grupo/cargo no.

### Cargo / Posición

Elemento configurable de la estructura organizacional. Puede representar Presidente, Gerente, Analista, Director, etc. **Puede heredar Roles**, pero su nombre nunca concede acceso por sí mismo.

Ejemplo válido:

```text
Cargo: Tesorero
  ↓
Rol: Aprobador
  ↓
requests:approve
```

Ejemplo prohibido:

```python
if user.title == 'TESORERO':
    allow_approve()
```

### Cuenta de sistema

Identidad técnica registrada en `system_accounts`. Su política puede diferir por ambiente sin depender de email, cargo ni `UserRole` legacy.

## Modelo

```text
permissions
   ↑
role_permissions ← roles ← group_roles ← user_groups ← group_members ← users
                         ↖ position_roles ← positions ← user_positions ← users
                         ↖ user_role_assignments ← users
permissions ← user_permissions ← users
system_accounts ← users
```

Forma conceptual:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
```

## Permisos iniciales

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

## Fórmula para usuarios operativos

Para todo usuario activo:

```text
effective_permissions(user) =
    {requests:read}
  ∪ direct permissions
  ∪ permissions from direct roles
  ∪ permissions from group roles
  ∪ permissions from position roles
```

`requests:read` es baseline del producto y no se revoca quitándolo de un rol/grupo/cargo. Para las capacidades mutables no hay DENY explícito en esta versión; la ausencia de ALLOW produce DENY.

## Herencia por Cargo

`position_roles` relaciona Cargos con Roles:

```text
Position 1 ─┐
Position 2 ─┼─→ Role Aprobador → requests:approve
Position 3 ─┘
```

Un usuario asignado mediante `user_positions` hereda los permisos de todos los Roles activos asociados a todos sus Cargos activos.

Si el Cargo o el Rol está inactivo, esa fuente deja de conceder permisos.

## Herencia por Grupo

La relación existente sigue siendo:

```text
User
 ↓
GroupMember
 ↓
UserGroup
 ↓
GroupRole
 ↓
Role
 ↓
RolePermission
 ↓
Permission
```

Cargo y Grupo son caminos independientes y acumulativos. Una organización puede usar solo uno o combinar ambos.

## Fuentes visibles

`permission_sources()` debe poder devolver, entre otras:

```text
Acceso base del producto para usuarios activos
Asignación directa
Rol directo: Comprador
Grupo Junta Directiva → Aprobador
Cargo Tesorero → Aprobador
```

Esto permite saber no solo qué puede hacer el usuario, sino por qué.

## Cancelación no es `requests:create`

La facultad de cancelar una solicitud abierta se resuelve por identidad/propiedad del recurso y no por una asignación IAM heredable.

```text
can_cancel(expense, user) =
    expense.status está abierto
    AND (
        expense.requested_by == user.email
        OR user ∈ system_accounts
    )
```

Por tanto:

- el solicitante original puede cancelar su propia solicitud abierta;
- el Administrador del sistema puede cancelar cualquier solicitud abierta;
- otro usuario con `requests:create`, `requests:approve` o `config:manage` no puede cancelar una solicitud ajena por esos permisos;
- el frontend recibe `can_cancel` calculado por el backend y no debe reconstruir esta regla localmente.

## Acciones pendientes no son nuevos permisos IAM

Los códigos del dashboard:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

**no son permisos** y no deben agregarse al catálogo `permissions`.

Representan tareas contextuales derivadas de:

```text
permiso efectivo
+
asignación concreta del workflow
+
estado actual de la solicitud
```

Ejemplos:

```text
requests:approve
+ Approval.PENDING asignado al usuario
→ APPROVAL_DECISION

requests:approve
+ invitación de votación vigente sin voto
→ QUOTATION_VOTE

requests:create
+ solicitud propia NEEDS_REVISION
→ CORRECT_REQUEST

requests:close
+ solicitud APPROVED
→ CLOSE_REQUEST
```

Esto evita multiplicar permisos por cada estado del workflow. IAM responde **qué capacidades generales tiene el usuario**; `pending_action_service.py` responde **qué tarea concreta requiere su intervención ahora**.

La consulta contextual `GET /api/expenses/{request_id}/my-actions` vuelve a calcular estas tareas antes de mostrar controles en el modal de Inicio.

## Política de `TECHNICAL_ADMIN`

La cuenta técnica no usa la fórmula normal como autoridad final. `iam_service.py` aplica una política ambiental explícita sobre el catálogo de permisos activos.

### Producción

Cuando:

```env
ENVIRONMENT=production
```

la cuenta técnica obtiene únicamente como permisos IAM:

```text
config:manage
requests:read
```

La política filtra cualquier asignación accidental de:

```text
requests:create
requests:approve
requests:close
```

incluso si llega por Grupo, Cargo, Rol directo o Permiso directo, y la excluye de poblaciones financieras para esos permisos.

La cancelación administrativa de una solicitud abierta es una excepción explícita de ciclo de vida basada en `system_accounts`; no otorga ni implica los permisos financieros anteriores.

En consecuencia, en producción la cuenta técnica tampoco recibe tareas contextuales financieras como `APPROVAL_DECISION`, `QUOTATION_VOTE` o `CLOSE_REQUEST`.

### No producción

Para cualquier `ENVIRONMENT` distinto de `production`, incluidos `local`, `development`, `dev`, `test`, `staging` y `preview`:

```text
TECHNICAL_ADMIN effective permissions = todos los permisos activos
```

La cuenta puede probar end-to-end:

- creación/corrección;
- consulta;
- aprobación;
- votación de cotizaciones;
- carga/reemplazo de factura;
- cierre;
- cancelación;
- configuración.

También puede aparecer en `users_with_permission('requests:approve')` fuera de producción.

Esta elevación no se persiste como permisos financieros en el rol system-managed. Cambiar el runtime a `ENVIRONMENT=production` restablece la segregación sin migración de datos.

## Ambiente vs hosting

`Settings` mantiene dos conceptos separados:

```text
is_production_environment
→ solo ENVIRONMENT=production
→ gobierna autorización de cuenta técnica

is_production
→ production o runtime alojado como Render
→ gobierna validaciones estrictas de secretos/CORS
```

Por tanto un preview alojado puede exigir secretos fuertes y, a la vez, permitir pruebas funcionales completas si `ENVIRONMENT` no es `production`.

## Contrato de permisos del usuario actual

El backend expone:

```text
permission_codes
```

como lista canónica de permisos efectivos.

Compatibilidad temporal:

```text
can_request   = requests:create
can_approve   = requests:approve
can_view      = requests:read
can_configure = config:manage
can_close     = requests:close
```

`apply_effective_permissions_to_user()` deriva estos valores. No se usan como fuente de autorización.

En respuestas de solicitudes, `can_cancel` es una capacidad por recurso calculada por el backend y no forma parte de `permission_codes`.

Las acciones contextuales del dashboard tampoco forman parte de `permission_codes`; se consultan por solicitud mediante `my-actions`.

## Administración gráfica

`Configuración → Accesos` expone:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos;
- Roles heredados por Grupo;
- Roles heredados por Cargo;
- membresías/asignaciones;
- permisos efectivos y su origen.

### Grupos

Un Grupo permite administrar:

```text
Miembros
Roles heredados
```

### Cargos

Un Cargo permite administrar:

```text
Nombre / descripción / estado
Roles heredados
```

Todos los usuarios asignados al Cargo reciben los permisos de esos Roles de forma inmediata en la resolución backend.

`requests:read` debe mostrarse como baseline efectivo para usuarios activos aunque no exista asignación explícita.

Para cuentas técnicas, `permission_sources()` identifica si el acceso proviene de:

```text
Política de cuenta técnica (producción)
```

o:

```text
Acceso de prueba de cuenta técnica (no producción)
```

## APIs

Base `/api/iam`:

```text
GET  /me/permissions
GET  /permissions
GET  /roles
POST /roles
PATCH /roles/{id}
GET  /groups
POST /groups
PATCH /groups/{id}
PUT/DELETE /groups/{group_id}/roles/{role_id}
PUT/DELETE /groups/{group_id}/members/{user_id}
GET  /positions
POST /positions
PATCH /positions/{id}
PUT/DELETE /positions/{position_id}/roles/{role_id}
PUT/DELETE /users/{user_id}/roles/{role_id}
PUT/DELETE /users/{user_id}/permissions/{code}
GET /users/{user_id}/effective-permissions
```

Base `/api/iam/users` ofrece administración neutral de usuarios, Grupos, Cargos, Roles directos y permisos directos.

Las APIs `/api/expenses/{request_id}/my-actions` pertenecen al workflow y no a IAM porque describen tareas concretas, no asignaciones de acceso.

## Participación en workflows

Aprobadores/votantes se descubren por `requests:approve` usando `users_with_permission()`.

Fuentes canónicas elegibles:

```text
Permiso directo
Rol directo
Grupo → Rol → Permiso
Cargo → Rol → Permiso
```

No se consulta:

- `UserRole.APPROVER`;
- `can_approve` persistido;
- si el cargo se llama Presidente/Tesorero/etc.;
- si un grupo tiene un nombre particular.

Comportamiento de cuenta técnica:

- producción: excluida de poblaciones financieras;
- no producción: puede participar para pruebas si el flujo no la excluye por otra razón, por ejemplo ser el solicitante.

Las invitaciones de una votación representan el snapshot de participantes de esa ronda.

## Migración `0004`

`20260818_0004_position_role_inheritance.py` agrega `position_roles`.

Para preservar la configuración de producción existente, realiza una importación única desde:

```text
access_profiles.can_*
users.title
```

hacia:

```text
Position
Role
RolePermission
PositionRole
UserPosition
```

Esto permite que cargos legacy configurados como aprobadores pasen a otorgar realmente `requests:approve` mediante IAM.

La migración puede contener nombres legacy como datos de compatibilidad histórica, pero el runtime posterior no los consulta para autorización.

## Compatibilidad legacy

Los campos `role`, `title`, `can_*`, `AccessProfile` y `BOARD_CODES` aún pueden existir físicamente durante la transición.

No son autoridad de runtime.

La pantalla autoritativa para cambios de acceso es **Configuración → Accesos**. La administración legacy de perfiles/cargos debe retirarse o convertirse en una vista de compatibilidad para evitar volver a divergir de IAM.

`UserOut.permission_codes` y `UserOut.can_close` permiten migrar el frontend hacia capacidades reales.

El frontend monolítico todavía contiene bypasses visuales legacy como `user.role === "ADMIN"` y un `canClose={true}`. No son autoridad y deben retirarse en la modularización del frontend.

La cancelación ya no confía en esos bypasses: el listado canónico devuelve `can_cancel` y el endpoint vuelve a validar propiedad/cuenta técnica.

## Evolución futura

Posibles extensiones:

- scopes por organización;
- scopes por Área/recurso;
- DENY explícito con precedencia;
- SSO/OIDC;
- SCIM;
- grupos jerárquicos;
- jerarquía de cargos;
- permisos temporales;
- aprobaciones de cambios IAM;
- auditoría IAM completa append-only.
