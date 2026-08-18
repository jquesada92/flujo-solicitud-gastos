# Historial funcional y técnico

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

`vite.config.js` deja de parchear condiciones internas del formulario. Durante la transición solo importa el componente modular y elimina del bundle la función `ExpenseForm` legacy completa. Se mantiene una `key` por solicitud/flujo para remount.

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
2. Al entrar o cambiar de corrección el formulario recibe una `key` basada en la solicitud/flujo y se remonta, descartando el estado previo de las pestañas.
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

Al retirar `Base.metadata.create_all()` del startup se detectó que una instalación nueva también necesitaba una ruta determinista de creación. Se añadió `20260817_0000_application_baseline.py`, libre del dominio inmobiliario. La cadena actual es:

```text
0000 application baseline → 0001 IAM foundation → 0002 system accounts → 0003 MULTI_QUOTE request_type repair
```

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

---

## 2026-08-17 — Deuda funcional mantenida explícitamente

Pendientes separados:

- fórmula exacta del motor de aprobación para cumplir la Constitución 2.3.3;
- regla de quorum/empate de votación de cotizaciones;
- edición estructural de una ronda MULTI_QUOTE corregida (agregar/eliminar opciones con evidencia/versionado explícito);
- retiro completo de `UserRole`, `can_*`, `/api/users` legacy y ramas legacy de `api/expenses.py`;
- modularización restante de `frontend/src/main.jsx`, incluyendo retiro de bypasses visuales de ADMIN y `canClose={true}`;
- retirar `modularExpenseFormPlugin` cuando `main.jsx` importe directamente el componente modular.

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
