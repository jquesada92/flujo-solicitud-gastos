# Flujo de Control de Gastos

> Constitución vigente: **2.5.0**.

Aplicación web para solicitar, evaluar, aprobar, ejecutar y documentar gastos con trazabilidad y evidencia verificable.

El producto es **neutral respecto al tipo de organización**. Un PH, empresa, comité o área de negocio puede configurar su estructura sin modificar el código.

## Principios del producto

- Backend FastAPI es la autoridad final.
- La estructura organizacional es **dato configurable**, no código.
- `Usuario`, `Grupo`, `Rol`, `Permiso` y `Cargo` son conceptos separados.
- Un Cargo puede heredar Roles; **su nombre nunca autoriza por sí mismo**.
- Un Grupo puede heredar Roles y sus miembros reciben esos permisos.
- Todo usuario activo puede entrar a Inicio y dar seguimiento a las solicitudes mediante el baseline `requests:read`.
- Ver una solicitud ajena no concede acciones sobre ella.
- Las filas de **Inicio → Acciones pendientes** abren una acción contextual del usuario; **Ver todas** navega a Solicitudes.
- Solo el solicitante original o el Administrador del sistema pueden cancelar una solicitud abierta.
- La cuenta técnica tiene política explícita por ambiente.
- Área y Categoría son dimensiones independientes.
- Una corrección nunca cambia silenciosamente el tipo de solicitud.
- La pestaña seleccionada antes de corregir nunca determina el tipo del editor.
- Documentos e historial forman parte del expediente auditable.
- Migraciones son versionadas con Alembic y no se ejecutan dentro del lifespan de FastAPI.

## Terminología

- **Usuario**: cuenta que interactúa con el sistema.
- **Grupo**: conjunto configurable de usuarios que puede heredar Roles.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica del producto.
- **Cargo / Posición**: dato organizacional configurable que puede heredar Roles; el nombre del Cargo no autoriza directamente.
- **Área**: unidad/departamento/función asociada al gasto.
- **Categoría**: naturaleza del bien o servicio.

## IAM configurable

Para usuarios operativos activos:

```text
Usuario
  ├─ Baseline del producto: requests:read
  ├─ Grupos ───────────> Roles ──> Permisos
  ├─ Cargos/Posiciones -> Roles ──> Permisos
  ├─ Roles directos ─────────────> Permisos
  └─ Permisos directos
```

`requests:read` es una capacidad base no revocable mientras el usuario esté activo. Para las demás capacidades, si no existe ALLOW explícito, el resultado es DENY.

Un mismo Rol puede reutilizarse en varios Cargos y Grupos. Por ejemplo:

```text
Rol: Aprobador
  requests:approve

Cargo: Presidente      → Aprobador
Cargo: Vicepresidente  → Aprobador
Cargo: Tesorero        → Aprobador

Grupo: Junta Directiva → Aprobador
```

Ningún nombre como Presidente, Tesorero, CFO o Procurement Manager está hardcodeado en runtime. La autorización proviene de relaciones persistidas `Cargo/Grupo → Rol → Permiso`.

### Permisos atómicos iniciales

| Código | Capacidad |
| --- | --- |
| `requests:read` | Consultar solicitudes/documentos autorizados; baseline para usuarios activos |
| `requests:create` | Crear/corregir solicitudes y cargar soportes |
| `requests:approve` | Participar en votaciones y decisiones |
| `requests:close` | Subir/reemplazar factura y cerrar |
| `config:manage` | Administrar configuración e IAM |

Los clientes pueden crear grupos, roles, cargos y asignaciones desde la interfaz; no pueden inventar permisos que el backend no implemente.

La cancelación de una solicitud abierta **no se deriva de `requests:create`**. Es una regla de propiedad del recurso: únicamente el solicitante original o la cuenta protegida de Administrador del sistema pueden ejecutarla.

Los códigos del dashboard `APPROVAL_DECISION`, `QUOTATION_VOTE`, `CORRECT_REQUEST` y `CLOSE_REQUEST` tampoco son nuevos permisos IAM. Son tareas contextuales calculadas desde permiso efectivo + asignación + estado actual.

## Administrador del sistema por ambiente

La cuenta creada por `ADMIN_*` se registra como `TECHNICAL_ADMIN` en `system_accounts`. Su comportamiento **no depende del email, cargo ni `UserRole.ADMIN`**.

### Producción

Con:

```env
ENVIRONMENT=production
```

sus permisos IAM efectivos máximos son:

```text
config:manage
requests:read
```

En producción no puede:

```text
requests:create
requests:approve
requests:close
```

Aunque un rol, grupo, cargo o permiso directo intente concedérselos, el backend los filtra. Tampoco participa en poblaciones financieras de aprobación/votación ni recibe esas acciones en su bandeja personal.

Como excepción explícita de administración del ciclo de vida, el Administrador del sistema **sí puede cancelar una solicitud abierta**. Esta facultad se valida mediante `system_accounts`; no equivale a conceder `requests:create`, `requests:approve` ni `requests:close`.

### Local / dev / test / staging / preview

Con cualquier `ENVIRONMENT` diferente de `production`, la cuenta técnica recibe **todos los permisos atómicos activos** para poder probar el producto end-to-end con un solo usuario.

Puede crear, consultar, aprobar, votar, subir/reemplazar factura, cerrar y administrar configuración. También puede entrar en poblaciones de aprobación/votación cuando corresponda.

Ejemplos:

```env
ENVIRONMENT=development
ENVIRONMENT=test
ENVIRONMENT=preview
```

`RENDER=true` sigue activando validaciones fuertes de secretos/CORS, pero no convierte automáticamente un preview en producción para autorización. Solo `ENVIRONMENT=production` activa la segregación financiera.

## Seguimiento universal

Todo usuario activo y autenticado puede:

- abrir **Inicio / Dashboard**;
- ver métricas generales de solicitudes;
- abrir **Solicitudes**;
- consultar solicitudes creadas por otros usuarios para dar seguimiento.

El baseline no concede creación, aprobación, cierre ni configuración.

### Acciones pendientes del usuario

El dashboard no deduce acciones únicamente desde el estado de la solicitud. `pending_action_service.py` combina permiso efectivo + asignación/estado concreto.

```text
APPROVAL_DECISION
= requests:approve + Approval.PENDING asignado al usuario

QUOTATION_VOTE
= requests:approve + invitación vigente + sin voto

CORRECT_REQUEST
= requests:create + solicitud propia NEEDS_REVISION

CLOSE_REQUEST
= requests:close + solicitud APPROVED
```

`GET /api/expenses/dashboard` devuelve los códigos en cada `pending_item`.

Al seleccionar una fila de **Acciones pendientes**, el frontend abre un modal y revalida:

```text
GET /api/expenses/{request_id}/my-actions
```

El modal muestra únicamente controles que siguen vigentes para ese usuario:

- aprobar / rechazar / solicitar corrección;
- votar una cotización revisando sus soportes;
- subir factura y cerrar;
- abrir una solicitud propia para corregir / reenviar.

**Ver todas** sigue navegando a la pantalla de Solicitudes.

Después de registrar una acción, el dashboard y el detalle contextual se recargan. Si la tarea ya fue respondida desde correo, otra pestaña o una sesión distinta, el modal puede informar que ya no quedan acciones pendientes.

La aprobación desde el modal usa:

```text
POST /api/expenses/{request_id}/approval-decision
```

y no expone al frontend el token bearer de los links de correo.

El listado canónico `GET /api/expenses` devuelve además `can_cancel` por solicitud. La UI usa ese valor para mostrar u ocultar **Cancelar solicitud** y no intenta inferir la autorización desde roles, cargos o `can_request`.

## Contrato del usuario autenticado

El backend devuelve los permisos efectivos actuales en:

```text
permission_codes
```

Y durante la transición del frontend legacy también deriva:

```text
can_request   <- requests:create
can_approve   <- requests:approve
can_view      <- requests:read
can_configure <- config:manage
can_close     <- requests:close
```

Estos aliases son solo UX/compatibilidad. El backend siempre vuelve a validar el permiso canónico o la regla de propiedad aplicable al recurso.

Las acciones contextuales del dashboard no forman parte de `permission_codes`.

## Consola gráfica de Accesos

En **Configuración → Accesos** se administran:

- usuarios;
- grupos;
- roles;
- permisos;
- cargos;
- miembros de grupos;
- roles heredados por grupos;
- roles heredados por cargos;
- roles directos;
- permisos directos;
- cargos de cada usuario;
- permisos efectivos y su origen.

### Ejemplo por Grupo

```text
Grupo: Junta Directiva
  Miembros: Presidente, Vicepresidente, Tesorero
  Rol: Aprobador
    requests:approve
```

### Ejemplo por Cargo

```text
Cargo: Presidente      → Rol Aprobador
Cargo: Vicepresidente  → Rol Aprobador
Cargo: Tesorero        → Rol Aprobador

Rol Aprobador:
  requests:approve
```

Ambas estrategias son válidas y pueden combinarse. Una empresa puede usar Procurement, Finance, IT, Executive Committee o cualquier estructura propia sin cambiar código.

La sección **Permisos efectivos** identifica también el origen, por ejemplo:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
```

## Arquitectura

```mermaid
flowchart LR
    U[Usuario] --> F[React + Vite / Vercel]
    F -->|HTTPS JSON| A[FastAPI / Render]
    A --> D[(PostgreSQL / Neon)]
    A --> S[(Disco privado Render)]
    A --> E[Brevo API]
```

Backend:

```text
backend/app/
├── api/          # HTTP / APIRouter
├── core/         # Settings, DB, security, rate limit
├── models/       # SQLAlchemy
├── schemas/      # Pydantic
├── services/     # lógica reutilizable
├── application.py
└── main.py       # alias de compatibilidad
```

Frontend relevante para solicitudes/accesos:

```text
frontend/src/
├── expense-form.jsx       # formulario canónico SIMPLE / MULTI_QUOTE
├── home-dashboard.jsx     # dashboard + modal de acciones personales
├── home-dashboard.css     # estilos del modal contextual
├── iam-admin.jsx          # consola IAM canónica
├── main.jsx               # shell legacy aún pendiente de modularización total
└── domain-normalization.js
```

### FastAPI

- `APIRouter` separa dominios/capacidades.
- `get_db()` entrega una sesión SQLAlchemy por request y la cierra siempre.
- configuración centralizada con `pydantic-settings`.
- `lifespan` no ejecuta DDL/backfills/seeds de negocio.
- SQLAlchemy/filesystem síncrono usa path operations `def`.
- contratos sensibles usan response models explícitos.
- tests HTTP usan `FastAPI TestClient`.

Rutas canónicas actualmente registradas antes de compatibilidad legacy incluyen creación, corrección, cancelación, documentos, acciones financieras, acciones contextuales del usuario, seguimiento y herencia de Roles por Cargo.

## Seguridad

- JWT firmado con expiración absoluta.
- inactividad de sesión configurable.
- revocación mediante `session_version`.
- Argon2 para hashes nuevos mediante `pwdlib`.
- hashes PBKDF2 legacy se migran automáticamente a Argon2 tras login exitoso.
- rate limiting separado para read/write/upload/sensitive.
- CORS explícito en producción/runtime alojado.
- documentos privados y validación de firma real de archivo.
- autorización por permisos persistidos, capacidades base, propiedad del recurso y política técnica ambiental; no por emails hardcodeados/nombres de cargos/IDs mágicos.
- `Cargo → Rol → Permiso` es válido; `if cargo == 'TESORERO'` no lo es.
- cuenta técnica segregada del flujo financiero en producción, con la excepción explícita de cancelación administrativa de solicitudes abiertas.
- un usuario con `requests:create` no puede cancelar por ese hecho una solicitud creada por otro usuario.
- el modal de acciones vuelve a autorizar en backend antes de cada mutación y no confía en una tarjeta que pudo quedar obsoleta.

## Base de datos y migraciones

Alembic es la herramienta canónica. La cadena actual es lineal:

```text
backend/alembic/versions/
├── 20260817_0000_application_baseline.py
├── 20260817_0001_iam_foundation.py
├── 20260817_0002_system_accounts.py
├── 20260817_0003_backfill_multi_quote_request_type.py
└── 20260818_0004_position_role_inheritance.py
```

`0003` repara solicitudes históricas que tengan evidencia durable de múltiples cotizaciones pero conserven accidentalmente `request_type=SIMPLE`.

`0004` agrega `position_roles` y convierte una sola vez la configuración legacy de Cargos/Perfiles (`access_profiles` + `users.title`) a IAM canónico. Los `can_*` se usan únicamente como entrada histórica de migración; runtime sigue consultando Roles/Permisos persistidos.

La migración preserva, entre otros, los cargos existentes configurados con `can_approve=true` convirtiéndolos en Roles con `requests:approve` y asignando los usuarios actuales al Cargo canónico correspondiente.

El modal contextual y `pending_action_service.py` no requieren una migración adicional.

El contenedor ejecuta antes de FastAPI:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

El bootstrap se ejecuta como módulo Python desde la raíz `backend/`/`/app`.

## Desarrollo local

### Docker Compose

```bash
docker compose up --build
```

Docker Compose publica el frontend Nginx en:

```text
http://localhost:3000
```

Por ese motivo, Compose fuerza por defecto el `PUBLIC_URL` del backend a `http://localhost:3000` para que los enlaces incluidos en correos de aprobación/votación sean alcanzables. El `.env` de la raíz puede personalizarlo con:

```env
LOCAL_PUBLIC_URL=http://localhost:3000
LOCAL_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

`localhost:5173` corresponde al servidor de desarrollo de Vite cuando se ejecuta directamente con `npm run dev`; no debe aparecer en correos mientras solo esté levantado Docker Compose.

El valor por defecto de `ENVIRONMENT` es no productivo, por lo que el Administrador del sistema puede probar todas las capacidades disponibles localmente.

Para comprobarlo:

```text
GET /api/iam/me/permissions
```

debe devolver los permisos activos del catálogo, por ejemplo:

```text
requests:read
requests:create
requests:approve
requests:close
config:manage
```

### Correo local con Google SMTP

El entorno local debe usar correo real mediante Gmail/Google Workspace SMTP. Copia `backend/.env.example` como `backend/.env` y completa:

```env
ENVIRONMENT=development
EMAIL_MODE=smtp
EMAIL_FROM=<TU_CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<TU_CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_DE_GOOGLE>
```

Alternativa soportada:

```env
SMTP_PORT=587
SMTP_SECURITY=starttls
```

Para cuentas Google con Verificación en 2 pasos, usa una **App Password**; no guardes la contraseña normal de Google ni la App Password en Git.

Prueba el transporte antes de crear una solicitud:

```bash
docker compose exec backend python -m scripts.test_email --to destino@example.com
```

Si el comando termina correctamente, Google aceptó el correo. Luego prueba el flujo SIMPLE/MULTI_QUOTE. Bajo Docker Compose, un link nuevo de aprobación/votación debe comenzar por `http://localhost:3000/email-action/`. Ver `docs/EMAIL_CONFIGURATION.md` y `specs/004-email-delivery-by-environment/`.

### Backend sin Docker

```bash
cd backend
python -m venv .venv
# activar .venv
pip install -r requirements.txt
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### Portabilidad Windows → Linux

- `.gitattributes` fuerza `*.sh text eol=lf`.
- El Dockerfile elimina defensivamente CRLF.
- El frontend Compose espera `/api/health` antes de iniciar Nginx.
- El comando canónico del bootstrap es `python -m scripts.bootstrap_admin`.

Si el backend falla:

```bash
docker compose ps -a
docker compose logs backend --tail=200
```

No usar `docker compose down -v` salvo que se acepte eliminar los datos PostgreSQL locales.

## Variables principales

### Producción

```env
ENVIRONMENT=production
DATABASE_URL=<NEON_URL>
SECRET_KEY=<32+ RANDOM CHARS>
ANALYTICS_HASH_KEY=<DIFFERENT 32+ RANDOM CHARS>
PUBLIC_URL=<VERCEL_URL>
CORS_ALLOWED_ORIGINS=<VERCEL_URL>
TOKEN_EXPIRE_MINUTES=480
SESSION_IDLE_MINUTES=30
APP_TIME_ZONE=America/Panama

EMAIL_MODE=brevo
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
EMAIL_FROM=<VERIFIED_EMAIL>

ADMIN_NAME=Administrador del sistema
ADMIN_EMAIL=<TECHNICAL_ADMIN_EMAIL>
ADMIN_PASSWORD=<12+ SECURE CHARS>

UPLOAD_DIR=/app/uploads
MAX_UPLOAD_STORAGE_MB=450
```

Las variables Brevo viven únicamente en el backend/Render. No colocar `BREVO_API_KEY` ni secretos SMTP en Vercel/Vite.

`render.yaml` productivo establece explícitamente `ENVIRONMENT=production`.

### No producción

Por ejemplo:

```env
ENVIRONMENT=development
```

o:

```env
ENVIRONMENT=test
```

No se debe usar `ENVIRONMENT=production` en un entorno donde se pretenda usar la cuenta técnica para pruebas financieras completas.

Frontend:

```env
VITE_API_URL=<BACKEND_URL>
VITE_TIME_ZONE=America/Panama
```

No existe una variable de entorno especial para Cargo/Grupo → Rol ni para el modal de acciones; esas reglas viven en backend/PostgreSQL y en el bundle normal del frontend.

## Clasificación Área + Categoría

Área y Categoría son catálogos independientes con relación configurable N:M.

```text
Administración ─┐
IT              ├── Equipos
Operaciones     ┘
```

No se duplica la categoría `Equipos` por cada Área.

## Flujo de solicitudes

### Simple

Una solicitud simple contiene proveedor, monto y soporte/cotización. La creación requiere `requests:create`.

### Múltiples cotizaciones

La población de votación se obtiene desde usuarios con `requests:approve`, excluyendo al solicitante.

`requests:approve` puede provenir de:

```text
Permiso directo
Rol directo
Grupo → Rol
Cargo → Rol
```

- Producción: las cuentas técnicas quedan fuera de permisos financieros.
- No producción: la cuenta técnica puede participar para pruebas si no queda excluida por una regla propia del flujo, por ejemplo ser el mismo solicitante.

Las invitaciones guardadas representan el snapshot de participantes de esa ronda.

### Acciones pendientes desde Inicio

La bandeja de Inicio presenta tareas concretas del usuario actual.

Al hacer clic en una fila se abre un modal contextual, no la lista genérica de Solicitudes. Según el workflow puede mostrar:

```text
Responder aprobación
Votar cotización
Subir factura y cerrar
Corregir y reenviar
```

La acción se vuelve a consultar en backend al abrir el modal y después de cada decisión.

### Seguimiento y cancelación

Las solicitudes abiertas son visibles para todos los usuarios activos, pero la visibilidad no concede mutación.

Puede cancelar una solicitud abierta únicamente:

```text
solicitante original
OR
Administrador del sistema registrado en system_accounts
```

Estados cancelables:

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

La cancelación requiere motivo y conserva `cancelled_at`, `cancelled_by` y `cancellation_reason`. El botón del frontend depende de `can_cancel` calculado por el backend.

### Corrección y reenvío

`Corregir / reenviar` **preserva siempre el tipo original/canónico**:

```text
SIMPLE      -> SIMPLE
MULTI_QUOTE -> MULTI_QUOTE
```

La pestaña que estaba seleccionada antes de pulsar **Corregir / reenviar** no participa en esa decisión. Si la pantalla estaba en **Solicitud sencilla** y se corrige una MULTI_QUOTE, el editor debe abrir directamente como MULTI_QUOTE.

El formulario canónico vive en `frontend/src/expense-form.jsx`. Durante corrección calcula el tipo efectivo exclusivamente desde la solicitud/evidencia durable; la pestaña solo aplica a nuevas solicitudes.

Para compatibilidad histórica se considera MULTI_QUOTE cuando:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Alembic `0003` persiste la reparación de esas filas legacy.

Cuando se corrige una MULTI_QUOTE:

- se muestra `Tipo de solicitud: Múltiples cotizaciones` como dato de solo lectura;
- el layout visible es **Opciones para votación**, no el formulario SIMPLE;
- se restauran las cotizaciones existentes;
- proveedor, monto, URL y observaciones se editan dentro de cada opción;
- los soportes existentes se conservan y se indican como soporte existente;
- por ahora se mantiene la misma cantidad de opciones;
- se genera un `flow_id` nuevo;
- votos e invitaciones vigentes de la ronda anterior se reinician;
- los eventos históricos se conservan;
- la solicitud vuelve a `QUOTATION_VOTING`.

Mientras `main.jsx` conserve las definiciones históricas de `ExpenseForm` y `HomeDashboard`, `frontend/vite.config.js` hace extracciones estructurales durante dev/build: importa los componentes modulares y elimina las funciones legacy completas del bundle. El mismo transform sustituye el guard legacy de cancelación por `x.can_cancel`. Ver `docs/REQUEST_CORRECTIONS.md`, `docs/REQUEST_TRACKING.md` y sus specs.

### Aprobación

La población canónica de aprobadores se obtiene desde el permiso efectivo `requests:approve`. El motor no pregunta si alguien se llama/carga como Presidente o Tesorero; sí reconoce `requests:approve` cuando llega mediante un Rol asociado a ese Cargo.

> La fórmula de mayoría legacy todavía requiere una feature separada para ajustarse completamente a la Constitución 2.5.0.

### Cierre

Cerrar o reemplazar factura requiere `requests:close`. `APPROVED` no equivale a `CLOSED`.

La cuenta técnica puede ejecutar cierre fuera de producción y recibe 403 en producción.

## Testing

```bash
cd backend
python -m unittest discover -s tests -v
```

La suite IAM verifica específicamente:

- cuenta técnica con todos los permisos activos en no-producción;
- login no-productivo con `permission_codes` + aliases efectivos;
- participación de cuenta técnica en población de aprobación fuera de producción;
- restricción config/read en producción;
- 403 de cierre en producción incluso con permiso financiero accidental;
- exclusión de población de aprobación en producción.

`test_position_role_inheritance.py` verifica:

- Cargo → Rol → `requests:approve`;
- origen visible `Cargo Tesorero → Aprobador`;
- `users_with_permission('requests:approve')` incluye aprobadores por Cargo;
- Grupo y Cargo funcionan como fuentes simultáneas;
- Cargo inactivo no concede permisos.

La suite de seguimiento verifica que cualquier usuario activo reciba `requests:read`, pueda ver solicitudes ajenas y cargar el dashboard sin adquirir permisos mutables.

`test_pending_actions.py` verifica:

- aprobación pendiente asignada → `APPROVAL_DECISION`;
- decisión autenticada desde el modal sin token de correo;
- invitación MULTI_QUOTE → `QUOTATION_VOTE`;
- solicitud propia `NEEDS_REVISION` → `CORRECT_REQUEST`;
- solicitud `APPROVED` → `CLOSE_REQUEST` solo para usuario con `requests:close`.

`test_frontend_dashboard_contract.py` protege click de fila → modal, los cuatro tipos de acción y la revalidación posterior a una mutación.

La suite de cancelación verifica:

- `can_cancel=true` para el solicitante de una solicitud abierta;
- `can_cancel=false` para otro usuario empresarial;
- `requests:create` no permite cancelar una solicitud ajena;
- cancelación propia durante `QUOTATION_VOTING`;
- cancelación administrativa por cuenta técnica;
- rechazo de cancelación de una solicitud cerrada.

La suite de correcciones verifica además que una MULTI_QUOTE no pueda degradarse a SIMPLE, que un registro legacy con flag SIMPLE pero evidencia múltiple sea reparado, que conserve evidencia, que reinicie votos/invitaciones y que el frontend modular use el tipo efectivo para render y payload.

Prueba manual específica de acciones pendientes:

```text
1. iniciar sesión con un usuario que tenga una aprobación PENDING asignada;
2. Inicio → Acciones pendientes → seleccionar la solicitud;
3. verificar que se abre un modal y NO se navega inmediatamente a Solicitudes;
4. verificar Responder aprobación con Rechazar / Solicitar corrección / Aprobar;
5. registrar una decisión y comprobar que dashboard + modal se refrescan;
6. repetir con una invitación MULTI_QUOTE y verificar selección/voto;
7. repetir con usuario requests:close y verificar factura/cierre.
```

Prueba manual específica de herencia de aprobación:

```text
1. Configuración → Accesos → Roles: crear/seleccionar Aprobador con requests:approve;
2. Accesos → Cargos: asociar Aprobador a Tesorero y Vicepresidente;
3. Accesos → Usuarios: confirmar los Cargos asignados;
4. verificar en Permisos efectivos: requests:approve + origen Cargo ... → Aprobador;
5. crear una MULTI_QUOTE con uno de ellos;
6. verificar que el otro aparezca en la ronda de votación.
```

Prueba manual específica de corrección:

```text
1. dejar seleccionada Solicitud sencilla;
2. pulsar Corregir / reenviar en una MULTI_QUOTE;
3. verificar Tipo de solicitud: Múltiples cotizaciones;
4. verificar Opciones para votación con las cotizaciones existentes;
5. verificar que no aparezca el formulario sencillo como estructura principal.
```

Prueba manual específica de cancelación:

```text
1. iniciar sesión como solicitante de una MULTI_QUOTE en QUOTATION_VOTING;
2. verificar que aparezca Cancelar solicitud;
3. iniciar sesión como otro usuario y verificar que no aparezca;
4. iniciar sesión como Administrador del sistema y verificar que sí aparezca;
5. cancelar indicando motivo y comprobar estado CANCELLED.
```

GitHub Actions normalmente ejecuta backend, frontend y Docker, pero la cuenta alcanzó su cuota de Actions durante este PR. Mientras no se restablezca la cuota, ejecutar localmente:

```bash
cd backend
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build

cd ..
docker compose build --no-cache
docker compose up -d
```

## Documentación

Orden de autoridad:

1. `.specify/memory/constitution.md`
2. `specs/*/spec.md`
3. criterios de aceptación
4. `specs/*/plan.md`
5. código
6. README/prompts/docs derivados

Documentos principales:

- `docs/DOCUMENTATION_POLICY.md`
- `docs/TERMINOLOGY.md`
- `docs/CLASSIFICATION_MODEL.md`
- `docs/IAM_MODEL.md`
- `docs/FASTAPI_ARCHITECTURE.md`
- `docs/REQUEST_CORRECTIONS.md`
- `docs/REQUEST_TRACKING.md`
- `docs/EMAIL_CONFIGURATION.md`
- `docs/HISTORY.md`
- `CHANGELOG.md`
- `PROMPT_RECONSTRUCCION.md`
- `specs/006-position-group-role-inheritance/`

## Deuda de transición conocida

- `UserRole`, `title` y `can_*` permanecen temporalmente para compatibilidad; no autorizan.
- `AccessProfile` y `BOARD_CODES` siguen físicamente en `/api/users` legacy. `0004` los usa solo como entrada de migración; no son arquitectura objetivo.
- La pantalla autoritativa para cambios de acceso es **Configuración → Accesos**.
- `/api/users` legacy continúa temporalmente.
- `frontend/src/main.jsx` sigue siendo monolítico en otras áreas.
- El monolito todavía contiene bypasses visuales legacy como `user.role === "ADMIN"` y `canClose={true}`; el backend no confía en ellos. Deben migrarse a `permission_codes`/capacidades por recurso.
- `vite.config.js` elimina temporalmente las implementaciones legacy completas de `ExpenseForm` y `HomeDashboard`, e integra el guard `can_cancel`. Debe retirarse cuando el shell importe componentes canónicos directamente.
- `domain-normalization.js` sigue como capa temporal.
- quorum/mayoría de aprobación y empate de cotizaciones requieren specs funcionales separadas.
