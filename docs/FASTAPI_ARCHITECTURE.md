# Arquitectura FastAPI

## Referencia

La arquitectura sigue los patrones recomendados por la documentación oficial de FastAPI para aplicaciones grandes, dependencias, lifespan, seguridad y testing.

## Application factory

`app/application.py` crea la aplicación y registra middleware, routers, health endpoint y lifespan mínimo. `app/main.py` existe únicamente como alias de compatibilidad.

Las rutas canónicas se registran antes del router legacy. Entre ellas:

```text
request_actions.py   → creación
revision_actions.py  → corregir / reenviar
quotation_actions.py → votación
document_actions.py  → documentos
financial_actions.py → factura / cierre
```

Esto permite reemplazar gradualmente handlers legacy sin depender del orden accidental de rutas en `expenses.py`.

## Separación de responsabilidades

```text
api/       HTTP, parámetros, dependencias, códigos de respuesta
schemas/   contratos Pydantic
services/  reglas reutilizables y lógica de negocio
models/    persistencia SQLAlchemy
core/      configuración, DB, seguridad, rate limiting
```

## Dependencia de DB

`get_db()` usa `yield`/context manager para entregar una sesión por request y cerrarla siempre.

El backend actual usa SQLAlchemy síncrono. Las rutas canónicas que ejecutan SQLAlchemy o filesystem bloqueante se declaran con `def` para que FastAPI las ejecute en threadpool.

## Settings

`core/config.py` utiliza `pydantic-settings` y centraliza variables de entorno.

Se distinguen dos propiedades:

### `is_production_environment`

```text
ENVIRONMENT=production → True
cualquier otro valor   → False
```

Gobierna **comportamiento funcional sensible al ambiente**, actualmente la segregación de la cuenta `TECHNICAL_ADMIN`.

### `is_production`

Es verdadero cuando el ambiente es productivo o el runtime está alojado bajo condiciones que requieren endurecimiento, por ejemplo Render.

Gobierna validaciones como:

- secretos fuertes;
- CORS HTTPS explícito;
- credenciales requeridas.

Esta separación es deliberada: un preview alojado puede requerir secretos fuertes sin perder la capacidad de probar todo el flujo con la cuenta técnica.

## IAM y dependencias FastAPI

`require_permission(code)` consulta `iam_service.has_permission()`.

Para usuarios operativos, los permisos provienen de asignaciones persistidas de usuario/rol/grupo.

Para una cuenta registrada en `system_accounts`:

```text
ENVIRONMENT=production
→ permisos activos ∩ {requests:read, config:manage}

ENVIRONMENT!=production
→ todos los permisos activos del producto
```

No existe bypass por `UserRole.ADMIN`, email, cargo o ID.

`users_with_permission()` aplica la misma política a poblaciones de workflow. Por tanto:

- producción: cuenta técnica excluida de permisos financieros;
- no producción: puede participar en aprobación/votación para pruebas.

## Vista del usuario autenticado

`apply_effective_permissions_to_user()` calcula capacidades antes de serializar el usuario actual.

Contrato canónico:

```text
permission_codes
```

Aliases temporales:

```text
can_request
can_approve
can_view
can_configure
can_close
```

El login aplica esta decoración inmediatamente. `current_user()` la recalcula en cada request autenticado.

Esto permite que cambios IAM y el cambio de ambiente se reflejen sin confiar en columnas legacy persistidas.

## Invariant de correcciones

`revision_actions.py` protege una regla de negocio que no puede depender del estado React ni de la pestaña SIMPLE/MULTI_QUOTE seleccionada en el formulario de creación.

El tipo canónico se resuelve defensivamente como MULTI_QUOTE cuando existe cualquiera de estas señales durables:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options.length >= 2
```

El endpoint compara el payload contra ese tipo canónico. Un intento real de convertirlo devuelve `409`.

Para MULTI_QUOTE la ruta canónica:

- repara `request_type` legacy inconsistente;
- conserva los IDs de opciones y sus attachments;
- permite actualizar contenido de las opciones manteniendo su cantidad actual;
- cambia `flow_id`;
- limpia `QuotationVote` vigente;
- reemplaza `QuotationVotingInvitation`;
- conserva eventos históricos;
- resuelve nuevos participantes con `requests:approve`;
- vuelve a `QUOTATION_VOTING`.

Este invariant permanece aunque el frontend se reescriba.

## Lifespan

El lifespan solo valida/carga recursos de ciclo de vida. No ejecuta:

- `Base.metadata.create_all()`;
- `ALTER TABLE`;
- backfills;
- seeds organizacionales;
- migraciones destructivas.

## Alembic

Topología lineal:

```text
20260817_0000 application baseline
        ↓
20260817_0001 configurable IAM
        ↓
20260817_0002 protected system accounts
        ↓
20260817_0003 backfill MULTI_QUOTE request_type
```

`0003` es una reparación de datos histórica: cambia a `MULTI_QUOTE` filas con evidencia durable de múltiples cotizaciones que aún conservaban el default `SIMPLE`.

`tests/test_migrations.py` exige `0003` como único head.

El entrypoint Docker ejecuta:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

`scripts` es importable y el bootstrap se ejecuta como módulo desde `/app`.

## Portabilidad Docker Windows → Linux

- `.gitattributes` fuerza `*.sh text eol=lf`.
- `backend/Dockerfile` elimina `\r` defensivamente.
- Docker Compose espera `/api/health` antes de iniciar Nginx.
- CI valida `start.sh` real e `import scripts.bootstrap_admin` dentro de la imagen.

## Password hashing

`pwdlib.PasswordHash.recommended()` genera Argon2.

`verify_password_and_upgrade()` permite autenticar PBKDF2 legacy y reemplazarlo por Argon2 después de login exitoso.

## Response models

Autenticación usa `LoginResponse`/`TokenResponse`. `UserOut` incluye `permission_codes` y `can_close` para la transición hacia autorización visual por capacidades.

Al crear endpoints nuevos se debe declarar `response_model` salvo streaming/file o razón documentada.

## Testing

`tests/test_iam_api.py` usa `FastAPI TestClient` con SQLite aislada y cubre ambas políticas ambientales:

```text
no-prod → full technical-admin access
prod    → config/read only
```

También verifica población de aprobadores, 403 de cierre productivo y el contrato del login.

`tests/test_multi_quote_revision.py` verifica el invariant de correcciones con una solicitud MULTI_QUOTE real y con un registro legacy cuyo `request_type` quedó erróneamente en SIMPLE: preserva/repara tipo, conserva evidencia, reinicia ronda y rechaza conversión real a SIMPLE.

`tests/test_migrations.py` verifica topología Alembic hasta `0003`.

`tests/test_container_portability.py` verifica defensas de portabilidad local.

## Producción vs preview

`render.yaml` de producción declara explícitamente:

```env
ENVIRONMENT=production
```

Un servicio de preview/test debe usar otro valor si se desea acceso funcional completo con la cuenta técnica.

## Router/frontend legacy

`api/expenses.py`, `api/users.py` y `frontend/src/main.jsx` contienen partes del MVP anterior. Las rutas canónicas se registran antes que equivalentes legacy.

El frontend monolítico todavía contiene bypasses visuales como:

```text
user.role === "ADMIN"
canClose={true}
```

El backend no confía en esos valores, pero la deuda debe retirarse migrando la visibilidad de acciones a `permission_codes`.

### Transform temporal de correcciones

Mientras `ExpenseForm` siga dentro del monolito, `frontend/vite.config.js` aplica un plugin `legacy-revision-safety` antes del plugin React.

El plugin ahora protege explícitamente el aislamiento de estado:

- deriva el `requestType` inicial desde el draft/evidencia durable;
- al entrar en corrección, `ExpenseForm` recibe una `key` basada en la solicitud/flujo y se remonta;
- el estado de la pestaña de creación anterior no sobrevive al cambio de modo;
- restaura cotizaciones y metadata de attachments.

El transform utiliza reemplazos obligatorios y hace fallar `vite build` si los fragmentos legacy dejan de coincidir. Esto evita una degradación silenciosa, pero no sustituye la modularización. Al extraer `ExpenseForm` a un componente propio, el plugin debe eliminarse y la hidratación debe cubrirse con tests frontend normales.
