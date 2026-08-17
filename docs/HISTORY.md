# Historial funcional y técnico

## 2026-08-17 — Corrección MULTI_QUOTE preserva el tipo de solicitud

### Incidente detectado

Al seleccionar **Corregir / reenviar** sobre una solicitud en `QUOTATION_VOTING`, el formulario legacy se abría como **Solicitud sencilla**. La causa era que `ExpenseForm` inicializaba `requestType` en `SIMPLE` y, al hidratar un draft, no restauraba `draft.request_type` ni `draft.quotation_options`.

El endpoint legacy de `resubmit` tampoco reconstruía correctamente una nueva ronda MULTI_QUOTE.

### Decisión funcional

Se establece como invariant:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

`Corregir / reenviar` no puede utilizarse para convertir el tipo de solicitud. Un intento de cambio de `request_type` es rechazado por backend con `409 Conflict`.

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

Mientras `ExpenseForm` siga dentro de `main.jsx`, `vite.config.js` aplica un transform de compatibilidad durante dev/build para restaurar correctamente el draft MULTI_QUOTE. El build falla si el transform no encuentra los fragmentos legacy esperados.

Este transform no es arquitectura objetivo y debe retirarse al modularizar `ExpenseForm`.

### Protección backend y pruebas

Se añadió `api/revision_actions.py` como ruta canónica registrada antes de `expenses.py` legacy, y una suite `TestClient` que verifica preservación del tipo, evidencia, reinicio de votos/invitaciones y rechazo de MULTI_QUOTE → SIMPLE.

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

Al retirar `Base.metadata.create_all()` del startup se detectó que una instalación nueva también necesitaba una ruta determinista de creación. Se añadió `20260817_0000_application_baseline.py`, libre del dominio inmobiliario, y se dejó una única cadena Alembic:

```text
0000 application baseline → 0001 IAM foundation → 0002 system accounts
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

- fórmula exacta del motor de aprobación para cumplir la Constitución 2.3.1;
- regla de quorum/empate de votación de cotizaciones;
- edición estructural de una ronda MULTI_QUOTE corregida (agregar/eliminar opciones con evidencia/versionado explícito);
- retiro completo de `UserRole`, `can_*`, `/api/users` legacy y ramas legacy de `api/expenses.py`;
- modularización completa de `frontend/src/main.jsx`, incluyendo retiro de bypasses visuales de ADMIN, `canClose={true}` y del transform temporal de correcciones.

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
