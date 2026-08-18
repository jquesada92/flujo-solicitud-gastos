# Arquitectura FastAPI

## Referencia

La arquitectura sigue los patrones recomendados por la documentación oficial de FastAPI para aplicaciones grandes, dependencias, lifespan, seguridad y testing.

## Application factory

`app/application.py` crea la aplicación y registra middleware, routers, health endpoint y lifespan mínimo. `app/main.py` existe únicamente como alias de compatibilidad.

Las rutas canónicas se registran antes del router legacy. Entre ellas:

```text
request_actions.py      → creación
revision_actions.py     → corregir / reenviar
cancellation_actions.py → cancelación
quotation_actions.py    → votación
document_actions.py     → documentos
financial_actions.py    → factura / cierre
tracking.py             → dashboard y seguimiento compartido
position_access.py      → herencia Cargo → Rol
```

Esto permite reemplazar gradualmente handlers legacy sin depender del orden accidental de rutas en `expenses.py` o `users.py`.

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

Gobierna comportamiento funcional sensible al ambiente, actualmente la segregación de la cuenta `TECHNICAL_ADMIN`.

### `is_production`

Es verdadero cuando el ambiente es productivo o el runtime está alojado bajo condiciones que requieren endurecimiento, por ejemplo Render.

Gobierna validaciones como secretos fuertes, CORS HTTPS explícito y credenciales requeridas.

Esta separación es deliberada: un preview alojado puede requerir secretos fuertes sin perder la capacidad de probar todo el flujo con la cuenta técnica.

## IAM y dependencias FastAPI

`require_permission(code)` consulta `iam_service.has_permission()`.

Para todo usuario activo, `requests:read` es baseline de producto. Los demás permisos de usuarios operativos pueden provenir de cuatro fuentes configurables:

```text
Permiso directo
Rol directo
Grupo → Rol → Permiso
Cargo/Posición → Rol → Permiso
```

El modelo persistente incorpora:

```text
user_positions → positions → position_roles → roles → role_permissions → permissions
```

El nombre/código de un Cargo nunca se compara para autorizar. Un Cargo concede acceso únicamente porque existe una relación persistida con uno o más Roles.

Para una cuenta registrada en `system_accounts`:

```text
ENVIRONMENT=production
→ permisos activos ∩ {requests:read, config:manage}

ENVIRONMENT!=production
→ todos los permisos activos del producto
```

No existe bypass por `UserRole.ADMIN`, email, nombre de Cargo o ID.

`users_with_permission()` aplica la misma resolución a poblaciones de workflow. Sus fuentes SQL son:

```text
user_permissions
direct user roles
group roles
position roles
system-account policy cuando corresponda
```

Por tanto:

- un usuario que hereda `requests:approve` por Cargo es elegible como aprobador/votante;
- un usuario que lo hereda por Grupo es igualmente elegible;
- producción excluye la cuenta técnica de permisos financieros aunque exista una asignación accidental por Grupo/Cargo/Rol/directa;
- no producción permite participación de la cuenta técnica para pruebas.

`permission_sources()` distingue el origen, por ejemplo:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

## API de Cargos y Roles

`position_access.py` se registra antes de `iam.py` para enriquecer la ruta de Cargos sin reconstruir el router legacy.

```text
GET    /api/iam/positions
PUT    /api/iam/positions/{position_id}/roles/{role_id}
DELETE /api/iam/positions/{position_id}/roles/{role_id}
```

`GET /positions` devuelve `role_ids` además de los metadatos del Cargo.

Las mutaciones:

- requieren `config:manage`;
- no aceptan Roles técnicos `system_managed`;
- no dependen de nombres organizacionales.

## Seguimiento universal

`tracking.py` registra antes del router legacy:

```text
GET /api/expenses
GET /api/expenses/dashboard
```

Ambos requieren `requests:read`, cuya resolución incluye el baseline para usuarios activos.

El listado no filtra por `UserRole.REQUESTER` ni por `requested_by`. Esto permite que todos los usuarios activos den seguimiento a solicitudes de la organización.

La lectura compartida no concede acciones mutables. El dashboard calcula `pending_my_action` solo desde capacidades ejecutables (`requests:approve`, `requests:close`) e invitaciones/asignaciones vigentes.

## Cancelación por recurso

La cancelación no se modela como una consecuencia de `requests:create`.

`cancellation_actions.py` implementa:

```text
POST /api/expenses/{request_id}/cancel
```

La autorización es:

```text
solicitud abierta
AND (
  current_user.email == expense.requested_by
  OR current_user está registrado en system_accounts
)
```

Estados abiertos cancelables:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
```

Estados no cancelables:

```text
CLOSED
CANCELLED
REJECTED
```

El endpoint bloquea la fila, exige motivo, expira aprobaciones abiertas y persiste `cancelled_at`, `cancelled_by` y `cancellation_reason`.

El Administrador del sistema puede cancelar solicitudes abiertas incluso en producción como excepción explícita de ciclo de vida. Esto se determina mediante `system_accounts`; no concede `requests:create`, `requests:approve` ni `requests:close` y no lo incorpora a poblaciones financieras.

`tracking.py` devuelve `ExpenseOut.can_cancel` calculado por solicitud. El endpoint vuelve a autorizar siempre aunque el frontend consuma correctamente `can_cancel`.

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

`can_cancel` no forma parte de estos aliases ni de `permission_codes`: es una capacidad por recurso calculada en el contrato de solicitud.

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
- resuelve nuevos participantes con `requests:approve` usando todas las fuentes IAM, incluido Cargo/Grupo;
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
        ↓
20260818_0004 position role inheritance
```

`0003` repara datos históricos MULTI_QUOTE.

`0004`:

- crea `position_roles`;
- importa una sola vez la configuración legacy de `access_profiles/users.title` hacia `Position`, `Role`, `RolePermission`, `PositionRole` y `UserPosition`;
- convierte `can_approve=true` legacy en un Rol que contiene `requests:approve`;
- excluye cuentas técnicas de la asignación organizacional migrada;
- deja de depender de esa información legacy una vez finalizado el upgrade.

`tests/test_migrations.py` exige `0004` como único head.

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

`ExpenseOut` incluye `can_cancel` para la capacidad por solicitud.

`PositionOut` incluye `role_ids` para administrar la herencia Cargo → Rol.

Al crear endpoints nuevos se debe declarar `response_model` salvo streaming/file o razón documentada.

## Testing

`tests/test_iam_api.py` usa `FastAPI TestClient` con SQLite aislada y cubre políticas de cuenta técnica.

`tests/test_position_role_inheritance.py` verifica:

- Cargo → Rol → `requests:approve`;
- fuente `Cargo Tesorero → Aprobador`;
- `users_with_permission('requests:approve')` incluye usuarios heredados por Cargo;
- Grupo y Cargo son fuentes simultáneas;
- un Cargo inactivo deja de conceder permiso.

`tests/test_universal_tracking.py` verifica el baseline `requests:read`, dashboard compartido y seguimiento de solicitudes ajenas sin conceder mutaciones.

`tests/test_request_cancellation.py` verifica la regla de cancelación por propietario/cuenta técnica.

`tests/test_multi_quote_revision.py` verifica el invariant de correcciones.

`tests/test_migrations.py` verifica topología Alembic hasta `0004` y el contrato de compatibilidad de la migración de Cargos.

`tests/test_container_portability.py` verifica defensas de portabilidad local.

## Producción vs preview

`render.yaml` de producción declara explícitamente:

```env
ENVIRONMENT=production
```

Un servicio de preview/test debe usar otro valor si se desea acceso funcional completo con la cuenta técnica.

## Router/frontend legacy

`api/expenses.py`, `api/users.py` y `frontend/src/main.jsx` contienen partes del MVP anterior.

`api/users.py` todavía contiene `AccessProfile`, `BOARD_CODES`, `users.title` y `can_*`. Son deuda de compatibilidad y no deben utilizarse para nuevas decisiones de autorización. `0004` los lee una sola vez para preservar la configuración productiva existente.

La pantalla autoritativa de acceso es **Configuración → Accesos**:

- Grupos administra miembros + Roles;
- Cargos administra Roles heredados;
- Usuarios administra Grupos/Cargos/Roles directos/Permisos directos.

El frontend monolítico todavía contiene bypasses visuales como:

```text
user.role === "ADMIN"
canClose={true}
```

El backend no confía en esos valores y deben retirarse progresivamente.

### Transform temporal del frontend

Mientras `ExpenseForm` siga definido también dentro del monolito, `frontend/vite.config.js` importa `./expense-form.jsx` y elimina la definición legacy completa durante dev/build.

Mientras `ExpenseTable` conserve el guard legacy de cancelación, el transform sustituye esa condición por `x.can_cancel`.

Estas transformaciones son deuda temporal. Deben retirarse cuando `main.jsx` importe directamente los componentes modulares y la visibilidad de acciones se cubra con tests frontend normales.
