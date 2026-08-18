# Modelo IAM configurable

## Objetivo

Permitir que cada organización configure acceso sin hardcodear nombres, cargos o correos y distinguir **permisos IAM**, **capacidades por recurso**, **delegaciones** y **tareas contextuales**.

## Modelo

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ baseline requests:read
       ↘ capacidades/delegaciones por recurso
```

Persistencia IAM:

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

La delegación de cierre se persiste aparte en `expense_closure_delegations` porque pertenece a una solicitud concreta, no a la organización global.

## Permisos IAM operativos

```text
requests:read
requests:create
requests:approve
config:manage
```

`requests:close` permanece físicamente como registro **legacy inactivo** después de Alembic `0005`. No autoriza runtime ni debe configurarse para conseguir cierre/factura.

Para usuario activo:

```text
effective_permissions =
    {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
```

`requests:read` es baseline. Para permisos mutables IAM, ausencia de ALLOW implica DENY.

## Grupo y Cargo

Cargo/Posición puede heredar Roles, pero su nombre no autoriza.

```text
Cargo Tesorero → Rol Aprobador → requests:approve
```

Grupo y Cargo son fuentes independientes y acumulativas. Prohibido autorizar con comparaciones de nombres.

## Fuentes visibles

`permission_sources()` puede explicar:

```text
Acceso base del producto
Asignación directa
Rol directo: Comprador
Grupo Junta Directiva → Aprobador
Cargo Tesorero → Aprobador
```

Una delegación de cierre no aparece como permiso efectivo porque **no es un permiso IAM**; se presenta en el contexto de la solicitud.

## Capacidades por recurso

### Cancelación

```text
can_cancel = estado cancelable AND (requester OR system_accounts)
```

### Corrección

```text
can_correct = estado corregible AND (requester OR system_accounts)
```

### Cierre/factura

```text
can_close =
  status ∈ {APPROVED, CLOSED}
  AND (requester OR system_accounts OR active_closure_delegate)
```

### Administración de delegación

```text
can_delegate_close = requester original
```

Solo el solicitante crea/cambia/revoca la delegación. El Administrador del sistema ya posee la excepción administrativa y no necesita una delegación.

Por tanto:

- `requests:create` no permite corregir/cancelar/cerrar solicitudes ajenas;
- `requests:approve` no permite editar ni cerrar solicitudes ajenas;
- `config:manage` no permite sustituir al solicitante;
- `requests:close` legacy no concede nada en runtime;
- Grupo/Rol/Cargo no amplían estas reglas por recurso;
- frontend consume `can_cancel`, `can_correct`, `can_close`, `can_delegate_close`; backend siempre revalida.

## Tareas contextuales

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

### `APPROVAL_DECISION`

```text
requests:approve + Approval.PENDING asignado + PENDING_APPROVAL
```

### `QUOTATION_VOTE`

```text
requests:approve + invitación vigente + QUOTATION_VOTING + sin voto
```

### `CORRECT_REQUEST`

```text
NEEDS_REVISION + requested_by == current_user.email
```

### `CLOSE_REQUEST`

```text
APPROVED + (requester original OR active_closure_delegate)
```

El Administrador del sistema conserva facultad administrativa desde la lista, pero no recibe todas las solicitudes aprobadas como tareas personales.

## Enviar a revisión

Es una decisión dentro de una aprobación asignada, no un permiso nuevo:

```text
requests:approve
+ Approval.PENDING
+ comentario >= 3
```

Una `REVISION_REQUESTED` válida interrumpe inmediatamente:

```text
request → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester → CORRECT_REQUEST
```

No concede `can_correct` al aprobador.

## `TECHNICAL_ADMIN`

Identidad persistida en `system_accounts`.

### Producción

IAM máximo:

```text
config:manage
requests:read
```

No participa en aprobación/votación. Excepciones administrativas por recurso:

```text
can_cancel
can_correct
can_close
```

No administra delegaciones ordinarias en nombre del solicitante.

### No producción

`ENVIRONMENT != production` obtiene todos los permisos IAM activos para pruebas E2E además de capacidades administrativas por recurso.

## Consola autoritativa

**Configuración → Accesos** administra IAM canónico. La delegación de cierre/factura se administra desde la solicitud.

`AccessProfile`, `users.title`, `can_*`, `BOARD_CODES` y `requests:close` legacy son compatibilidad/deuda y no autoridad runtime.

## Migraciones

```text
0004 → position_roles + importación legacy de Cargo/Perfil a IAM
0005 → expense_closure_delegations + requests:close inactivo/legacy
```

Cadena completa actual termina en `20260818_0005`.

## Pruebas mínimas

- permiso directo / Rol directo / Grupo→Rol / Cargo→Rol;
- Cargo inactivo y fuentes efectivas;
- política técnica producción/no-producción;
- `can_cancel` requester/Admin;
- `can_correct` requester/Admin;
- `CORRECT_REQUEST` solo solicitante;
- `can_close` requester/Admin/delegado;
- `requests:close` legacy no autoriza tercero;
- solo solicitante administra delegación;
- revocación elimina autoridad;
- `CLOSE_REQUEST` requester/delegado;
- una sola delegación activa por solicitud.
