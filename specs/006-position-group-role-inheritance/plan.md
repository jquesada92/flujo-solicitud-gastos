# Plan técnico — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución vigente:** 2.9.0

## Modelo persistente

```text
position_roles
- id
- position_id FK positions
- role_id FK roles
- UNIQUE(position_id, role_id)
```

Modelo IAM:

```text
UserPosition → Position → PositionRole → Role → RolePermission → Permission
GroupMember  → Group    → GroupRole    → Role → RolePermission → Permission
UserRoleAssignment      → Role         → RolePermission → Permission
UserPermission                                      → Permission
```

## Resolución efectiva

`effective_permission_codes()` combina:

- baseline `requests:read`;
- permiso directo;
- Rol directo;
- Grupo→Rol;
- Cargo→Rol;
- política `system_accounts`;
- exclusión de `config:manage` para usuarios ordinarios.

`config:read` y `areas:manage` sí pueden llegar por Cargo/Grupo/Rol/directo.

## Población de workflow

`users_with_permission()` reconoce la misma herencia por Cargo y Grupo y respeta exclusiones de workflow/política productiva.

## Fuentes visibles

`permission_sources()` explica, entre otras:

```text
Cargo <position.name> → <role.name>
Grupo <group.name> → <role.name>
```

## API

`position_access.py` mantiene:

```text
GET    /api/iam/positions
PUT    /api/iam/positions/{position_id}/roles/{role_id}
DELETE /api/iam/positions/{position_id}/roles/{role_id}
```

Mutaciones IAM requieren administración técnica y rechazan Roles técnicos no asignables.

## UI vigente

La consola canónica es **Configuración → Accesos**:

- **Cargos** → Roles heredados;
- **Grupos** → Roles + Miembros;
- **Usuarios** → Cargos/Grupos/Roles/permisos directos;
- permisos efectivos → fuentes de herencia.

Usuarios es una pestaña interna de Accesos, no una pantalla independiente del menú.

## Migración 0004

`20260818_0004_position_role_inheritance.py`:

1. crea `position_roles`;
2. promueve configuración legacy a Cargos/Roles canónicos;
3. crea/reutiliza Roles equivalentes;
4. traduce flags legacy a permisos atómicos;
5. crea `UserPosition` cuando corresponda;
6. excluye cuentas técnicas de asignaciones organizacionales migradas.

## Evolución posterior

Cadena actual continúa:

```text
0004 → 0005 → 0006 → 0007 → 0008
```

- `0006`: `areas:manage`;
- `0007`: `config:read`;
- `0008`: `expense_area` / `expense_category` físicos.

## Compatibilidad

`AccessProfile`, `users.title`, `can_*` y `BOARD_CODES` pueden permanecer temporalmente, pero no participan en autorización runtime.

## Pruebas

Mantener pruebas de:

- Cargo→Rol→Permiso;
- Grupo + Cargo simultáneos;
- fuente visible;
- Cargo/Role inactivo;
- `users_with_permission()`;
- política de cuenta técnica;
- integración de asignaciones dentro de Accesos.

Gates finales del proyecto:

```text
alembic heads
alembic current
python -m unittest discover -s tests -v
npm run build
```

## Despliegue

Verificar Cargos/Roles heredados desde **Configuración → Accesos → Cargos** y permisos efectivos desde **Accesos → Usuarios**.
