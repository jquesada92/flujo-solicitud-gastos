# Aceptación 016

- [x] un Grupo puede guardar cero o más Permisos heredables.
- [x] un Rol agrupado sin Permisos propios hereda todos los Permisos activos del Grupo activo.
- [x] Grupo `{read, approve}` y Rol `{create, approve}` producen `{read, approve, create}` sin duplicados.
- [x] un Permiso ausente en el Rol se hereda; no existe `DENY`.
- [x] vaciar o cambiar los Permisos del Grupo conserva `RolePermission`.
- [x] desvincular un Rol elimina solo la herencia y conserva Permisos propios y asignaciones de Usuario.
- [x] vincularlo a otro Grupo suma la nueva herencia sin reemplazar Permisos propios.
- [x] `GroupMember` sin `UserRoleAssignment` agrupado no concede acceso.
- [x] Rol, Grupo o Permiso inactivo no concede por esa ruta.
- [x] `users_with_permission()` incluye Usuarios autorizados por herencia.
- [x] `permission_sources()` distingue Permiso propio y heredado.
- [x] `RoleOut.permission_codes` contiene solo grants propios y `GroupOut.permission_codes` solo grants del Grupo.
- [x] un código desconocido o inactivo produce 422 sin persistencia parcial.
- [x] la UI guarda Permisos y Roles del Grupo de forma staged y atómica.
- [x] la UI identifica la herencia aunque el checkbox propio del Rol esté desmarcado.
- [x] `config:manage` no es efectivo para Usuarios ordinarios desde Rol ni Grupo.
- [x] Alembic 0009 crea `group_permissions` vacía y no cambia accesos existentes.
