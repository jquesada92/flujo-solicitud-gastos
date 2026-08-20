# Historial funcional y técnico

## 2026-08-19 — Usuarios y Organigrama se consolidan en Accesos

### Problema observado

La Configuración tenía tres superficies solapadas para identidad y estructura: **Usuarios/Personas**, **Organigrama** y **Accesos**. Esto duplicaba navegación y permitía que el mismo dominio administrativo pareciera tener más de una fuente de verdad.

Además, después de integrar la consola IAM con el shell principal, la barra superior permanecía visible pero podía no abandonar Accesos al pulsar Inicio/Solicitudes/Facturas/Auditoría/Salir. La causa era que Accesos se monta mediante `#access-management`: React podía cambiar la pestaña subyacente mientras el hash mantenía la consola montada. El caso era especialmente visible al volver a la misma pestaña desde la que se abrió Accesos.

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

Accesos se convierte en la única superficie para:

```text
Usuarios
Grupos
Roles
Permisos
Cargos/Posiciones
Asignaciones
Permisos efectivos/fuentes
```

El modelo persistido de Usuario/Cargo/Grupo/Rol/Permiso no se elimina; la consolidación retira duplicidad de UX y navegación.

Para `config:read`, la misma consola se usa en modo solo lectura. `areas:manage` continúa independiente y `config:manage` permanece system-only.

### Navegación desde Accesos

Se agrega `frontend/src/access-navigation-bridge.js`, cargado antes de `main.jsx`.

El bridge escucha la topbar en capture phase y, cuando Accesos está activo, elimina `#access-management` antes de que el shell procese el destino. Así funcionan en un solo clic:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

Abrir/cerrar únicamente el dropdown **Configuración** no abandona Accesos.

Se agrega `test_access_navigation_bridge.py` como contrato de regresión. La validación manual en Docker continúa como gate explícito del checklist hasta ser ejecutada.

### Sincronización con main y clasificación

La rama de Feature 011 se sincronizó con `main` antes de continuar. Esto incorporó Alembic `20260819_0008_expense_area_category_columns.py` y mantuvo alineada la base local que ya estaba en revisión `0008`.

El contrato vigente queda:

```text
expense_area
expense_category
```

`expense_type` / `expense_subcategory` permanecen únicamente como aliases de compatibilidad transitoria.

### Gobierno documental

El cambio sincroniza:

- Constitución 2.9.0;
- Feature 011 (`spec.md`, `plan.md`, checklist);
- README;
- prompt maestro;
- CONFIGURATION_ACCESS;
- IAM_MODEL;
- CLASSIFICATION_MODEL;
- TERMINOLOGY;
- FASTAPI_ARCHITECTURE;
- índice de docs;
- política documental;
- HISTORY;
- CHANGELOG.

---

## 2026-08-19 — Asignación Área-Categoría oculta categorías inactivas

### Problema observado

La tarjeta **Categorías por área** mostraba también categorías inactivas. Aunque esa visibilidad servía para inspección técnica, mezclaba dos responsabilidades distintas: mantenimiento del catálogo y selección de opciones realmente disponibles para asignar a un Área.

### Decisión funcional

Se separa explícitamente la visibilidad:

```text
Maestro de Categorías
→ activas + inactivas
→ mantenimiento / reactivación

Categorías por área
→ solo active=true
→ asignación operativa
```

Desactivar una categoría no elimina sus relaciones `expense_area_categories` ni altera solicitudes históricas. Mientras esté inactiva deja de aparecer en la tarjeta de asignación. Si se necesita editar nuevamente esa relación, se reactiva primero desde el Maestro de Categorías.

Los checkboxes de la tarjeta siguen siendo estado local: la relación solo cambia al pulsar **Guardar** por fila. El contador usa la misma población activa visible para evitar discrepancias entre número mostrado y filas disponibles.

### Implementación y protección

- `classification-admin.js` centraliza la población visible en `visibleAssignmentCategories()`.
- la tabla, el contador, el control de cambios pendientes y el estado vacío usan únicamente categorías activas.
- `test_frontend_classification_admin_contract.py` protege esta regla.
- Feature 009, checklist y `docs/CLASSIFICATION_MODEL.md` quedan sincronizados con el comportamiento.

---

## 2026-08-18 — Notificaciones de Cargo y permisos efectivos

### Necesidad

Al crear usuarios o modificar su Cargo, el usuario debía recibir una comunicación explícita de su posición organizacional y de los permisos efectivos que realmente tiene en el sistema.

### Decisión funcional

Se incorpora Feature 010:

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

El correo usa `UserPosition → Position` y `effective_permission_codes()` como fuentes de verdad. No usa `UserRole`, `title` ni `can_*` legacy.

Guardar el mismo conjunto de `position_ids` no genera correo duplicado.

### Semántica de entrega

La invitación inicial conserva su comportamiento obligatorio. El cambio de Cargo adopta la misma garantía: si el proveedor de correo falla, la transacción se revierte y el endpoint devuelve 502.

Esto es distinto de algunos correos de workflow, que actualmente pueden ser best-effort. La deuda futura sigue siendo una outbox/reintentos persistentes.

### Código y pruebas

- `email_service.send_user_invitation()` ahora recibe Cargo(s) y permisos efectivos.
- se agrega `send_user_access_updated()` sin contraseña temporal.
- `iam_users.py` detecta cambios reales de `position_ids`, recalcula el acceso y notifica.
- `test_user_access_notifications.py` cubre creación, cambio real, no duplicación, rollback por fallo de correo y contenido HTML/texto.
- no requiere nueva migración; Constitución permanece **2.8.0** para Feature 010.

---

## 2026-08-18 — Hardening del bridge Vite de Accesos

Durante la validación local de Feature 009 con Vite 8.2.1 en Windows, `npm run build` falló con:

```text
Legacy main.jsx extraction could not find: system-only access menu injection
```

La regla funcional de autorización era correcta. El fallo estaba en `protectAccessMenuInjection()`: el bridge temporal buscaba mediante `replaceRequired()` una secuencia multilinea exacta dentro de `iam-admin.jsx`, por lo que un cambio de formato/transformación impedía localizar el guard de `injectAccessMenu()`.

Decisión técnica:

- mantener la frontera funcional de Constitución 2.8.0 sin cambios en ese momento;
- reemplazar la coincidencia multilinea literal por una regex estructural tolerante a whitespace y finales LF/CRLF;
- exigir exactamente una coincidencia del guard para conservar fail-fast;
- reforzar `test_frontend_configuration_access.py`;
- mantener `npm run build` como gate local.

---

## 2026-08-18 — Configuración técnica se separa de Gestión de Áreas

### Problema observado

El menú **Configuración** mostraba Usuarios / Organigrama / Accesos a actores que no debían administrar técnicamente la plataforma. Al mismo tiempo, la gestión de Áreas dependía de `config:manage`.

### Decisión funcional

Se incorporó `areas:manage` como permiso organizacional configurable y `config:manage` pasó a ser system-only. Alembic `0006` creó el Rol neutral:

```text
Gestor de áreas → areas:manage
```

sin asignarlo a ningún Grupo/Cargo por nombre.

Esta arquitectura evolucionó posteriormente con `config:read` (`0007`) y con Feature 011, que consolidó Usuarios/Organigrama dentro de Accesos.

---

## 2026-08-18 — Hardening del bridge Vite de delegación de cierre

Durante la validación local de Feature 008, `npm run build` falló porque el bridge temporal buscaba una secuencia con salto de línea e indentación exactos dentro de `main.jsx`.

Se reemplazó la coincidencia literal por un ancla regex tolerante a LF/CRLF y whitespace variable, exigiendo una sola coincidencia y agregando regresión en `test_frontend_closure_contract.py`.

---

## 2026-08-18 — Cierre/factura pasa a propiedad por solicitud con delegación

La autoridad de cierre/factura dejó de ser un permiso global:

```text
solicitante original
OR Administrador del sistema
OR delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` quedó como registro histórico inactivo. Se creó `expense_closure_delegations` con historial de creación/revocación y una sola delegación activa por solicitud.

`financial_actions.py` usa `can_manage_closure()` y `tracking.py` expone `can_close` / `can_delegate_close`.

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

Migración `0004` creó `position_roles` e importó una sola vez configuración legacy a relaciones IAM. El nombre del Cargo nunca autoriza.

---

## 2026-08-18 — Dashboard: acciones contextuales y KPIs informativos

Todo usuario activo obtiene baseline `requests:read` para Inicio/Solicitudes y seguimiento compartido. Las filas de **Acciones pendientes** abren un modal que revalida `/my-actions`; los KPIs superiores son informativos.

Códigos contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

---

## 2026-08-17 — Seguimiento universal y cancelación por recurso

`requests:read` pasó a baseline no revocable para usuarios activos. `GET /api/expenses` dejó de filtrar por solicitante.

Cancelación quedó reservada a:

```text
solicitante original OR system_accounts
```

con `can_cancel` calculado por backend.

---

## 2026-08-17 — Corrección MULTI_QUOTE modular y preservación de tipo

Se corrigió el bug donde una MULTI_QUOTE en corrección podía renderizar el formulario SIMPLE según la pestaña de creación activa.

Regla:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

`revision_actions.py` valida backend, la ronda MULTI_QUOTE recibe nuevo `flow_id`, votos/invitaciones se reinician y evidencia se conserva. Migración `0003` repara filas históricas inconsistentes.

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

Se incorporaron Pydantic Settings, Argon2 con compatibilidad PBKDF2, application factory, Alembic, baseline `0000`, IAM `0001`, system accounts `0002`, routers/servicios canónicos, TestClient y entrypoint Docker:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

La cuenta técnica se identifica por `system_accounts`; producción se rige por `ENVIRONMENT=production`.

---

## 2026-08-17 — Retiro de dominio inmobiliario y normalización

Se retiraron del núcleo activo conceptos como Apartment/UserApartment/ApartmentChangeEvent/OwnershipRole/PersonType/apartment_number. El producto pasó a terminología neutral y clasificación **Área + Categoría**.

Los nombres organizacionales son datos configurables, nunca condiciones de autorización runtime.

---

## Deuda explícita vigente

- `UserRole`, `users.title`, `can_*`, `AccessProfile`, `BOARD_CODES`, `/api/users` legacy y `requests:close` inactivo permanecen físicamente como compatibilidad.
- vistas internas `people` / `organization` pueden permanecer temporalmente, pero no son navegables ni autoridad.
- `main.jsx` sigue monolítico en partes; Vite mantiene bridges transitorios.
- `expense_type` / `expense_subcategory` pueden existir como aliases transitorios, pero la persistencia/contrato vigente es `expense_area` / `expense_category`.
- fórmula completa de quorum/mayoría APPROVED/REJECTED y empate MULTI_QUOTE siguen como deuda separada.
- edición estructural de opciones MULTI_QUOTE y outbox/retry persistente de correo siguen pendientes.
