# Plan técnico — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución:** 2.5.0

## Modelo persistente

Se agrega:

```text
position_roles
- id
- position_id FK positions
- role_id FK roles
- UNIQUE(position_id, role_id)
```

El modelo IAM queda:

```text
UserPosition → Position → PositionRole → Role → RolePermission → Permission
GroupMember  → Group    → GroupRole    → Role → RolePermission → Permission
UserRoleAssignment      → Role         → RolePermission → Permission
UserPermission                                      → Permission
```

## Resolución efectiva

`iam_service._unrestricted_permission_codes()` incorpora una cuarta fuente organizacional: `position_role_permissions`.

`effective_permission_codes()` conserva:

- baseline universal `requests:read`;
- política especial de `system_accounts`;
- unión de fuentes para usuarios operativos.

## Población de workflow

`users_with_permission()` agrega un `SELECT` para:

```text
UserPosition
→ Position(active)
→ PositionRole
→ Role(active)
→ RolePermission
→ Permission(active)
```

La unión SQL evita consultar usuario por usuario y mantiene el mismo contrato que la autorización individual.

Para permisos no admitidos por la política productiva de la cuenta técnica, se mantiene la exclusión de `system_accounts`.

## Fuentes de permisos

`permission_sources()` agrega:

```text
Cargo <position.name> → <role.name>
```

Esto permite distinguir claramente la herencia por Cargo de la herencia por Grupo.

## API

Se agrega `app/api/position_access.py`, registrado antes de `iam.py` genérico.

Rutas:

```text
GET    /api/iam/positions
PUT    /api/iam/positions/{position_id}/roles/{role_id}
DELETE /api/iam/positions/{position_id}/roles/{role_id}
```

El GET enriquecido devuelve `role_ids` junto con metadatos del Cargo.

Las mutaciones requieren `config:manage` y rechazan Roles técnicos `system_managed`.

## UI

`frontend/src/iam-admin.jsx`:

- `PositionsPanel` permite seleccionar un Cargo;
- muestra los Roles activos no técnicos;
- permite asociarlos/desasociarlos;
- Usuarios explica que el Cargo puede heredar Roles;
- Permisos efectivos muestra también las fuentes de herencia;
- Grupos conserva su flujo existente de Roles + Miembros.

## Migración 0004

`20260818_0004_position_role_inheritance.py`:

1. crea `position_roles`;
2. promueve `access_profiles` legacy a `positions` canónicos cuando corresponda;
3. crea/reutiliza un Rol migrado por perfil;
4. traduce `can_view`, `can_request`, `can_approve`, `can_configure` a permisos atómicos del Rol;
5. preserva la compatibilidad histórica de cierre de ADMINISTRADORA como dato migrado, no condición runtime;
6. crea `PositionRole`;
7. crea `UserPosition` para usuarios cuyo `users.title` coincidía con el perfil legacy;
8. excluye cuentas técnicas de la asignación organizacional migrada.

La migración es collision-safe cuando ya existen Cargos/Roles equivalentes.

## Compatibilidad y retiro de legacy

`AccessProfile`, `users.title`, `can_*` y `BOARD_CODES` pueden permanecer temporalmente físicamente, pero:

- no participan en runtime authorization;
- no participan en `users_with_permission()`;
- no deben ser la pantalla autoritativa para nuevos cambios de acceso.

La consola canónica es **Configuración → Accesos**.

## Pruebas

`test_position_role_inheritance.py` cubre:

- Cargo → Rol → `requests:approve`;
- fuente `Cargo Tesorero → Aprobador`;
- `users_with_permission('requests:approve')` incluye el usuario heredado por Cargo;
- Grupo y Cargo funcionan simultáneamente;
- Cargo inactivo deja de conceder permiso.

`test_migrations.py` exige:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

## Despliegue productivo

1. respaldo/snapshot de Neon;
2. merge a `main` con CI verde;
3. Render ejecuta `alembic upgrade head` antes de Uvicorn;
4. verificar que `alembic current` esté en `20260818_0004`;
5. abrir Configuración → Accesos → Cargos;
6. verificar Cargos migrados y Roles heredados;
7. comprobar Permisos efectivos de Tesorero/Vicepresidente;
8. crear/corregir una MULTI_QUOTE y verificar población de votantes.

No se requiere variable nueva de Vercel/Render para esta feature.
