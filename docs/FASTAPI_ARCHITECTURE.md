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

### Restablecimiento de contraseña

`POST /api/users/{user_id}/regenerate-password` conserva la ruta administrativa
compatible, pero requiere `config:manage` efectivo y rechaza destinatarios
inactivos o pertenecientes a `system_accounts`. Incrementa
`password_reset_version` y envía un token de propósito exclusivo sin cambiar la
contraseña, `must_change_password` ni `session_version`; si falla el correo, la
transacción revierte.

`POST /api/auth/reset-password` es público y acepta únicamente ese propósito de
token. Valida expiración y `password_reset_version`; al consumir aplica Argon2,
establece `must_change_password=false` e incrementa `session_version` y
`password_reset_version`. No emite un JWT de sesión. La emisión usa el rate limit
sensible por usuario autenticado; el consumo usa una cuota pública dedicada de
5 intentos por 15 minutos por IP y proceso, limpia claves inactivas por TTL y
solo confía en el último `X-Forwarded-For` cuando el peer directo es
privado/loopback. Cambiar correo o estado invalida tokens previos. Tras el commit
se intenta una confirmación best-effort sin secretos; su fallo no revierte el
restablecimiento.

Ninguna respuesta ni evento de auditoría almacena o devuelve token, contraseña o
hash. Los logs ordinarios tampoco los incluyen; `EMAIL_MODE=console` es la
excepción local explícita porque imprime el cuerpo del correo y sus logs se
tratan como sensibles.

## IAM

Autoridad actual:

```text
UserRoleAssignment → Role → RolePermission → Permission
                          └→ GroupRole → UserGroup → GroupPermission → Permission
```

`effective_permission_codes()` suma `RolePermission` y `GroupPermission` para Roles agrupados activos dentro de Grupos activos. No usa Cargo, permisos directos a Usuario ni `GroupMember` como fuente de autoridad; `config:manage` se elimina para Usuarios ordinarios y solo llega por la política `SystemAccount`.

`roles.max_users` limita opcionalmente las asignaciones activas. Las rutas
canónicas y compatibles bloquean el Rol antes de contar, rechazan overflow con
409 y revalidan al reactivar un Usuario. Los inactivos conservan su asignación y
no consumen cupo.

`iam_access_policy.py` se registra antes del router IAM de compatibilidad para bloquear rutas que contradigan el modelo actual.

## Middlewares

- CORS explícito;
- rate limiting por sujeto autenticado;
- headers API `no-store`, `nosniff`, `no-referrer`, `DENY`.

## Routers relevantes

```text
/api/auth
/api/auth/reset-password
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

`DATABASE_SCHEMA` se aplica mediante metadata schema-qualified. Los tipos `Enum` ORM usan `inherit_schema=True` y cualquier SQL crudo usa nombres completos derivados de tablas SQLAlchemy; no se depende de `search_path`. Alembic corre fuera de lifespan y usa `version_table_schema`.

## Tests

Los contratos críticos deben tener pruebas HTTP/modelo para:

- autorización;
- cardinalidades IAM;
- cupo de Rol en asignación, reactivación y reducción del máximo;
- workflow/capacidades;
- schema PostgreSQL;
- frontend contracts cuando haya bridges transitorios.
- emisión/consumo de restablecimiento: autorización, expiración, uso único,
  reemplazo, rollback, rate limits, Argon2, revocación y ausencia de auto-login.

La validación Docker/PostgreSQL es obligatoria para rutas que usan SQL específico del dialecto; SQLite no detecta referencias sin schema ni casts ENUM sin calificar.
