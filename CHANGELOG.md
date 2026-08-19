# Changelog

## 2026-08-18 — Notificaciones de Cargo y permisos efectivos

### Added
- `send_user_access_updated()` para notificar cambios reales de Cargo.
- resumen IAM reutilizable de Cargo(s) + permisos efectivos en `iam_users.py`.
- Feature 010 y `test_user_access_notifications.py`.

### Changed
- la invitación inicial con contraseña temporal ahora incluye Cargo(s) y permisos efectivos.
- el cambio real de `position_ids` recalcula permisos efectivos y envía **Actualización de cargo y permisos**.
- guardar el mismo conjunto de Cargos no envía correo duplicado.
- los correos usan `effective_permission_codes()` y `UserPosition → Position`; no usan `UserRole`, `title` ni `can_*` legacy.

### Reliability
- si falla la invitación inicial, la creación no se confirma, conservando el comportamiento vigente.
- si falla la notificación de cambio de Cargo, la transacción se revierte y el endpoint devuelve 502.
- no se añade una migración Alembic; la cadena permanece hasta `0006`.

### Testing
- invitación incluye Cargo/permisos heredados.
- cambio Vocal → Tesorero recalcula y notifica `requests:approve`.
- guardar el mismo Cargo no duplica correo.
- fallo de transporte revierte el cambio.
- plantillas texto/HTML contienen Cargo y códigos de permiso.

---

## 2026-08-18 — Configuración técnica system-only y Gestión de Áreas delegable

### Added
- permiso atómico `areas:manage`.
- Rol neutral `area-manager / Gestor de áreas`.
- `UserOut.is_system_account` para UX basada en identidad persistida.
- Alembic `20260818_0006_area_management_permission.py`.
- Feature 009 y `docs/CONFIGURATION_ACCESS.md`.
- `test_frontend_configuration_access.py`.

### Changed
- `config:manage` pasa a ser una capacidad **system-only**: usuarios ordinarios no la reciben efectivamente por permiso directo, Rol, Grupo o Cargo.
- producción del System Admin queda `requests:read + areas:manage + config:manage`.
- `/api/areas` usa `areas:manage` para mutaciones y consulta de inactivos.
- menú de Configuración usa `is_system_account` para Usuarios/Organigrama/Accesos/Reglas/Auditoría y `areas:manage` para Áreas.
- `iam-admin.jsx` solo inyecta **Accesos** en menú marcado como System Admin.
- Constitución actualizada a **2.8.0**.

### Fixed
- El bridge temporal de Vite que protege la inyección de **Accesos** deja de depender de una coincidencia multilinea literal de `iam-admin.jsx`.
- `protectAccessMenuInjection()` usa una regex estructural tolerante a whitespace y LF/CRLF, exige exactamente una coincidencia y conserva fail-fast ante código ambiguo.
- Se corrige el build local de Vite 8.2.1 que fallaba con `Legacy main.jsx extraction could not find: system-only access menu injection`; el rerun local permanece como gate de aceptación hasta confirmación del desarrollador.

### Security
- asignaciones legacy de `config:manage` a usuarios ordinarios dejan de producir permiso efectivo.
- nombres de Grupos/Cargos como Administración o Junta Directiva no participan en autorización.
- `0006` no asigna automáticamente `Gestor de áreas` a ningún nombre organizacional.
- el bridge remueve cualquier botón **Accesos** de un menú no marcado `data-system-admin=true`.

### Migrations
- Cadena actual: `0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006`.
- `0006` crea/activa `areas:manage`, crea el Rol neutral y actualiza la descripción de `config:manage` como administración técnica.

### Testing
- usuario ordinario con `areas:manage` puede administrar Áreas y sigue bloqueado de IAM técnico.
- usuario ordinario con `config:manage` legacy sigue bloqueado.
- login/`/auth/me` distinguen `is_system_account`.
- contratos frontend protegen separación de menú y Accesos system-only.
- `test_frontend_configuration_access.py` verifica que el bridge use `matchAll`, `\s*`, unicidad y no vuelva a `replaceRequired()` para el guard de inyección.

---

## 2026-08-18 — Cierre/factura por solicitante, Admin o delegación

### Added
- `ExpenseClosureDelegation` en `backend/app/models/closure.py`.
- `closure_service.py` con autorización por recurso y administración de delegación.
- `closure_delegation.py` con GET/PUT/DELETE por solicitud.
- `ClosureDelegationContextOut` y schemas asociados.
- `ExpenseOut.can_close` y `ExpenseOut.can_delegate_close`.
- `frontend/src/closure-delegation.jsx` con selección/cambio/revocación.
- Alembic `20260818_0005_closure_delegation.py`.
- `test_closure_delegation.py` y `test_frontend_closure_contract.py`.
- Feature 008 y `docs/CLOSURE_DELEGATION.md`.

### Changed
- Cerrar, adjuntar factura y corregir/reemplazar factura pasan a autorización por solicitud:
  ```text
  solicitante original
  OR Administrador del sistema
  OR delegado activo de esa solicitud
  ```
- `financial_actions.py` deja `require_permission('requests:close')` y revalida con `current_user + can_manage_closure()`.
- `CLOSE_REQUEST` se asigna al solicitante o delegado activo de una solicitud `APPROVED`.
- El Administrador del sistema conserva facultad administrativa desde Solicitudes, pero no recibe todos los cierres como tareas personales.
- La delegación solo se ofrece en `APPROVED`/`CLOSED`.
- La tabla usa `x.can_close` y `x.can_delegate_close` en lugar de la capacidad global legacy.
- Constitución actualizada a **2.7.0**.

### Fixed
- El bridge temporal de Vite para **Delegar cierre/factura** ya no depende de saltos de línea o indentación exactos de `main.jsx`; usa un ancla regex tolerante a LF/CRLF y exige exactamente una coincidencia para evitar transformaciones ambiguas.

### Security / Audit
- Solo el solicitante original puede crear/cambiar/revocar delegación.
- Una sola delegación activa por solicitud mediante índice parcial.
- Cambiar/revocar conserva fila histórica con actor/timestamp.
- Un tercero con `requests:close` legacy no puede cerrar una solicitud ajena.
- El delegado debe estar activo, ser distinto del solicitante y no ser `system_accounts`.

### Migrations
- Cadena hasta Feature 008: `0000 → 0001 → 0002 → 0003 → 0004 → 0005`.
- `0005` crea `expense_closure_delegations` y marca `requests:close` como inactivo/legacy sin borrar asignaciones históricas.

### Testing
- Requester/Admin/delegado positivos.
- `requests:close` legacy sin delegación negativo.
- revocación retira autoridad.
- Dashboard entrega `CLOSE_REQUEST` al requester/delegado.
- contratos frontend protegen `x.can_close` / `x.can_delegate_close` y la tolerancia de formato del bridge de delegación.

---

## 2026-08-18 — Propiedad de corrección y Enviar a revisión

### Added
- `ExpenseOut.can_correct` como capacidad por solicitud.
- Feature 007.

### Changed
- **Corregir / reenviar** solo para solicitante original o `system_accounts`.
- Un aprobador usa **Enviar a revisión** con comentario; no edita solicitud ajena.
- `REVISION_REQUESTED` interrumpe inmediatamente: `NEEDS_REVISION`, pares PENDING/WAITING → `EXPIRED`, solicitante → `CORRECT_REQUEST`.
- Constitución **2.6.0**.

### Security
- `/resubmit` devuelve 403 a terceros aunque tengan `requests:create`, `requests:approve`, `config:manage`, Rol/Grupo/Cargo.

---

## 2026-08-18 — Permisos heredados por Cargo y Grupo

### Added
- `position_roles`, `PositionRole`, API/UI de Roles heredados por Cargo.
- `users_with_permission()` reconoce Cargo→Rol además de Grupo/directos.
- Migración `0004` importa una sola vez perfiles/títulos legacy a IAM canónico.
- Feature 006.

### Changed
- Modelo IAM permite Grupo→Rol→Permiso y Cargo→Rol→Permiso sin autorizar por nombres.
- Constitución **2.5.0**.

### Fixed
- Brecha donde Tesorero/Vicepresidente aparecían como aprobadores legacy pero no tenían `requests:approve` canónico.

---

## 2026-08-18 — Dashboard contextual y KPIs informativos

### Added
- `pending_action_service.py`, `my_actions.py`, `home-dashboard.jsx` y modal contextual.

### Changed
- Filas de Acciones pendientes abren modal; **Ver todas** abre Solicitudes.
- KPIs superiores dejan de ser botones.
- Todo usuario activo recibe baseline `requests:read` para seguimiento compartido.

---

## 2026-08-17 — Seguimiento universal y cancelación por recurso

### Added
- `tracking.py`, `cancellation_actions.py`, `ExpenseOut.can_cancel`.

### Changed
- Todos los usuarios activos pueden consultar solicitudes ajenas.
- Cancelación solo requester/Admin del sistema en estados cancelables.

---

## 2026-08-17 — Corrección MULTI_QUOTE preserva tipo y evidencia

### Added
- `expense-form.jsx`, `revision_actions.py`, migración `0003`, regresiones de corrección.

### Fixed
- `SIMPLE → SIMPLE` y `MULTI_QUOTE → MULTI_QUOTE` durante corrección.
- Pestaña de creación ya no decide el editor.
- Ronda MULTI_QUOTE corregida reinicia votos/invitaciones con nuevo `flow_id` y conserva soportes.

---

## 2026-08-17 — Correo por ambiente

### Changed
- Producción: Brevo HTTPS API en Render.
- Local: Gmail/Workspace SMTP.
- Docker local usa `PUBLIC_URL=http://localhost:3000`.

### Added
- `python -m scripts.test_email` y documentación de diagnóstico.

---

## 2026-08-17 — IAM configurable + FastAPI hardening

### Added
- Pydantic Settings, Argon2, application factory, Alembic `0000/0001/0002`, system accounts, consola IAM, TestClient y hardening Docker.

### Changed
- autorización runtime por permisos efectivos/políticas, no `UserRole`/`can_*`.
- producción y no-producción separadas por `ENVIRONMENT`.

---

## 2026-08-17 — Normalización de dominio

### Changed
- clasificación canónica Área + Categoría.
- Usuario/Grupo/Rol/Permiso/Cargo como terminología neutral.

### Removed / Retired
- dominio inmobiliario activo (`Apartment`, `UserApartment`, `OwnershipRole`, etc.).
- Persona/Personas como nombre del módulo y Subárea como segundo nivel funcional.

---

## Compatibility / Technical debt

Permanecen temporalmente sin autoridad runtime: `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `users.title`, `/api/users` legacy, `requests:close` inactivo, `main.jsx`, `domain-normalization.js` y bridges Vite.

La UI IAM puede todavía mostrar referencias legacy a `config:manage`; runtime las ignora para usuarios ordinarios hasta retirar esa deuda visual.

Pendientes separados: fórmula completa de mayoría APPROVED/REJECTED, empate MULTI_QUOTE, edición estructural de opciones y outbox/retry persistente.
