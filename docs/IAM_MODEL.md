# Modelo IAM configurable

## Objetivo

Permitir que cada organización configure acceso sin hardcodear nombres, cargos o correos y distinguir claramente:

- permisos IAM;
- capacidades system-only;
- lectura de Configuración;
- capacidades por recurso;
- delegaciones;
- tareas contextuales.

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

La delegación de cierre se persiste aparte en `expense_closure_delegations` porque pertenece a una solicitud concreta.

## Permisos IAM vigentes

```text
requests:read     baseline de consulta
requests:create   crear nuevas solicitudes
requests:approve  aprobar/votar/enviar a revisión
areas:manage      administrar Área + Categoría
config:read       consultar Configuración
config:manage     administración técnica system-only
```

`requests:close` permanece físicamente como registro legacy inactivo. No autoriza runtime ni debe configurarse para conseguir cierre/factura.

Para usuario activo ordinario:

```text
effective_permissions =
    {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
  - {config:manage}
```

`requests:read` es baseline. `config:manage` es system-only. `config:read` y `areas:manage` sí pueden heredarse por las vías IAM ordinarias.

## Configuración

### `config:manage`

Reservado a cuentas persistidas en `system_accounts`.

Gobierna mutaciones de administración técnica. La superficie IAM canónica es:

```text
Configuración → Accesos
```

**Usuarios/Personas y Organigrama no son pantallas administrativas independientes.**

Accesos concentra:

```text
Usuarios
Grupos
Roles
Permisos
Cargos/Posiciones
Asignaciones
Permisos efectivos/fuentes
```

### `config:read`

Permiso de lectura configurable.

```text
config:read
→ Accesos solo lectura
→ Áreas solo lectura salvo areas:manage
→ Reglas solo lectura
→ Auditoría solo lectura
```

No concede mutaciones y no se convierte en `config:manage`.

### `areas:manage`

Permiso organizacional configurable. Puede llegar por:

```text
Permiso directo
Rol directo
Grupo → Rol
Cargo → Rol
```

Gobierna:

```text
Áreas
Categorías
activación/desactivación
relaciones Área ↔ Categoría
```

Alembic `0006` crea `Gestor de áreas`. Alembic `0007` crea `Visor de configuración`. Ninguna migración debe autorizar por nombres organizacionales.

## Grupo y Cargo

Cargo/Posición puede heredar Roles, pero su nombre no autoriza.

```text
Cargo X → Rol Aprobador → requests:approve
Grupo Y → Rol Visor de configuración → config:read
```

Grupo y Cargo son fuentes independientes y acumulativas.

## Accesos como única fuente de administración

Toda creación/configuración de usuarios e IAM debe realizarse dentro de Accesos.

No debe requerirse una pantalla separada para:

- crear usuarios;
- activar/inactivar usuarios;
- asignar Cargos;
- asignar Grupos;
- asignar Roles/Permisos;
- visualizar permisos efectivos.

Vistas legacy `people` / `organization` pueden permanecer internamente de forma temporal, pero no son navegables ni autoridad.

## Notificaciones de Cargo y permisos efectivos

### Creación de usuario

Después de aplicar las asignaciones iniciales, la invitación con contraseña temporal incluye:

```text
Cargo(s) activos
Permisos efectivos
```

### Cambio de Cargo

Cuando cambia realmente `position_ids` de un usuario activo:

1. se aplican los nuevos `UserPosition`;
2. se recalculan permisos efectivos;
3. se envía **Actualización de cargo y permisos**;
4. si falla la entrega obligatoria, la transacción se revierte.

Guardar el mismo conjunto de Cargos no genera notificación duplicada.

Las fuentes de verdad son `UserPosition → Position` y `effective_permission_codes()`.

## Fuentes visibles

`permission_sources()` puede explicar:

```text
Acceso base del producto
Asignación directa
Rol directo
Grupo → Rol
Cargo → Rol
```

Una delegación de cierre no aparece como permiso efectivo porque no es IAM global.

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

### Delegación

```text
can_delegate_close = requester original
```

Por tanto:

- `requests:create` no permite corregir/cancelar/cerrar solicitudes ajenas;
- `requests:approve` no permite editar ni cerrar solicitudes ajenas;
- `config:read` no concede mutaciones;
- `config:manage` no sustituye automáticamente al solicitante en reglas ordinarias;
- `requests:close` legacy no concede autoridad;
- frontend consume `can_*` por recurso y backend revalida.

## Tareas contextuales

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

```text
APPROVAL_DECISION = requests:approve + Approval.PENDING + PENDING_APPROVAL
QUOTATION_VOTE    = requests:approve + invitación vigente + QUOTATION_VOTING + sin voto
CORRECT_REQUEST   = NEEDS_REVISION + requester actual
CLOSE_REQUEST     = APPROVED + (requester OR active_closure_delegate)
```

## Enviar a revisión

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

Se identifica mediante `system_accounts`.

### Producción

```text
config:manage
config:read
areas:manage
requests:read
```

No participa en aprobación/votación. Conserva excepciones administrativas por recurso para cancelar, corregir y gestionar cierre/factura.

### No producción

Puede recibir todos los permisos activos para pruebas E2E según política de ambiente.

## Navegación de Accesos

La consola se monta temporalmente mediante `#access-management`.

La navegación superior debe seguir funcionando y cerrar la consola en el mismo clic al ir a otra pantalla.

Implementación transitoria:

```text
frontend/src/access-navigation-bridge.js
```

Casos mínimos:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

Abrir/cerrar únicamente el dropdown Configuración no abandona Accesos.

## Prohibiciones

No autorizar por:

- `UserRole`;
- `can_*` legacy;
- `BOARD_CODES`;
- email fijo;
- ID mágico;
- nombre/código de Rol, Grupo o Cargo;
- conceptos inmobiliarios.

## Compatibilidad

Pueden permanecer temporalmente `UserRole`, `AccessProfile`, flags `can_*`, `title`, `/api/users`, vistas `people` / `organization` y bridges Vite. No son arquitectura objetivo ni fuente de verdad.
