# Plan 006 — Acceso por Grupo

## Backend

- validar Roles activos/no técnicos;
- resolver el Grupo de cada Rol;
- rechazar dos Roles del mismo Grupo;
- reemplazar `UserRoleAssignment` y `GroupMember` atómicamente;
- bloquear permisos directos, Cargo→Rol y membresía independiente;
- mantener Cargo fuera de `effective_permission_codes()`.

## Base de datos

- `20260820_0002_group_scoped_roles`: Rol único por Grupo y guard usuario/grupo;
- `20260821_0003_single_user_position`: un Cargo por Usuario.

## Frontend

- `iam-admin.jsx`: selectores de Rol por Grupo;
- miembros de Grupo solo lectura;
- Guardar cambios explícito.
