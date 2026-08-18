# Historial funcional y técnico

## 2026-08-18 — Acciones pendientes abren un modal contextual del usuario

### Problema observado

En **Inicio → Acciones pendientes**, seleccionar una solicitud ejecutaba el mismo callback que **Ver todas**. El resultado era una navegación genérica a **Solicitudes**, aunque la tarjeta decía que existía una acción concreta que requería la atención del usuario autenticado.

Esto obligaba al usuario a volver a localizar la solicitud y no distinguía entre:

```text
puedo aprobar en general
vs
esta aprobación concreta está asignada a mí y sigue pendiente
```

### Decisión funcional

Una fila de **Acciones pendientes** pasa a representar una tarea contextual y abre una ventana/modal de **Mis acciones** para esa solicitud.

**Ver todas** conserva una responsabilidad diferente:

```text
Ver todas
→ navegar a Solicitudes

clic en una fila pendiente
→ abrir modal contextual
```

Las acciones contextuales iniciales son:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

Estos códigos **no son permisos IAM nuevos**. Se derivan de:

```text
permiso efectivo
+
asignación concreta del workflow
+
estado vigente
```

### Backend authoritative

Se agrega `pending_action_service.py` para resolver las tareas del usuario actual:

- `APPROVAL_DECISION`: `requests:approve` + `Approval.PENDING` asignado al usuario + solicitud `PENDING_APPROVAL`;
- `QUOTATION_VOTE`: `requests:approve` + invitación vigente + solicitud `QUOTATION_VOTING` + ausencia de voto del usuario;
- `CORRECT_REQUEST`: `requests:create` + solicitud propia `NEEDS_REVISION`;
- `CLOSE_REQUEST`: `requests:close` + solicitud `APPROVED`.

`tracking.py` usa este mismo resolver para `pending_my_action` y para los códigos de cada `pending_item`.

Se agrega:

```text
GET  /api/expenses/{request_id}/my-actions
POST /api/expenses/{request_id}/approval-decision
```

`my-actions` revalida la tarea al abrir el modal. La decisión de aprobación autenticada reutiliza `approval_engine.apply_decision()` y no expone al frontend el token bearer de los enlaces de correo.

Votación y cierre reutilizan los endpoints canónicos existentes. La corrección dirige al editor canónico de Solicitudes para mantener los invariants SIMPLE/MULTI_QUOTE.

### Frontend

Se crea:

```text
frontend/src/home-dashboard.jsx
frontend/src/home-dashboard.css
```

El modal permite, según la tarea vigente:

- Aprobar / Rechazar / Solicitar corrección;
- revisar opciones/soportes y votar una cotización;
- subir factura y cerrar;
- abrir una solicitud propia para Corregir / reenviar.

Después de una mutación se recargan en paralelo el dashboard y `my-actions`. Si la tarea fue atendida desde correo, otra pestaña o sesión, el modal informa que ya no quedan acciones pendientes en vez de mostrar controles obsoletos.

Mientras `main.jsx` conserve la implementación histórica, Vite importa el `HomeDashboard` modular y elimina la función legacy completa entre `function HomeDashboard` y `function App()`. No se parchea el `onClick` de filas por coincidencias de whitespace.

### Ajuste UX posterior: KPIs superiores solo informativos

Durante la validación manual se detectó que **Acciones que requieren mi atención** y **Solicitudes en proceso** todavía estaban implementadas como botones. Se corrige la separación de responsabilidades:

```text
KPI superior          → información solamente
Fila acción pendiente → modal contextual
Ver todas             → Solicitudes
```

Los KPIs superiores pasan a renderizarse como `article`, sin `onClick` ni semántica de control. `test_frontend_dashboard_contract.py` protege esta regla para evitar que regresen como botones interactivos.

### Pruebas y validación

Se agregan:

- `test_pending_actions.py`;
- `test_frontend_dashboard_contract.py`.

La Constitución permanece en **2.5.0**: backend-authoritative y acciones personales del dashboard ya son principios vigentes; este cambio concreta su contrato UX en Feature 005.

GitHub Actions alcanzó la cuota de la cuenta durante este PR. Por tanto, hasta que vuelva la cuota, la validación obligatoria se ejecuta localmente: suite backend, `npm run build`, Docker build/smoke y prueba manual del modal. Un run bloqueado por cuota no se registra como CI verde.

---

## 2026-08-18 — Cargo y Grupo pasan a ser fuentes configurables de Roles

### Problema productivo que reveló la brecha

En producción se observó una solicitud MULTI_QUOTE que indicaba:

```text
No existe otro usuario activo con permiso de aprobación para participar en la votación
```

mientras la pantalla legacy mostraba usuarios Tesorero y Vicepresidente con **Aprobar** marcado.

La investigación confirmó que existían dos modelos de acceso conviviendo:

```text
Pantalla legacy
AccessProfile.can_approve → users.can_approve

Motor canónico
users_with_permission('requests:approve') → IAM persistido
```

El workflow nuevo no consulta `users.can_approve`, por lo que un cargo podía verse configurado como aprobador y aun así no formar parte de la población IAM real.

### Decisión funcional

Se evoluciona el IAM para soportar explícitamente dos formas organizacionales de herencia:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
```

Esto permite configurar, por ejemplo:

```text
Rol: Aprobador
  requests:approve

Cargo Presidente      → Aprobador
Cargo Vicepresidente  → Aprobador
Cargo Tesorero        → Aprobador

Grupo Junta Directiva → Aprobador
```

El mismo Rol puede reutilizarse en varios Cargos y Grupos.

El nombre del Cargo **no autoriza**. Runtime no puede contener condiciones como `cargo == TESORERO`; la autorización proviene exclusivamente de la relación persistida `Cargo → Rol → Permiso`.

### Implementación

Se agrega `position_roles` y el resolver IAM incorpora una nueva fuente SQL:

```text
UserPosition
→ Position(active)
→ PositionRole
→ Role(active)
→ RolePermission
→ Permission(active)
```

`effective_permission_codes()`, `users_with_permission()` y `permission_sources()` usan el mismo modelo. Los orígenes pueden mostrarse como:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
```

La consola **Configuración → Accesos → Cargos** permite seleccionar Roles heredados, mientras **Grupos** conserva miembros + Roles heredados.

### Migración 0004

`20260818_0004_position_role_inheritance.py`:

1. crea `position_roles`;
2. importa una sola vez `access_profiles` y `users.title` como datos de compatibilidad;
3. transforma los flags legacy en permisos del Rol (`can_approve → requests:approve`, etc.);
4. crea/reutiliza Positions y Roles equivalentes;
5. crea `PositionRole` y `UserPosition`;
6. excluye `system_accounts` de la asignación organizacional migrada.

Después de la migración, `can_*`, `AccessProfile`, `users.title` y `BOARD_CODES` no son autoridad runtime. La pantalla autoritativa para cambios de acceso es **Configuración → Accesos**.

La Constitución evoluciona a **2.5.0** porque Cargo deja de ser exclusivamente descriptivo: ahora puede heredar Roles configurables, manteniendo la prohibición de autorizar por nombres hardcodeados.

---

## 2026-08-17 — Seguimiento universal y cancelación por solicitante/Admin del sistema

### Decisión funcional

Todo usuario activo puede abrir **Inicio / Dashboard** y **Solicitudes** para dar seguimiento a las solicitudes de la organización. `requests:read` pasa a ser baseline de producto para usuarios activos; la lectura compartida no concede acciones mutables.

Se define además una regla explícita para cancelar solicitudes abiertas:

```text
solicitante original
OR
Administrador del sistema persistido en system_accounts
```

Tener `requests:create`, `requests:approve`, `config:manage`, un cargo o un rol particular no permite cancelar una solicitud ajena.

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

La cancelación exige motivo y conserva actor/timestamp/razón. El listado canónico devuelve `can_cancel` por solicitud para que la UI no reconstruya la regla desde flags legacy.

### Diagnóstico de producción

Una captura de Configuración inicialmente parecía confirmar que Tesorero y Vicepresidente tenían permiso de aprobación. La investigación posterior precisó que esa pantalla era legacy y reflejaba `AccessProfile.can_approve/users.can_approve`, no necesariamente `requests:approve` efectivo en IAM. Ese hallazgo dio origen a Feature 006 y a la migración `0004` documentada arriba.

### Implementación

- `tracking.py` sirve lectura compartida y calcula `can_cancel`.
- `cancellation_actions.py` registra la ruta canónica antes del router legacy.
- la cuenta técnica se identifica por `system_accounts`, no por `UserRole.ADMIN`.
- el frontend temporal consume `x.can_cancel` para el botón **Cancelar solicitud**.
- `test_request_cancellation.py` prueba propiedad, cuenta técnica y estados terminales.

La Constitución 2.4.0 introdujo backend authoritative y baseline de lectura; la regla de cancelación permanece como regla de recurso, no como permiso heredable.

---

## 2026-08-17 — Docker local expone fragilidad del parche de montaje de ExpenseForm

### Incidente confirmado

Al reconstruir el frontend local con `docker compose build --no-cache frontend`, Vite falló con:

```text
[plugin modular-expense-form]
Legacy main.jsx extraction could not find: ExpenseForm mount
```

La extracción estructural sí podía localizar la definición legacy completa de `ExpenseForm`, pero luego intentaba encontrar el punto de montaje JSX mediante una cadena exacta de espacios y saltos de línea. Ese reemplazo era innecesario y frágil.

### Corrección

`vite.config.js` conserva únicamente la transformación estructural necesaria:

1. importar `ExpenseForm` desde `./expense-form.jsx`;
2. eliminar del bundle la definición legacy entre `function ExpenseForm` y `function ClosurePanel`;
3. no tocar el JSX donde se monta `<ExpenseForm>`.

`expense-form.jsx` ya rehidrata el draft cuando cambian `draft.request_id` o `draft.flow_id`, por lo que no requiere una `key` inyectada durante build.

Se actualiza `test_frontend_revision_contract.py` para impedir que vuelva a introducirse el marcador/parche `ExpenseForm mount`. CI inspecciona además el `dist/` final para comprobar que el formulario modular está realmente presente.

La Constitución 2.3.3 fue revisada y no requiere una nueva regla: el invariant funcional ya exige que la corrección derive el tipo desde la solicitud y que CI/pruebas protejan el comportamiento. Este cambio corrige el mecanismo de implementación, no el contrato funcional.

---

## 2026-08-17 — ExpenseForm modular elimina la ruta visual SIMPLE en correcciones MULTI_QUOTE

### Incidente confirmado

La prueba manual volvió a mostrar una solicitud en **Votación de cotizaciones** que, al pulsar **Corregir / reenviar**, renderizaba el formulario sencillo. Esto confirmó que mantener el source real de `ExpenseForm` como legacy y depender de sustituciones granulares de Vite no era una frontera suficientemente confiable para una regla de negocio.

### Decisión

Se crea un formulario canónico mantenible en:

```text
frontend/src/expense-form.jsx
```

El componente usa `resolveRequestType(draft)` y un único `effectiveRequestType`. Cuando existe `draft`, el tipo efectivo se deriva exclusivamente de evidencia persistida:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Para una corrección MULTI_QUOTE, el layout sencillo deja de ser una ruta válida: el componente renderiza directamente **Opciones para votación**, restaura las opciones existentes y conserva metadata de soportes.

`vite.config.js` deja de parchear condiciones internas del formulario. Durante la transición solo importa el componente modular y elimina del bundle la función `ExpenseForm` legacy completa. El componente modular rehidrata por `draft.request_id`/`draft.flow_id`; no se inyecta una `key` mediante reemplazo textual.

### Protección

`test_frontend_revision_contract.py` ahora exige la existencia del componente modular, la autoridad de `effectiveRequestType`, restauración de opciones/soportes y la extracción completa del ExpenseForm legacy durante build.

---

## 2026-08-17 — Corrección MULTI_QUOTE: el tipo efectivo pasa a ser autoritativo

### Incidente observado

Una nueva reproducción manual mostró que la solicitud estaba claramente en **Votación de cotizaciones**, pero al pulsar **Corregir / reenviar** aparecía el formulario SIMPLE con `Monto`, `Proveedor` y un solo soporte. El backend luego rechazaba el reenvío porque el payload intentaba degradar el flujo múltiple a sencillo.

La primera corrección había restaurado `requestType` desde el draft, pero eso no era suficiente: el formulario legacy seguía usando directamente el estado React `requestType` en render, validaciones y construcción del payload.

### Corrección consolidada

Se introduce el concepto frontend temporal `effectiveRequestType`:

```text
si existe draft:
    tipo efectivo = tipo canónico/inferido de la solicitud
si es nueva solicitud:
    tipo efectivo = pestaña seleccionada
```

Durante una corrección ese tipo efectivo gobierna:

- qué editor se renderiza;
- validación de soportes;
- `request_type` enviado al backend;
- `quotation_options`;
- carga de archivos.

El tipo de la solicitud se muestra como dato de solo lectura durante la corrección. No se permite cambiar SIMPLE ↔ MULTI_QUOTE dentro de **Corregir / reenviar**.

Se agrega `test_frontend_revision_contract.py` para impedir que el transform temporal vuelva a utilizar `requestType` como autoridad de una corrección.

---

## 2026-08-17 — Enlaces de correo local alineados con Docker Compose

### Problema observado

Los correos SMTP locales llegaban correctamente, pero al abrir una acción de aprobación el navegador intentaba acceder a:

```text
http://localhost:5173/email-action/...
```

y devolvía `ERR_CONNECTION_REFUSED`.

La causa era una desalineación entre `PUBLIC_URL` y el modo de ejecución: `5173` corresponde al servidor de desarrollo de Vite, mientras que Docker Compose publica el frontend Nginx en `http://localhost:3000`.

### Corrección

`docker-compose.yml` ahora sobreescribe de forma intencional los Settings dependientes del frontend local:

```env
PUBLIC_URL=${LOCAL_PUBLIC_URL:-http://localhost:3000}
CORS_ALLOWED_ORIGINS=${LOCAL_CORS_ALLOWED_ORIGINS:-http://localhost:3000,http://localhost:5173}
```

El `.env` raíz documenta `LOCAL_PUBLIC_URL` y `LOCAL_CORS_ALLOWED_ORIGINS`. `backend/.env` sigue almacenando las credenciales y Settings propios de FastAPI.

Se agrega una prueba de regresión que exige que el puerto publicado por Compose (`3000`) y el `PUBLIC_URL` suministrado al backend permanezcan alineados.

### Regla operativa

```text
Docker Compose → http://localhost:3000
Vite directo   → http://localhost:5173
Producción     → URL HTTPS de Vercel
```

Los correos ya enviados conservan la URL con la que fueron generados; la corrección aplica a correos nuevos después de recrear el backend.

---

## 2026-08-17 — Google SMTP local y Brevo en producción

### Problema observado

Durante pruebas locales las solicitudes generaban aprobaciones/invitaciones, pero no se recibían correos reales porque el entorno podía quedar en `EMAIL_MODE=console`, modo que únicamente escribe el contenido en logs.

### Decisión

Se formaliza la estrategia de correo por ambiente:

```text
Producción
Frontend: Vercel
Backend:  Render
Correo:   Brevo HTTPS API

Local / development
Frontend: localhost
Backend:  FastAPI/Docker local
Correo:   Gmail/Google Workspace SMTP
```

Configuración SMTP local recomendada:

```env
EMAIL_MODE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
EMAIL_FROM=<CUENTA_GOOGLE>
```

Se mantiene `587 + starttls` como alternativa soportada. Las credenciales reales viven únicamente en `backend/.env` y nunca en Git.

### Diagnóstico

Se incorpora `python -m scripts.test_email --to <correo>` para validar el transporte configurado sin depender de crear una solicitud. Esto separa dos preguntas distintas:

1. ¿Google SMTP/Brevo acepta el correo?
2. ¿El workflow creó correctamente la aprobación o invitación y disparó la notificación?

El estado del workflow sigue siendo persistido aunque el proveedor de correo falle; una futura outbox/retry debe mejorar esa observabilidad sin acoplar la transacción de negocio a la disponibilidad inmediata del proveedor.

---

## 2026-08-17 — Aislamiento del estado de corrección y reparación de request_type

### Incidente refinado

La reproducción manual permitió precisar la causa del bug de correcciones MULTI_QUOTE:

```text
Pestaña SIMPLE activa
→ Corregir MULTI_QUOTE
→ editor SIMPLE ❌

Pestaña MULTI_QUOTE activa
→ Corregir la misma MULTI_QUOTE
→ editor MULTI_QUOTE ✅
```

Esto demostró que el estado React de la pestaña de **creación** estaba sobreviviendo al cambio a modo corrección. La solicitud seleccionada no era la única fuente de verdad del editor.

También se identificó una segunda posibilidad de compatibilidad: filas históricas con `request_type=SIMPLE` aunque exista evidencia durable de múltiples cotizaciones.

### Corrección

Se agregaron defensas independientes:

1. `ExpenseForm` deriva su tipo inicial desde el draft/evidencia durable.
2. `expense-form.jsx` rehidrata al cambiar la solicitud/flujo en corrección, descartando el estado previo de creación.
3. `revision_actions.py` deriva el tipo canónico por `request_type`, estado `QUOTATION_VOTING` o presencia de dos o más `quotation_options`.
4. Alembic `20260817_0003_backfill_multi_quote_request_type.py` repara permanentemente filas legacy inconsistentes.
5. La topología Alembic pasa a `0000 → 0001 → 0002 → 0003`.
6. Se agregó regresión backend para un registro con flag SIMPLE pero evidencia MULTI_QUOTE.

### Regla consolidada

La pestaña SIMPLE/MULTI_QUOTE solo representa intención al **crear una nueva solicitud**. No puede influir en una corrección.

---

## 2026-08-17 — Corrección MULTI_QUOTE preserva el tipo de solicitud

### Incidente detectado

Al seleccionar **Corregir / reenviar** sobre una solicitud en `QUOTATION_VOTING`, el formulario legacy se abría como **Solicitud sencilla**. La causa inicial identificada era que `ExpenseForm` inicializaba `requestType` en `SIMPLE` y, al hidratar un draft, no restauraba correctamente `draft.request_type` ni `draft.quotation_options`.

El endpoint legacy de `resubmit` tampoco reconstruía correctamente una nueva ronda MULTI_QUOTE.

### Decisión funcional

Se establece como invariant:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

`Corregir / reenviar` no puede utilizarse para convertir el tipo de solicitud. Un intento real de cambio del tipo canónico es rechazado por backend con `409 Conflict`.

### Comportamiento MULTI_QUOTE

Una corrección:

- restaura las opciones existentes en la UI;
- conserva soportes existentes;
- mantiene por ahora la cantidad de opciones;
- permite corregir proveedor, monto, URL y observaciones;
- genera un `flow_id` nuevo;
- elimina el estado vigente de votos;
- reemplaza las invitaciones de la ronda;
- conserva eventos históricos;
- resuelve la nueva población mediante `requests:approve`;
- vuelve a `QUOTATION_VOTING`.

### Implementación temporal frontend

Históricamente `ExpenseForm` vivía dentro de `main.jsx` y se aplicaron transforms de compatibilidad para restaurar drafts MULTI_QUOTE. Ese enfoque fue reemplazado posteriormente por el componente modular descrito al inicio de este historial.

### Protección backend y pruebas

Se añadió `api/revision_actions.py` como ruta canónica registrada antes de `expenses.py` legacy, y una suite `TestClient` que verifica preservación/reparación del tipo, evidencia, reinicio de votos/invitaciones y rechazo de MULTI_QUOTE → SIMPLE.

---

## 2026-08-17 — Administrador del sistema con política por ambiente

### Decisión

Se ajusta la política de `TECHNICAL_ADMIN` para separar claramente pruebas y producción.

```text
ENVIRONMENT=production
→ config:manage + requests:read

ENVIRONMENT!=production
→ todos los permisos atómicos activos
```

En local, dev, test, staging y preview la cuenta técnica puede crear, aprobar, votar, cerrar y configurar para validar el producto end-to-end. También puede aparecer en poblaciones de aprobación/votación.

En producción mantiene segregación estricta: no puede crear, aprobar ni cerrar, aunque reciba accidentalmente un permiso financiero mediante rol, grupo o asignación directa.

### Motivo

La restricción productiva era correcta para segregación de funciones, pero impedía utilizar la única cuenta técnica para probar todos los recorridos en ambientes no productivos. Crear cuentas auxiliares obligatorias solo para testing aumentaba fricción sin aportar seguridad real fuera de producción.

La excepción se implementa como política `SystemAccount + ENVIRONMENT`; no se basa en email, nombre, cargo ni `UserRole.ADMIN`.

### Distinción de Settings

Se separan:

- `is_production_environment`: únicamente `ENVIRONMENT=production`, utilizado por autorización funcional;
- `is_production`: producción o runtime alojado que requiere endurecimiento de secretos/CORS.

Así un preview alojado puede conservar seguridad de configuración y al mismo tiempo permitir pruebas funcionales completas.

### Contrato de sesión

El backend pasa a exponer `permission_codes` efectivos y `can_close` en `UserOut`. Los aliases legacy `can_request`, `can_approve`, `can_view`, `can_configure` y `can_close` se derivan del IAM al login y en requests autenticados.

Se documenta como deuda que el frontend monolítico todavía contiene bypasses visuales legacy (`user.role === "ADMIN"`, `canClose={true}`); el backend no confía en ellos.

---

## 2026-08-17 — IAM configurable y segregación de la cuenta técnica

### Decisión

Se abandona `UserRole`/`can_*` como fuente de autorización y se adopta un modelo IAM persistido:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo descriptivo
```

Los cinco permisos iniciales son:

- `requests:read`;
- `requests:create`;
- `requests:approve`;
- `requests:close`;
- `config:manage`.

Los Grupos, Roles, Cargos, membresías y asignaciones son configurables desde la interfaz. Los nombres de estructuras organizacionales no se utilizan en condiciones de autorización.

> Este modelo fue evolucionado posteriormente por Constitución 2.5.0 / Feature 006 para permitir `Cargo → Rol → Permiso` sin autorizar por el nombre del Cargo.

### Cuenta técnica

La cuenta de bootstrap del administrador del sistema queda identificada mediante `system_accounts`. La restricción config/read se aplica específicamente en producción; fuera de producción la política posterior permite acceso completo de prueba.

### Motivo

El administrador técnico de la plataforma no debe formar parte del proceso financiero productivo. Además, el producto debe soportar empresas con estructuras distintas sin despliegues de código.

---

## 2026-08-17 — Hardening FastAPI

### Decisiones

- configuración centralizada con Pydantic Settings;
- nuevos hashes Argon2 mediante `pwdlib`;
- migración transparente de PBKDF2 legacy durante login;
- Alembic como mecanismo de migración;
- DDL/backfills retirados del lifespan;
- `app/main.py` reducido a alias de `app.application`;
- modelos de clasificación movidos fuera del router;
- rutas canónicas de documentos/cierre con `def` porque SQLAlchemy/filesystem son síncronos;
- `FastAPI TestClient` agregado para la matriz IAM;
- application factory y routers canónicos registrados antes de compatibilidad legacy.

### Baseline de base de datos

Al retirar `Base.metadata.create_all()` del startup se detectó que una instalación nueva también necesitaba una ruta determinista de creación. Se añadió `20260817_0000_application_baseline.py`, libre del dominio inmobiliario. La cadena en ese momento era:

```text
0000 application baseline → 0001 IAM foundation → 0002 system accounts → 0003 MULTI_QUOTE request_type repair
```

Feature 006 agrega posteriormente `0004 position role inheritance`.

El baseline conserva tablas existentes cuando se aplica sobre la base actual y crea el esquema base cuando se ejecuta sobre una base limpia. Una prueba de topología falla si aparecen múltiples heads o se rompe esta cadena.

El CI valida código y topología Alembic; antes del despliegue productivo continúa siendo obligatorio ejecutar un smoke test real de las migraciones contra PostgreSQL/Neon de preview con respaldo previo.

### Despliegue Render

Se evaluó `preDeployCommand`. Para mantener compatibilidad con un despliegue económico, el contenedor ejecuta Alembic + bootstrap antes de `uvicorn` mediante `scripts/start.sh`. En múltiples réplicas, la migración debe moverse a una etapa única de release/pre-deploy.

### Compatibilidad de scripts entre Windows y Linux

Durante una ejecución local desde Windows, Docker reportó:

```text
exec /app/scripts/start.sh: no such file or directory
```

Se adoptaron defensas permanentes:

1. `.gitattributes` fuerza `*.sh` a `eol=lf`.
2. `backend/Dockerfile` elimina cualquier `\r` durante el build.
3. Docker Compose espera el `healthcheck` del backend antes de iniciar Nginx.

### Bootstrap Python como módulo

Después de corregir CRLF, la ejecución local expuso:

```text
ModuleNotFoundError: No module named 'app'
```

Se cambió el contrato operativo a:

```text
python -m scripts.bootstrap_admin
```

`scripts` se convirtió en paquete importable y CI verifica el import dentro de la imagen backend.

---

## 2026-08-17 — Consola gráfica de Accesos

Se agrega una consola modular `Configuración → Accesos` para administrar Usuarios, Grupos, Roles, Permisos, Cargos, membresías, roles/permisos directos y permisos efectivos.

La consola consume `/api/iam/*` y no depende de perfiles/cargos hardcodeados del frontend monolítico.

Feature 006 amplía esta consola para administrar también **Roles heredados por Cargo**.

---

## 2026-08-17 — Deuda funcional mantenida explícitamente

Pendientes separados:

- fórmula exacta del motor de aprobación para cumplir la Constitución vigente;
- regla de quorum/empate de votación de cotizaciones;
- edición estructural de una ronda MULTI_QUOTE corregida (agregar/eliminar opciones con evidencia/versionado explícito);
- retiro completo de `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `/api/users` legacy y ramas legacy de `api/expenses.py`;
- modularización restante de `frontend/src/main.jsx`, incluyendo retiro de bypasses visuales de ADMIN y `canClose={true}`;
- retirar los transforms temporales de Vite cuando `main.jsx` importe directamente `ExpenseForm` y `HomeDashboard` modulares.

---

## 2026-08-17 — Documentación como parte del Definition of Done

Se establece que ningún cambio funcional o técnico se considera terminado si deja desactualizadas las fuentes documentales afectadas. Se incorporan Constitución, specs, planes, criterios, README, prompt maestro, docs, HISTORY y CHANGELOG como artefactos gobernados.

---

## 2026-08-17 — Terminología Usuario / Usuarios

El término canónico para el dominio de cuentas es **Usuario / Usuarios**. La UI no debe utilizar **Persona / Personas** como nombre del módulo de administración de cuentas.

---

## 2026-08-17 — Clasificación Área + Categoría

- **Área**: parte de la organización asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Área y Categoría son catálogos independientes y una Categoría puede estar disponible para múltiples Áreas.

Compatibilidad histórica: `expenses.expense_type` → Área; `expenses.expense_subcategory` → Categoría; tablas legacy permanecen como puente temporal.

---

## 2026-08-17 — Retiro del dominio inmobiliario

Se inició el retiro del dominio específico de propiedad horizontal del núcleo de la aplicación. Se retiraron del modelo activo conceptos como `Apartment`, `UserApartment`, `ApartmentChangeEvent`, `OwnershipRole`, `PersonType`, `apartment_number` y endpoints específicos de apartamentos.

La eliminación física de datos legacy requiere respaldo previo.
