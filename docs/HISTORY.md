# Historial funcional y técnico

## 2026-08-20 — Nueva base `ph_torre_delta` con schema `administracion`

### Contexto

Se decidió reiniciar el ciclo de vida físico de la base de datos. No se requiere conservar tablas, datos ni el historial Alembic utilizado por instalaciones anteriores.

La aplicación mantiene su modelo funcional actual, pero la nueva instalación nace limpia y reproducible.

### Decisión técnica

Feature 012 y Constitución **2.10.0** establecen:

```text
DEV
DATABASE_URL  → Neon / database ph_torre_delta
DATABASE_SCHEMA=administracion

PROD / Render
DATABASE_URL  → Neon / database ph_torre_delta
DATABASE_SCHEMA=administracion
```

La base y el schema cumplen responsabilidades distintas:

```text
Database: ph_torre_delta
Schema:   administracion
```

`public` no es schema de aplicación ni fallback.

### Reinicio de Alembic

La historia operativa anterior:

```text
0000 → 0001 → ... → 0008
```

se retira de la rama vigente.

La nueva historia comienza en:

```text
20260820_0001_initial_schema.py
```

con `down_revision = None`.

Esta revisión es una baseline limpia, no una migración de la base anterior. Crea directamente el modelo físico actual y no ejecuta:

- copia de tablas;
- `ALTER ... SET SCHEMA`;
- renombres para adaptar columnas históricas;
- backfills de datos;
- importación de usuarios/asignaciones anteriores;
- `alembic stamp`.

`expense_area` y `expense_category` nacen con sus nombres canónicos desde la baseline.

### Protección contra reutilización accidental

Antes de crear las tablas, la baseline inspecciona `administracion`. Si encuentra tablas de aplicación preexistentes, aborta. La única excepción permitida es `alembic_version`, que Alembic puede crear antes de ejecutar la revisión.

Esto convierte el requisito de “crear desde cero” en una garantía técnica.

### SQLAlchemy y Alembic schema-aware

`DATABASE_SCHEMA` se incorpora a Settings y se valida como identificador PostgreSQL seguro. Se rechazan schemas del sistema como `public`, `information_schema` y `pg_*`.

En PostgreSQL:

- el metadata ORM usa el schema configurado;
- la conexión limita `search_path` al schema de aplicación;
- Alembic crea el schema si no existe;
- `version_table_schema` coloca `alembic_version` dentro de `administracion`;
- discovery/autogenerate se restringe al mismo schema.

SQLite continúa sin schema para las pruebas unitarias.

### Bootstrap IAM

La baseline crea la estructura IAM actual y las semillas mínimas:

```text
Permisos activos
- requests:read
- requests:create
- requests:approve
- areas:manage
- config:read
- config:manage

Registro legacy inactivo
- requests:close

Roles iniciales
- system-administrator
- area-manager
- configuration-viewer
```

Después de la baseline, `python -m scripts.bootstrap_admin` crea/reconcilia la cuenta técnica de la nueva instalación.

No se importan usuarios, grupos, cargos ni asignaciones de una base anterior.

### Auditoría

La nueva baseline mantiene la protección append-only de las tablas de eventos. La función y los triggers PostgreSQL también se crean dentro de `administracion`.

### Evolución futura

Una vez desplegada `20260820_0001` en un ambiente persistente, queda congelada. Cambios posteriores deben crear nuevas revisiones Alembic:

```text
20260820_0001_initial_schema
        ↓
0002_nuevo_cambio
        ↓
0003_otro_cambio
```

### Gobierno documental

El cambio sincroniza:

- Constitución 2.10.0;
- Feature 012 (`spec.md`, `plan.md`, checklist);
- README;
- prompt maestro;
- ENV examples;
- pruebas de contrato;
- HISTORY;
- CHANGELOG.

> Las menciones de migraciones `0000 → 0008` en eventos históricos posteriores a esta sección describen cómo evolucionó el producto antes del reset. Ya no son la cadena operativa vigente.

---

## 2026-08-19 — Usuarios y Organigrama se consolidan en Accesos

### Problema observado

La Configuración tenía tres superficies solapadas para identidad y estructura: **Usuarios/Personas**, **Organigrama** y **Accesos**. Esto duplicaba navegación y permitía que el mismo dominio administrativo pareciera tener más de una fuente de verdad.

Además, después de integrar la consola IAM con el shell principal, la barra superior permanecía visible pero podía no abandonar Accesos al pulsar Inicio/Solicitudes/Facturas/Auditoría/Salir. La causa era que Accesos se monta mediante `#access-management`: React podía cambiar la pestaña subyacente mientras el hash mantenía la consola montada.

### Decisión funcional

Se adopta Feature 011 y Constitución **2.9.0**:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / configuración técnica
```

**Usuarios/Personas y Organigrama dejan de ser pantallas independientes.**

Accesos se convierte en la única superficie para Usuarios, Grupos, Roles, Permisos, Cargos/Posiciones, asignaciones y permisos efectivos.

Para `config:read`, la misma consola se usa en modo solo lectura. `areas:manage` continúa independiente y `config:manage` permanece system-only.

### Navegación desde Accesos

`frontend/src/access-navigation-bridge.js`, cargado antes de `main.jsx`, retira `#access-management` antes de que el shell procese el destino.

Así funcionan en un solo clic:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

Abrir/cerrar únicamente el dropdown **Configuración** no abandona Accesos.

### Clasificación

En esta etapa se consolidó el contrato funcional:

```text
expense_area
expense_category
```

La cadena de migraciones que entonces preservaba datos quedó posteriormente reemplazada por la baseline limpia de Feature 012.

---

## 2026-08-19 — Asignación Área-Categoría oculta categorías inactivas

La tarjeta **Categorías por área** muestra únicamente categorías activas, mientras el Maestro de Categorías conserva activas e inactivas para mantenimiento/reactivación.

Desactivar una categoría no elimina relaciones ni altera solicitudes existentes. Los cambios de asignación solo se persisten al pulsar **Guardar**.

`test_frontend_classification_admin_contract.py` protege esta regla.

---

## 2026-08-18 — Notificaciones de Cargo y permisos efectivos

Al crear usuarios o modificar realmente su Cargo, el usuario recibe comunicación explícita de su posición organizacional y permisos efectivos.

```text
Creación de usuario activo
→ correo de invitación
→ contraseña temporal
→ Cargo(s)
→ permisos efectivos

Cambio real de Cargo
→ recalcular permisos efectivos
→ correo Actualización de cargo y permisos
```

Las fuentes de verdad son `UserPosition → Position` y `effective_permission_codes()`. Guardar el mismo conjunto de `position_ids` no genera correo duplicado.

---

## 2026-08-18 — Configuración técnica se separa de Gestión de Áreas

Se incorporó `areas:manage` como permiso organizacional configurable y `config:manage` pasó a ser system-only.

El nombre de un Grupo/Cargo no concede autorización. El rol neutral **Gestor de áreas** se conserva en la nueva baseline, sin asignaciones organizacionales automáticas.

---

## 2026-08-18 — Cierre/factura pasa a propiedad por solicitud con delegación

La autoridad de cierre/factura dejó de ser un permiso global:

```text
solicitante original
OR Administrador del sistema
OR delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` quedó como registro histórico inactivo. Se creó `expense_closure_delegations` con historial de creación/revocación y una sola delegación activa por solicitud.

---

## 2026-08-18 — Propiedad de corrección y handoff de revisión

Se separaron dos responsabilidades:

```text
Aprobador detecta problema
→ Enviar a revisión + comentario
→ NEEDS_REVISION inmediato
→ otros PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST

Solicitante original OR Administrador del sistema
→ Corregir / reenviar
```

`requests:create`, `requests:approve`, Cargo, Rol o Grupo no conceden edición de solicitud ajena.

---

## 2026-08-18 — Cargo y Grupo pasan a fuentes configurables de Roles

Se evolucionó el modelo IAM a:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
```

El nombre del Cargo nunca autoriza. La nueva baseline conserva la estructura final sin importar configuraciones organizacionales históricas.

---

## 2026-08-18 — Dashboard: acciones contextuales y KPIs informativos

Todo usuario activo obtiene baseline `requests:read` para Inicio/Solicitudes y seguimiento compartido.

Códigos contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

---

## 2026-08-17 — Seguimiento universal y cancelación por recurso

`requests:read` pasó a baseline no revocable para usuarios activos. `GET /api/expenses` dejó de filtrar exclusivamente por solicitante.

Cancelación quedó reservada a:

```text
solicitante original OR system_accounts
```

---

## 2026-08-17 — Corrección MULTI_QUOTE modular y preservación de tipo

Regla:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

La ronda MULTI_QUOTE corregida recibe nuevo `flow_id`; votos/invitaciones se reinician y la evidencia del flujo vigente se conserva según el contrato funcional.

---

## 2026-08-17 — Correo por ambiente

Se formalizó:

```text
Producción → Render + Brevo HTTPS API
Local      → Docker/FastAPI + Gmail/Workspace SMTP
```

Se agregó `python -m scripts.test_email` para diagnosticar transporte sin depender del workflow.

---

## 2026-08-17 — FastAPI hardening e IAM configurable

Se incorporaron Pydantic Settings, Argon2 con compatibilidad PBKDF2, application factory, Alembic, system accounts, routers/servicios canónicos, TestClient y entrypoint Docker.

La cuenta técnica se identifica por `system_accounts`; producción se rige por `ENVIRONMENT=production`.

---

## 2026-08-17 — Retiro de dominio inmobiliario y normalización

Se retiraron del núcleo activo conceptos como Apartment/UserApartment/ApartmentChangeEvent/OwnershipRole/PersonType/apartment_number. El producto pasó a terminología neutral y clasificación **Área + Categoría**.

Los nombres organizacionales son datos configurables, nunca condiciones de autorización runtime.

---

## Deuda explícita vigente

- `UserRole`, `users.title`, `can_*`, `AccessProfile`, `BOARD_CODES`, `/api/users` legacy y `requests:close` inactivo permanecen físicamente como compatibilidad de código.
- vistas internas `people` / `organization` pueden permanecer temporalmente, pero no son navegables ni autoridad.
- `main.jsx` sigue monolítico en partes; Vite mantiene bridges transitorios.
- `expense_type` / `expense_subcategory` pueden existir como aliases internos transitorios; la persistencia vigente usa `expense_area` / `expense_category`.
- fórmula completa de quorum/mayoría APPROVED/REJECTED y empate MULTI_QUOTE siguen como deuda separada.
- edición estructural de opciones MULTI_QUOTE y outbox/retry persistente de correo siguen pendientes.

La compatibilidad de código no implica conservar una base previa. La persistencia vigente nace desde `20260820_0001` en `ph_torre_delta.administracion`.
