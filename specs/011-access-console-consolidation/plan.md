# Plan 011 — Accesos y runtime

Frontend:

- `iam-admin.jsx`: staging, Guardar cambios, Rol por Grupo y Roles globales.
- `auth-route-guard.js`: rutas privadas.
- `request-governor.js`: deduplicación/caché corta.
- `access-navigation-bridge.js`: navegación del shell durante transición.
- `config-readonly.js`: experiencia de lectura sin polling.

Backend:

- `iam_users.py`: PATCH transaccional de Roles agrupados y globales.
- `iam_group_assignments.py`: Roles opcionales del Grupo y reconstrucción de miembros derivados.
- `iam_service.py`: permisos desde Roles globales o agrupados activos.
- `iam_access_policy.py`: rechazo de bypass.
- Alembic 0004: permite Roles globales sin relajar un Rol por Usuario/Grupo.

Validar Network: una pantalla quieta no debe emitir llamadas por segundo.
