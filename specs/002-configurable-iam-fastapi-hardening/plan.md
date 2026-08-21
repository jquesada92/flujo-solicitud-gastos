# Plan 002 — IAM y FastAPI

## Componentes

- `app/services/iam_service.py`: permisos efectivos.
- `app/core/security.py`: sesión y guards.
- `app/core/rate_limit.py`: cuotas de requests autenticados.
- `app/api/iam_users.py`: asignaciones canónicas.
- `app/api/iam_access_policy.py`: bloqueo de bypass legacy.
- `app/application.py`: orden de routers y middlewares.

## Mantenimiento

1. Cualquier permiso nuevo se persiste y se incorpora a roles, no se hardcodea por nombre de actor.
2. Mantener `config:manage` protegido para cuenta técnica.
3. Mantener `config:read` como excepción solo de lectura.
4. Añadir tests HTTP para cada mutación protegida.
5. No ejecutar migraciones desde lifespan.
6. Mantener middleware de rate limit y headers sensibles al agregar rutas API.
