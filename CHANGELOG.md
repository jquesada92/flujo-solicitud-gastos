# Changelog

## 2026-08-20 — Feature 012: Neon `ph_torre_delta` aislado por ambiente

### Added
- Feature 012 con `spec.md`, `plan.md` y checklist de aceptación para aislamiento de schema Neon.
- contrato central `DATABASE_SCHEMA=ph_torre_delta` para SQLAlchemy/Alembic.

### Changed
- Constitución actualizada a **2.10.0**.
- topología canónica de persistencia: `main → PROD`, `dev → DEV`, base `ph_torre_delta`, schema `ph_torre_delta`.
- DEV y PROD se definen como instalaciones limpias creadas desde cero mediante Alembic.
- `ph_torre_delta.alembic_version` debe ser la única tabla de versión usada por la instalación vigente.

### Prohibited
- no mover, copiar, clonar ni renombrar tablas desde `flujos_de_aprobacion`, `public` u otros schemas legacy.
- no usar `public` como schema de aplicación.
- no usar `alembic stamp` para reutilizar estado Alembic de schemas previos.

### Documentation
- Constitución, Feature 012, README, prompt maestro, HISTORY y CHANGELOG quedan sincronizados.

---

## 2026-08-19 — Feature 011: Accesos como única superficie de Usuarios/IAM

### Changed
- **Usuarios/Personas** y **Organigrama** dejan de ser entradas independientes de Configuración.
- **Configuración → Accesos** pasa a ser la única superficie para Usuarios, Grupos, Roles, Permisos, Cargos/Posiciones, asignaciones y permisos efectivos.
- actores con `config:read` consultan la misma experiencia de Accesos en modo solo lectura.
- `areas:manage` continúa separado y `config:manage` permanece system-only.
- Constitución actualizada a **2.9.0**.

### Fixed
- la topbar vuelve a navegar correctamente mientras `#access-management` está activo.
- `frontend/src/access-navigation-bridge.js` elimina el hash en capture phase antes de que el shell procese Inicio/Solicitudes/Facturas/Auditoría/Salir u otra pantalla de Configuración.
- el caso donde el destino ya era la pestaña React subyacente también cierra Accesos.
- abrir/cerrar únicamente el dropdown **Configuración** no abandona la consola.

### Testing
- se agrega `backend/tests/test_access_navigation_bridge.py`.
- la validación manual de navegación completa en Docker permanece como gate explícito hasta ejecutarse localmente.

### Documentation
- Feature 011, Constitución, README, prompt maestro, CONFIGURATION_ACCESS, IAM_MODEL, CLASSIFICATION_MODEL, TERMINOLOGY, FASTAPI_ARCHITECTURE, índice docs, política documental e HISTORY quedan sincronizados.

---

## 2026-08-19 — Contrato canónico `expense_area` / `expense_category`

### Changed
- el contrato nuevo de solicitud, API, ORM y persistencia usa `expense_area` y `expense_category`.
- `expense_type` / `expense_subcategory` quedan únicamente como aliases legacy de compatibilidad.
- la rama de Feature 011 se sincroniza con `main` antes de continuar.

### Migrations
- Alembic `20260819_0008_expense_area_category_columns.py` renombra las columnas físicas de `expenses` preservando datos existentes.
- cadena vigente: `0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008`.
- una revisión Alembic ausente debe resolverse sincronizando la cadena correcta, no ocultándose con `stamp`.

---

## 2026-08-19 — Configuración de solo lectura (`config:read`)

### Added
- permiso `config:read` y Rol neutral **Visor de configuración** mediante migración `0007`.

### Changed
- `config:read` permite consultar Configuración sin conceder mutaciones.
- `config:manage` sigue reservado a `system_accounts`.
- `areas:manage` sigue siendo el permiso dedicado para mutar Área + Categoría.

---

## 2026-08-19 — Consola de Accesos integrada al shell principal

### Changed
- Accesos conserva visible la navegación principal del producto.
- se retira el botón independiente **Volver**; la salida se realiza mediante navegación estándar.
- la acción de refresco pasa a llamarse **Recargar**.
- layout, tarjetas, listas y badges de IAM se alinean con el shell principal.
- **Guardar cambios** de Roles calcula estado `dirty` real.

### Testing
- `test_frontend_configuration_access.py` protege topbar, Recargar, overflow y estado de persistencia.

---

## 2026-08-19 — Asignación Área-Categoría muestra solo categorías activas

### Changed
- **Categorías por área** muestra únicamente categorías activas.
- el Maestro de Categorías conserva activas e inactivas para mantenimiento/reactivación.
- cambios de asignación se persisten solo al pulsar **Guardar**.

### Behavior
- desactivar una categoría no elimina relaciones persistidas ni modifica solicitudes históricas.

### Testing / Docs
- `test_frontend_classification_admin_contract.py` protege filtro, contador y guardado explícito.

---

## 2026-08-18 — Notificaciones de Cargo y permisos efectivos

### Added
- `send_user_access_updated()` para cambios reales de Cargo.
- resumen IAM reutilizable de Cargo(s) + permisos efectivos.
- Feature 010 y `test_user_access_notifications.py`.

### Changed
- invitación inicial incluye Cargo(s) y permisos efectivos.
- cambio real de `position_ids` recalcula y notifica.
- guardar el mismo Cargo no duplica correo.
- fuentes: `effective_permission_codes()` y `UserPosition → Position`.

### Reliability
- fallo de notificación obligatoria revierte la transacción.

---

## 2026-08-18 — Configuración técnica system-only y Gestión de Áreas delegable

### Added
- `areas:manage`.
- Rol neutral **Gestor de áreas**.
- `UserOut.is_system_account`.
- Alembic `0006`.

### Changed
- `config:manage` pasa a system-only.
- `/api/areas` usa `areas:manage` para mutaciones.
- nombres de Grupos/Cargos no participan en autorización.
- Constitución **2.8.0**.

### Fixed
- hardening del bridge Vite de Accesos con regex estructural tolerante a whitespace/LF/CRLF y fail-fast por unicidad.

---

## 2026-08-18 — Cierre/factura por solicitante, Admin o delegación

### Added
- `ExpenseClosureDelegation`.
- `closure_service.py` y API GET/PUT/DELETE por solicitud.
- `ExpenseOut.can_close` y `can_delegate_close`.
- `frontend/src/closure-delegation.jsx`.
- Alembic `0005`.
- Feature 008 y pruebas asociadas.

### Changed
- cierre/factura pasa a autorización por recurso:

```text
solicitante original
OR Administrador del sistema
OR delegado activo
```

- `requests:close` deja de ser autoridad runtime.
- Constitución **2.7.0**.

---

## 2026-08-18 — Propiedad de corrección y Enviar a revisión

### Added
- `ExpenseOut.can_correct`.
- Feature 007.

### Changed
- corregir/reenviar solo para solicitante original o `system_accounts`.
- aprobador usa **Enviar a revisión** con comentario.
- `REVISION_REQUESTED` interrumpe inmediatamente y genera `CORRECT_REQUEST` para solicitante.
- Constitución **2.6.0**.

---

## 2026-08-18 — Permisos heredados por Cargo y Grupo

### Added
- `position_roles`, API/UI de Roles heredados por Cargo.
- `users_with_permission()` reconoce Cargo→Rol.
- migración `0004` importa configuración legacy a IAM.
- Feature 006.

### Changed
- Grupo→Rol→Permiso y Cargo→Rol→Permiso sin autorización por nombres.
- Constitución **2.5.0**.

---

## 2026-08-18 — Dashboard contextual y KPIs informativos

### Added
- `pending_action_service.py`, `my_actions.py`, `home-dashboard.jsx` y modal contextual.

### Changed
- filas de Acciones pendientes son interactivas; KPIs superiores son informativos.
- todo usuario activo recibe baseline `requests:read`.

---

## 2026-08-17 — Seguimiento universal y cancelación por recurso

### Added
- `tracking.py`, `cancellation_actions.py`, `ExpenseOut.can_cancel`.

### Changed
- usuarios activos pueden consultar solicitudes ajenas.
- cancelación solo requester/Admin del sistema.

---

## 2026-08-17 — Corrección MULTI_QUOTE preserva tipo y evidencia

### Added
- `expense-form.jsx`, `revision_actions.py`, migración `0003`.

### Fixed
- `SIMPLE → SIMPLE` y `MULTI_QUOTE → MULTI_QUOTE` durante corrección.
- ronda corregida reinicia votos/invitaciones con nuevo `flow_id` y conserva soportes.

---

## 2026-08-17 — Correo por ambiente

### Changed
- Producción: Brevo HTTPS API en Render.
- Local: Gmail/Workspace SMTP.

### Added
- `python -m scripts.test_email`.

---

## 2026-08-17 — IAM configurable + FastAPI hardening

### Added
- Pydantic Settings, Argon2/PBKDF2 compatibility, application factory, Alembic `0000/0001/0002`, system accounts, consola IAM y TestClient.

### Changed
- autorización runtime por permisos efectivos/políticas.
- producción y no-producción separadas por `ENVIRONMENT`.

---

## 2026-08-17 — Normalización de dominio

### Changed
- clasificación funcional Área + Categoría.
- terminología neutral Usuario/Grupo/Rol/Permiso/Cargo.

### Removed / Retired
- dominio inmobiliario activo.
- Persona/Personas como módulo canónico.
- Subárea como segundo nivel funcional.

---

## Compatibility / Technical debt

Permanecen temporalmente sin autoridad o arquitectura objetivo:

- `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `users.title`, `/api/users` legacy;
- `requests:close` inactivo;
- vistas internas `people` / `organization` no navegables;
- `expense_type` / `expense_subcategory` como aliases transitorios;
- `main.jsx`, `domain-normalization.js` y bridges Vite;
- schemas/tablas legacy fuera de `ph_torre_delta`, sin autoridad runtime.

Pendientes separados: fórmula completa de mayoría APPROVED/REJECTED, empate MULTI_QUOTE, edición estructural de opciones y outbox/retry persistente.
