# Plan 011 — Accesos y runtime

Frontend:

- `iam-admin.jsx`: staging, Guardar cambios y Rol por Grupo.
- `auth-route-guard.js`: rutas privadas.
- `request-governor.js`: deduplicación/caché corta.
- `access-navigation-bridge.js`: navegación del shell durante transición.
- `config-readonly.js`: experiencia de lectura sin polling.

Backend:

- `iam_users.py`: PATCH transaccional de acceso.
- `iam_group_assignments.py`: Roles del Grupo.
- `iam_access_policy.py`: rechazo de bypass.

Validar Network: una pantalla quieta no debe emitir llamadas por segundo.
