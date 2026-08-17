# Plan técnico — IAM configurable y hardening FastAPI

## Arquitectura objetivo

```text
Frontend React
  ├─ UI operacional legacy (transición)
  └─ IAM Console
       ↓ HTTPS
FastAPI
  ├─ api/                 HTTP y dependencias
  ├─ schemas/             contratos Pydantic
  ├─ services/            lógica reutilizable
  ├─ models/              SQLAlchemy
  └─ core/                Settings, DB, security, rate limit
       ↓
PostgreSQL / Neon
```

## Modelo IAM

Tablas canónicas:

- `permissions`
- `roles`
- `role_permissions`
- `user_groups`
- `group_members`
- `group_roles`
- `user_role_assignments`
- `user_permissions`
- `positions`
- `user_positions`
- `system_accounts`

`users.role`, `users.title` y `users.can_*` son compatibilidad temporal; no autoridad.

## Resolución de permisos

`app/services/iam_service.py` resuelve permisos desde tres fuentes:

1. `user_permissions`;
2. `user_role_assignments → role_permissions`;
3. `group_members → group_roles → role_permissions`.

La cuenta técnica aplica una intersección defensiva con:

```text
{requests:read, config:manage}
```

`require_permission(code)` consulta el servicio IAM. No existe bypass ADMIN.

## API IAM

Base `/api/iam`:

- `GET /me/permissions`
- catálogo `GET /permissions`
- CRUD funcional de roles y grupos;
- asignación grupo↔rol;
- asignación grupo↔usuario;
- roles/permisos directos de usuario;
- permisos efectivos y sus fuentes;
- cargos/posiciones.

Base `/api/iam/users`:

- listado neutral de usuarios;
- creación con grupos/roles/permisos/cargos opcionales;
- actualización de atributos y asignaciones;
- permisos efectivos y fuentes de herencia por usuario.

## Rutas financieras canónicas

Las rutas registradas antes del router legacy garantizan:

- creación → `requests:create`;
- votación → `requests:approve`;
- cierre/factura → `requests:close`;
- documentos → create/read según operación.

La población de aprobadores se resuelve con `users_with_permission('requests:approve')`.

Las invitaciones de votación almacenadas representan el snapshot de participantes de la ronda actual.

## Seguridad de cuenta técnica

`system_accounts` identifica cuentas técnicas independientemente del enum legacy. El bootstrap crea/asocia la cuenta y la política IAM filtra cualquier permiso financiero accidental.

## Password hashing

- nuevo: `pwdlib.PasswordHash.recommended()` → Argon2;
- legacy: PBKDF2 se verifica temporalmente;
- login correcto PBKDF2 genera y persiste hash Argon2;
- cambio de contraseña siempre genera Argon2.

## Settings

`app/core/config.py` centraliza:

- DB;
- JWT/sesión;
- CORS;
- rate limits;
- documentos;
- correo/Brevo/SMTP;
- bootstrap admin;
- timezone.

Producción valida secretos, CORS y credenciales necesarias.

## Migraciones y startup

Alembic es la herramienta canónica. La cadena debe permanecer lineal:

```text
20260817_0000 application baseline
        ↓
20260817_0001 IAM foundation
        ↓
20260817_0002 system accounts
```

`0000` define el baseline property-free requerido para instalar el producto sobre una base PostgreSQL limpia y utiliza inspección para conservar tablas que ya existen en la base productiva actual.

`FastAPI.lifespan` no crea tablas, no ejecuta ALTER TABLE y no hace backfills.

Docker ejecuta:

```text
alembic upgrade head
python scripts/bootstrap_admin.py
uvicorn app.application:app
```

Esto mantiene la migración fuera del ciclo de vida FastAPI y funciona en planes de Render sin pre-deploy separado. Para despliegues con múltiples réplicas se debe mover la migración a una etapa única de release/pre-deploy para evitar carreras.

`tests/test_migrations.py` debe fallar si existe más de un head o se rompe la cadena `0000 → 0001 → 0002`.

La topología del script no sustituye una ejecución real: antes de producción se requiere snapshot y smoke test contra PostgreSQL/Neon de preview.

## Sync / async

SQLAlchemy actual es síncrono. Las nuevas rutas que ejecutan SQLAlchemy y filesystem bloqueante se declaran con `def`, permitiendo que FastAPI las ejecute en threadpool.

No se migra a Async SQLAlchemy en este PR.

## Modelos y routers

Los modelos `ExpenseCategoryCatalog` y `AreaCategoryLink` se movieron de `api/areas.py` a `models/classification.py`.

Nuevos contratos IAM y votación viven en `schemas/`.

`app/main.py` queda como alias de compatibilidad a `app.application`.

## Frontend

Se agrega módulo `iam-admin.jsx` separado del monolito legacy.

La consola se abre desde `Configuración → Accesos` y consume únicamente `/api/iam/*`.

El módulo permite:

- usuarios;
- grupos;
- roles;
- permisos;
- cargos;
- membresías/asignaciones;
- permisos efectivos.

`main.jsx` y `domain-normalization.js` siguen siendo deuda de modularización; no son autoridad de seguridad.

## Testing

`tests/test_iam_api.py` utiliza:

- `FastAPI TestClient`;
- DB SQLite aislada con `StaticPool`;
- dependency override de `get_db`;
- tokens reales del backend.

Matriz mínima:

- system admin: config/read;
- system admin: close denied incluso con permiso accidental;
- usuario sin config: IAM admin 403;
- Grupo→Rol cambia permisos inmediatamente;
- permiso directo es aditivo;
- rol system-managed no editable.

`tests/test_migrations.py` valida la topología Alembic sin afirmar que reemplaza un smoke test de PostgreSQL real.

## Despliegue

1. Crear backup/snapshot/branch de Neon.
2. Construir backend actualizado.
3. En preview, ejecutar `alembic upgrade head` y comprobar `0000 → 0001 → 0002`.
4. Ejecutar bootstrap técnico idempotente.
5. Iniciar FastAPI.
6. Verificar `/api/health`.
7. Login administrador técnico.
8. Verificar permisos efectivos: solo `config:manage`, `requests:read`.
9. Configurar grupos/roles requeridos desde UI.
10. Validar creación/aprobación/cierre con usuarios separados.
11. Solo después repetir el procedimiento en producción.

## Rollback

No depender únicamente de `alembic downgrade` para recuperar datos. Antes de migración productiva mantener snapshot/branch Neon. El baseline 0000 tiene downgrade deliberadamente no destructivo porque puede haberse aplicado sobre tablas preexistentes que Alembic no creó. Si la migración falla después de escrituras de negocio, restaurar snapshot y versión previa del servicio.
