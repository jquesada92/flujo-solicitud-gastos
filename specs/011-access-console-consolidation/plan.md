# Plan 011 — Accesos y runtime

Frontend:

- `iam-admin.jsx`: staging, Guardar cambios, Rol por Grupo, Roles globales, distinción entre Permisos propios/heredados, cupo opcional de Usuarios activos y listado de todos los Roles persistidos debajo del correo de cada Usuario.
- `iam-admin.jsx`: acción confirmada de restablecimiento para Usuarios activos no
  técnicos, separada del borrador IAM y con estado de envío.
- `iam-responsive.css`: layout apilable, wrap y protección contra overflow desde 320 px.
- `auth-route-guard.js`: rutas privadas.
- `request-governor.js`: deduplicación/caché corta.
- `access-navigation-bridge.js`: navegación del shell durante transición.
- `config-readonly.js`: experiencia de lectura sin polling.

Backend:

- `iam_users.py`: PATCH transaccional de Roles agrupados y globales.
- `users.py`: emisión compatible del enlace de restablecimiento bajo protección
  canónica de `config:manage` y `system_accounts`.
- `auth.py`: consumo público del token sin crear sesión.
- `iam_group_assignments.py`: Permisos y Roles opcionales del Grupo, preservando `RolePermission`, y reconstrucción de miembros derivados.
- `iam_service.py`: unión de Permisos propios del Rol y heredados del Grupo activo, sin autoridad desde `GroupMember`.
- `iam_access_policy.py`: rechazo de bypass.
- Alembic 0004: permite Roles globales sin relajar un Rol por Usuario/Grupo.
- Alembic 0009: agrega `group_permissions` como grants aditivos sin backfill de grants ni denegaciones y normaliza las instantáneas temporales abiertas.

Validar Network: una pantalla quieta no debe emitir llamadas por segundo.

Validar que cada click confirmado emite como máximo una solicitud, que un error
no altera el borrador IAM y que el éxito no expone el token.

Pendiente bloqueante: restaurar en `UsersPanel` un selector independiente por Grupo y multiselección de Roles globales, preservar todos los `role_ids` no editados y sustituir las pruebas estáticas que hoy fijan un único Rol total.
