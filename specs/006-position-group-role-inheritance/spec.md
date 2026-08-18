# Especificación funcional — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución:** 2.5.0

## Objetivo

Permitir que una organización configure acceso por estructura organizacional sin hardcodear nombres de cargos o grupos.

Un usuario puede heredar permisos mediante:

```text
Usuario → Cargo/Posición → Rol → Permiso
Usuario → Grupo          → Rol → Permiso
Usuario → Rol directo    → Permiso
Usuario → Permiso directo
```

Los caminos son acumulativos.

## Historia principal

**Como administrador de accesos**, quiero poder asignar Roles a Cargos y a Grupos, para que todos los usuarios asociados hereden automáticamente los permisos correspondientes sin tener que configurar cada usuario individualmente.

## Reglas funcionales

### F-006-01 — Cargo puede heredar Roles

Cada Cargo/Posición configurable puede tener cero o más Roles activos.

Ejemplo de datos de una organización:

```text
Rol: Aprobador
  requests:approve

Cargo: Presidente      → Aprobador
Cargo: Vicepresidente  → Aprobador
Cargo: Tesorero        → Aprobador
```

El sistema NO debe contener condiciones runtime como:

```text
if cargo in ['PRESIDENTE', 'TESORERO']:
    permitir_aprobar()
```

La autorización existe porque la relación persistida `Cargo → Rol → Permiso` existe.

### F-006-02 — Grupo puede heredar Roles

La capacidad existente Grupo → Rol → Permiso continúa siendo canónica.

Ejemplo:

```text
Grupo: Junta Directiva
  miembros:
    - Usuario A
    - Usuario B
    - Usuario C
  roles:
    - Aprobador
```

Todos los miembros activos heredan los permisos del Rol Aprobador.

### F-006-03 — Mismo Rol reutilizable

Un Rol puede asociarse simultáneamente a múltiples Cargos y Grupos.

No debe ser necesario crear `Aprobador Presidente`, `Aprobador Tesorero`, etc. si todos comparten la misma combinación de permisos.

### F-006-04 — Unión de permisos efectivos

Para usuario activo no técnico:

```text
effective = baseline
          ∪ permisos directos
          ∪ roles directos
          ∪ roles por grupos activos
          ∪ roles por cargos activos
```

No existe DENY individual en esta versión; las fuentes ALLOW se acumulan.

### F-006-05 — Cargo inactivo

Un Cargo inactivo no concede permisos aunque el usuario conserve históricamente la asignación.

Un Rol inactivo tampoco concede permisos.

### F-006-06 — Poblaciones de workflow

`users_with_permission(permission_code)` debe usar exactamente las mismas fuentes efectivas.

Por tanto, un usuario que recibe `requests:approve` por Cargo o Grupo debe aparecer en la población de aprobadores/votantes, salvo exclusiones propias del workflow, por ejemplo:

- ser el solicitante de la misma solicitud;
- ser cuenta técnica en producción.

### F-006-07 — Origen visible

La UI de permisos efectivos debe poder indicar el origen, por ejemplo:

```text
requests:approve
  Cargo Tesorero → Aprobador

requests:create
  Grupo Compras → Solicitante
```

### F-006-08 — Configuración gráfica

En **Configuración → Accesos → Cargos** se puede:

- crear/renombrar/activar/inactivar Cargos;
- seleccionar un Cargo;
- asignar/quitar Roles heredados.

En **Configuración → Accesos → Grupos** se conserva la administración de miembros y Roles heredados.

En **Usuarios**, la asignación de Cargos y Grupos continúa siendo configurable.

### F-006-09 — Cuenta técnica

La cuenta protegida `system_accounts` no obtiene permisos financieros productivos por pertenecer accidentalmente a un Cargo/Grupo/Rol.

La política ambiental de cuenta técnica prevalece sobre cualquier asignación organizacional.

## Migración de configuración existente

La migración `20260818_0004` crea `position_roles` y convierte una sola vez la configuración legacy existente:

```text
access_profiles.can_*
users.title
```

hacia datos IAM canónicos:

```text
Position
Role
RolePermission
PositionRole
UserPosition
```

Esta lectura de legacy es exclusivamente una migración de compatibilidad. Después del upgrade, runtime no debe consultar `can_approve`, `BOARD_CODES` ni nombres de Cargo para resolver permisos.

## Resultado esperado para el caso de aprobación

Si Tesorero y Vicepresidente tienen un Cargo asociado a un Rol que contiene:

```text
requests:approve
```

ambos son aprobadores efectivos.

Si uno de ellos crea una solicitud MULTI_QUOTE, el solicitante se excluye de su propia ronda y el otro continúa siendo elegible.

## Fuera de alcance

- permisos DENY explícitos;
- jerarquía Cargo padre/hijo;
- grupos anidados;
- scopes multi-tenant;
- autorización por nombre de cargo;
- mantener la pantalla legacy `AccessProfile` como fuente autoritativa.
