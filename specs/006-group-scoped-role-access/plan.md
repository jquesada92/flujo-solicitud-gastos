# Plan 006 — Roles agrupados y globales

## Backend

- validar Roles activos/no técnicos para usuarios ordinarios;
- distinguir Rol global (sin `GroupRole`) de Rol agrupado;
- resolver cada Rol agrupado como `RolePermission ∪ GroupPermission` y cada Rol global solo desde `RolePermission`;
- para Roles agrupados, exigir Grupo activo y rechazar dos Roles del mismo Grupo;
- permitir cero o más Roles globales ordinarios por Usuario;
- reemplazar `UserRoleAssignment` y reconstruir `GroupMember` atómicamente;
- permitir mover Roles Global↔Grupo sin borrar asignaciones;
- conservar `RolePermission` al editar Permisos del Grupo o mover el Rol y retirar solo la herencia al desvincular;
- impedir que mover Roles a un Grupo genere dos Roles del mismo Grupo para un Usuario;
- bloquear permisos directos, Cargo→Rol y membresía independiente;
- mantener Cargo fuera de `effective_permission_codes()`;
- mantener `GroupMember` fuera de `effective_permission_codes()` y no implementar `DENY`;
- representar `system-administrator` como Rol global protegido sin sustituir `SystemAccount`.

## Base de datos

- `20260820_0002_group_scoped_roles`: un Rol no puede pertenecer a más de un Grupo y guard usuario/grupo;
- `20260821_0003_single_user_position`: un Cargo por Usuario;
- `20260821_0004_allow_global_roles`: el guard acepta Roles sin Grupo y mantiene el límite para Roles agrupados.
- `20260824_0009_group_permission_inheritance`: agrega `group_permissions` sin backfill de grants para preservar los accesos efectivos previos y normaliza las instantáneas temporales abiertas.

## Frontend

- `iam-admin.jsx`: selectores de Rol por Grupo;
- sección separada de Roles globales;
- Grupos pueden tener cero Roles;
- Permisos heredables se editan en la ficha del Grupo;
- la ficha del Rol conserva checkboxes de Permisos propios y muestra cuáles también hereda;
- quitar un Rol de un Grupo lo convierte en global;
- miembros de Grupo solo lectura;
- cuenta técnica muestra Rol global protegido;
- Guardar cambios explícito.
