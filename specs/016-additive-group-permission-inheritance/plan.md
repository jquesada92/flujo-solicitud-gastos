# Plan 016 — Herencia aditiva de Permisos por Grupo

## Persistencia

- agregar `GroupPermission` con unicidad Grupo/Permiso;
- crear Alembic `20260824_0009_group_permission_inheritance` sobre `20260821_0008`;
- dejar la tabla vacía al migrar y conservar intacta `role_permissions`.

## Backend

- aceptar y devolver `permission_codes` en payloads de Grupo;
- reemplazar solo `GroupPermission` al guardar Permisos del Grupo;
- resolver Roles agrupados como `RolePermission ∪ GroupPermission`;
- excluir `GroupMember` de todas las consultas de autorización;
- mantener filtros de actividad y `config:manage` system-only;
- incluir la herencia en `users_with_permission()` y distinguirla en `permission_sources()`.

## Frontend

- stagear Permisos y Roles del Grupo hasta **Guardar cambios**;
- mostrar Permisos propios e heredados por separado en la ficha del Rol;
- comunicar que quitar el Rol del Grupo conserva sus Permisos propios;
- no presentar controles `DENY` ni membresía como grant.

## Validación

- cubrir Rol solo heredado, Rol con grants adicionales y duplicados;
- cubrir Grupo/Rol/Permiso inactivo y `GroupMember` aislado;
- cubrir edición y desvinculación sin pérdida de `RolePermission`;
- cubrir `users_with_permission()`, fuentes explicables y protección de `config:manage`;
- validar migración, rollback, suite backend y build frontend.
