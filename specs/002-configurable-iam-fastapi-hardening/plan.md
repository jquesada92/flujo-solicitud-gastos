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

Para usuarios operativos, `app/services/iam_service.py` resuelve permisos desde:

1. `user_permissions`;
2. `user_role_assignments → role_permissions`;
3. `group_members → group_roles → role_permissions`.

La cuenta técnica se detecta exclusivamente mediante `system_accounts` y aplica una política por ambiente.

### Política de producción

Si `Settings.is_production_environment == True`, equivalente a `ENVIRONMENT=production`:

```text
TECHNICAL_ADMIN effective permissions =
active_permissions ∩ {requests:read, config:manage}
```

Esta política ignora asignaciones financieras accidentales y excluye a la cuenta técnica de poblaciones de aprobación/votación para permisos financieros.

### Política no productiva

Si `ENVIRONMENT != production`:

```text
TECHNICAL_ADMIN effective permissions = all active product permissions
```

Esto permite usar una sola cuenta técnica para probar creación, consulta, aprobación, votación, cierre y configuración.

`users_with_permission()` incorpora la misma política: la cuenta técnica puede formar parte de poblaciones funcionales fuera de producción cuando el permiso está activo.

`require_permission(code)` consulta siempre este servicio IAM. No existe bypass por `UserRole.ADMIN`, email, cargo o ID.

## Settings

`app/core/config.py` distingue dos conceptos:

- `is_production_environment`: únicamente `ENVIRONMENT=production`; controla la segregación funcional de la cuenta técnica.
- `is_production`: producción o runtime alojado como Render; conserva validaciones fuertes de secretos/CORS.

Esto evita que un preview alojado en Render pierda capacidad de prueba solo por estar hospedado, sin relajar requisitos de secretos.

## Contrato de usuario autenticado

`app/core/security.py` aplica `apply_effective_permissions_to_user()` en cada vista autenticada relevante.

El usuario actual expone:

```text
permission_codes
can_request      ← requests:create
can_approve      ← requests:approve
can_view         ← requests:read
can_configure    ← config:manage
can_close        ← requests:close
```

`permission_codes` es el contrato canónico para frontend. Los `can_*` son compatibilidad temporal con `main.jsx`.

El login aplica esta decoración antes de serializar `UserOut`, de modo que el primer render del frontend ya refleja el ambiente actual.

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

En producción la cuenta técnica no entra en esa población. Fuera de producción sí puede entrar para pruebas, salvo exclusiones propias del flujo como ser el mismo solicitante.

Las invitaciones de votación almacenadas representan el snapshot de participantes de la ronda actual.

## Seguridad de cuenta técnica

`system_accounts` identifica cuentas técnicas independientemente del enum legacy. El bootstrap crea/asocia la cuenta, pero no necesita otorgar físicamente todos los permisos en no-producción: la política ambiental del servicio IAM calcula el acceso efectivo a partir del catálogo activo.

Esto evita contaminar datos persistidos de roles con privilegios de prueba y garantiza que el mismo dataset pase a segregación estricta al ejecutar con `ENVIRONMENT=production`.

## Password hashing

- nuevo: `pwdlib.PasswordHash.recommended()` → Argon2;
- legacy: PBKDF2 se verifica temporalmente;
- login correcto PBKDF2 genera y persiste hash Argon2;
- cambio de contraseña siempre genera Argon2.

## Migraciones y startup

Alembic es la herramienta canónica. La cadena debe permanecer lineal:

```text
20260817_0000 application baseline
        ↓
20260817_0001 IAM foundation
        ↓
20260817_0002 system accounts
```

`FastAPI.lifespan` no crea tablas, no ejecuta ALTER TABLE y no hace backfills.

Docker ejecuta:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

`scripts` es un paquete Python explícito y el bootstrap se ejecuta como módulo desde `/app`.

## Portabilidad Windows → Linux

- `.gitattributes` fuerza `*.sh` a LF.
- El Dockerfile normaliza defensivamente CRLF.
- Docker Compose espera `/api/health` antes de iniciar Nginx.
- CI carga la imagen backend y valida el entrypoint y `import scripts.bootstrap_admin`.

## Sync / async

SQLAlchemy actual es síncrono. Las rutas que ejecutan SQLAlchemy/filesystem bloqueante se declaran con `def`, permitiendo que FastAPI las ejecute en threadpool.

No se migra a Async SQLAlchemy en este PR.

## Modelos y routers

Los modelos SQLAlchemy viven en `models/`; contratos reutilizables en `schemas/`; lógica compartida en `services/`.

`app/main.py` queda como alias de compatibilidad a `app.application`.

## Frontend

La consola `Configuración → Accesos` consume `/api/iam/*`.

El backend ya entrega `permission_codes` y `can_close` además de los aliases legacy. La meta de frontend es migrar toda visibilidad de acciones a `permission_codes` y retirar el bypass visual `user.role === "ADMIN"` y cualquier `canClose={true}` hardcodeado durante la modularización del monolito.

Mientras esa deuda visual exista, el backend continúa siendo la autoridad y niega las operaciones de producción no permitidas.

## Testing

`tests/test_iam_api.py` usa `FastAPI TestClient`, SQLite aislada y dependency override de `get_db()`.

Matriz obligatoria:

- no-producción: cuenta técnica obtiene todos los permisos activos;
- no-producción: login devuelve `permission_codes` y aliases habilitados, incluido `can_close`;
- no-producción: cuenta técnica puede aparecer en población `requests:approve`;
- producción: cuenta técnica obtiene solo config/read;
- producción: `requests:close` asignado accidentalmente sigue en DENY;
- producción: endpoint de cierre devuelve 403 para cuenta técnica;
- producción: cuenta técnica no aparece en población `requests:approve`;
- usuario sin config: IAM admin 403;
- Grupo→Rol cambia permisos inmediatamente;
- permiso directo es aditivo;
- rol system-managed no editable.

`tests/test_migrations.py` valida topología Alembic.

`tests/test_container_portability.py` protege política LF/healthcheck y el job Docker valida la imagen real.

## Despliegue por ambiente

### Local / dev / test / staging / preview

1. Definir `ENVIRONMENT` con cualquier valor distinto de `production`.
2. Ejecutar migraciones + bootstrap.
3. Iniciar FastAPI.
4. Login con cuenta técnica.
5. Verificar que `/api/iam/me/permissions` incluya todos los permisos activos.
6. Ejecutar pruebas end-to-end con la misma cuenta cuando sea útil.

### Producción

1. Crear backup/snapshot/branch de Neon.
2. Definir explícitamente `ENVIRONMENT=production`.
3. Ejecutar `alembic upgrade head`.
4. Ejecutar `python -m scripts.bootstrap_admin`.
5. Iniciar FastAPI y verificar `/api/health`.
6. Login administrador técnico.
7. Verificar permisos efectivos exactamente `config:manage` + `requests:read`.
8. Verificar que crear/aprobar/cerrar devuelvan 403 para la cuenta técnica.
9. Validar los flujos financieros con usuarios operativos separados.

`render.yaml` productivo declara `ENVIRONMENT=production` explícitamente.

## Rollback

No depender únicamente de `alembic downgrade` para recuperar datos. Antes de migración productiva mantener snapshot/branch Neon. Si la migración falla después de escrituras de negocio, restaurar snapshot y versión previa del servicio.
