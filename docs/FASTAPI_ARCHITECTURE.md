# Arquitectura FastAPI

## Principios

- FastAPI autoriza y valida transiciones.
- SQLAlchemy models, Pydantic schemas y servicios se separan de routers.
- operaciones síncronas de DB/filesystem usan routes `def` para ejecutarse en threadpool.
- lifespan solo valida Settings; migraciones/bootstrap son pasos de despliegue.

## Capas

```text
app/application.py       ensamblaje/middleware/routers
app/api/                 HTTP y dependencias
app/schemas/             contratos Pydantic
app/models/              persistencia SQLAlchemy
app/services/            lógica reutilizable
app/core/                config, DB, security, rate limit
```

## Seguridad

`current_user()` valida token, `session_version`, estado activo, inactividad y contraseña temporal.

`require_permission()` resuelve permisos desde `iam_service.py`. Para Configuración, `config:read` puede satisfacer lecturas GET/HEAD protegidas históricamente por `config:manage`; las mutaciones siguen requiriendo escritura.

`require_system_account()` verifica `system_accounts`.

## IAM

Autoridad actual:

```text
UserRoleAssignment → GroupRole → UserGroup
RolePermission     → Permission
```

`effective_permission_codes()` no usa Cargo ni permisos directos.

`iam_access_policy.py` se registra antes del router IAM de compatibilidad para bloquear rutas que contradigan el modelo actual.

## Middlewares

- CORS explícito;
- rate limiting por sujeto autenticado;
- headers API `no-store`, `nosniff`, `no-referrer`, `DENY`.

## Routers relevantes

```text
/api/auth
/api/expenses
/api/approvals
/api/areas
/api/iam
/api/organization
/api/audit
/api/rules
```

Los routers canónicos de acciones se registran antes de rutas legacy de compatibilidad.

## Persistencia

`DATABASE_SCHEMA` se aplica mediante metadata schema-qualified. Alembic corre fuera de lifespan y usa `version_table_schema`.

## Tests

Los contratos críticos deben tener pruebas HTTP/modelo para:

- autorización;
- cardinalidades IAM;
- workflow/capacidades;
- schema PostgreSQL;
- frontend contracts cuando haya bridges transitorios.
