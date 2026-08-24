# Plan 011 — Accesos y runtime

Frontend:

- `iam-admin.jsx`: staging, Guardar cambios, Rol por Grupo, Roles globales y distinción entre Permisos propios/heredados.
- `auth-route-guard.js`: rutas privadas.
- `request-governor.js`: deduplicación/caché corta.
- `access-navigation-bridge.js`: navegación del shell durante transición.
- `config-readonly.js`: experiencia de lectura sin polling.

Backend:

- `iam_users.py`: PATCH transaccional de Roles agrupados y globales.
- `iam_group_assignments.py`: Permisos y Roles opcionales del Grupo, preservando `RolePermission`, y reconstrucción de miembros derivados.
- `iam_service.py`: unión de Permisos propios del Rol y heredados del Grupo activo, sin autoridad desde `GroupMember`.
- `iam_access_policy.py`: rechazo de bypass.
- Alembic 0004: permite Roles globales sin relajar un Rol por Usuario/Grupo.
- Alembic 0009: agrega `group_permissions` como grants aditivos sin backfill de grants ni denegaciones y normaliza las instantáneas temporales abiertas.

Validar Network: una pantalla quieta no debe emitir llamadas por segundo.
