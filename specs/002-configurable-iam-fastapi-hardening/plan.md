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

`app/services/iam_service.py` resuelve permisos persistidos desde tres fuentes para usuarios operativos:

1. `user_permissions`;
2. `user_role_assignments → role_permissions`;
3. `group_members → group_roles → role_permissions`.

La cuenta técnica aplica política por ambiente:

```text
ENVIRONMENT=production
→ {requests:read, config:manage}

ENVIRONMENT!=production
→ todos los permisos atómicos activos
```

`require_permission(code)` consulta el servicio IAM. No existe bypass por `UserRole.ADMIN`.

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

- creación → `request_actions.py` / `requests:create`;
- corrección/reenvío → `revision_actions.py` / `requests:create`;
- votación → `quotation_actions.py` / `requests:approve`;
- cierre/factura → `financial_actions.py` / `requests:close`;
- documentos → create/read según operación.

La población de aprobadores se resuelve con `users_with_permission('requests:approve')`.

Las invitaciones de votación almacenadas representan el snapshot de participantes de la ronda actual.

### Invariant posterior de correcciones

La Feature 003 añadió posteriormente:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

`revision_actions.py` rechaza un cambio de tipo con 409 y reinicia una ronda MULTI_QUOTE conservando evidencia. Ver `specs/003-request-correction-invariants/`. La Constitución vigente es 2.3.1.

## Seguridad de cuenta técnica

`system_accounts` identifica cuentas técnicas independientemente del enum legacy.

- Producción: la política IAM filtra permisos financieros accidentales.
- No producción: la política concede todos los permisos atómicos activos para pruebas end-to-end.

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
- timezone;
- ambiente funcional.

Distingue:

- `is_production_environment`: política funcional de producción;
- `is_production`: validaciones fuertes de producción/runtime alojado.

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
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

`scripts` es un paquete Python explícito y el bootstrap se ejecuta como módulo desde `/app`.

Esto mantiene la migración fuera del ciclo de vida FastAPI y funciona en planes de Render sin pre-deploy separado. Para despliegues con múltiples réplicas se debe mover la migración a una etapa única de release/pre-deploy para evitar carreras.

`tests/test_migrations.py` debe fallar si existe más de un head o se rompe la cadena `0000 → 0001 → 0002`.

La topología del script no sustituye una ejecución real: antes de producción se requiere snapshot y smoke test contra PostgreSQL/Neon de preview.

### Portabilidad Windows → Linux de scripts de arranque

Los entrypoints del contenedor son shell scripts Linux. El repositorio debe forzar `*.sh` a LF mediante `.gitattributes` y la imagen backend debe normalizar de forma defensiva cualquier `\r` antes de ejecutar `start.sh`.

El frontend local debe esperar a que el backend pase `/api/health` antes de arrancar Nginx. Así, un error de migración/startup se presenta como fallo del backend y no como un secundario `host not found in upstream "backend"`.

El CI debe cargar la imagen backend y validar tanto el entrypoint shell como `import scripts.bootstrap_admin` con una `DATABASE_URL` de prueba.

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

La Feature 003 añade temporalmente `frontend/vite.config.js` para hidratar correcciones MULTI_QUOTE mientras `ExpenseForm` continúe dentro del monolito. Ese transform no es arquitectura objetivo y debe retirarse con la modularización del formulario.

## Testing

`tests/test_iam_api.py` utiliza:

- `FastAPI TestClient`;
- DB SQLite aislada con `StaticPool`;
- dependency override de `get_db`;
- tokens reales del backend.

Matriz IAM mínima:

- system admin no-prod: todos los permisos activos;
- system admin prod: config/read;
- system admin prod: close denied incluso con permiso accidental;
- usuario sin config: IAM admin 403;
- Grupo→Rol cambia permisos inmediatamente;
- permiso directo es aditivo;
- rol system-managed no editable.

`tests/test_multi_quote_revision.py` cubre la semántica posterior de correcciones MULTI_QUOTE.

`tests/test_migrations.py` valida la topología Alembic sin afirmar que reemplaza un smoke test de PostgreSQL real.

`tests/test_container_portability.py` protege la política LF/healthcheck, mientras el job Docker de CI valida el entrypoint y la importabilidad real del bootstrap dentro de la imagen.

## Despliegue

1. Crear backup/snapshot/branch de Neon.
2. Construir backend actualizado.
3. En preview, ejecutar `alembic upgrade head` y comprobar `0000 → 0001 → 0002`.
4. Ejecutar `python -m scripts.bootstrap_admin` desde la raíz del backend.
5. Iniciar FastAPI.
6. Verificar `/api/health`.
7. Login administrador técnico.
8. En producción verificar permisos efectivos: solo `config:manage`, `requests:read`.
9. En preview/test verificar permisos técnicos completos si `ENVIRONMENT != production`.
10. Configurar grupos/roles requeridos desde UI.
11. Validar creación/aprobación/cierre con usuarios separados y validar correcciones SIMPLE/MULTI_QUOTE.
12. Solo después repetir el procedimiento en producción.

## Rollback

No depender únicamente de `alembic downgrade` para recuperar datos. Antes de migración productiva mantener snapshot/branch Neon. El baseline 0000 tiene downgrade deliberadamente no destructivo porque puede haberse aplicado sobre tablas preexistentes que Alembic no creó. Si la migración falla después de escrituras de negocio, restaurar snapshot y versión previa del servicio.
