# Changelog

## 2026-08-17 — Seguimiento universal y cancelación por solicitante/Admin del sistema

### Added
- `requests:read` pasa a ser baseline efectivo para todo usuario activo y autenticado.
- `backend/app/api/tracking.py` sirve el dashboard y listado compartido de solicitudes sin filtrar por solicitante.
- `backend/app/api/cancellation_actions.py` implementa cancelación canónica antes del router legacy.
- `ExpenseOut.can_cancel` expone la capacidad de cancelación por solicitud para la UX.
- `backend/tests/test_request_cancellation.py` cubre propiedad, cuenta técnica y estados terminales.
- `specs/005-universal-dashboard-tracking/` y `docs/REQUEST_TRACKING.md` documentan el contrato.

### Changed
- Todo usuario activo puede entrar a **Inicio / Dashboard** y **Solicitudes** para dar seguimiento a solicitudes creadas por otros usuarios.
- `pending_my_action` solo incluye acciones ejecutables por el usuario actual.
- Solo el solicitante original o el Administrador del sistema identificado mediante `system_accounts` pueden cancelar una solicitud abierta.
- `requests:create`, `requests:approve` y `config:manage` no conceden por sí mismos cancelación de solicitudes ajenas.
- `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION` y `APPROVED` son cancelables por esos actores; `CLOSED`, `CANCELLED` y `REJECTED` no lo son.
- El frontend usa `can_cancel` retornado por backend para mostrar **Cancelar solicitud**, en lugar de inferirlo desde `can_request` y una lista fija de estados.
- En producción la cuenta técnica mantiene como permisos IAM únicamente `config:manage + requests:read`; la cancelación administrativa es una excepción explícita de ciclo de vida, no un permiso financiero.

### Fixed
- Una solicitud MULTI_QUOTE abierta en `QUOTATION_VOTING` puede cancelarse por su solicitante original o por el Administrador del sistema.
- Se retiró un import transitorio a un bridge legacy inexistente que apareció durante la investigación.
- La evidencia de producción mostró que Tesorero/Vicepresidente ya tenían permiso efectivo de aprobación, por lo que se descartó un backfill IAM innecesario.

### Migrations
- Feature 005 no agrega migración de esquema.
- La cadena Alembic permanece `0000 → 0001 → 0002 → 0003`.

---

## 2026-08-17 — ExpenseForm modular para correcciones MULTI_QUOTE

### Fixed
- Una corrección MULTI_QUOTE ya no depende de sustituciones granulares sobre el formulario sencillo legacy.
- `frontend/src/expense-form.jsx` es ahora la implementación canónica del formulario de solicitudes.
- `resolveRequestType(draft)` reconoce `MULTI_QUOTE` por `request_type`, estado `QUOTATION_VOTING` o dos/más `quotation_options`.
- `effectiveRequestType` gobierna layout, validaciones, payload y uploads durante una corrección.
- Un draft MULTI_QUOTE renderiza directamente **Opciones para votación** y no el layout SIMPLE.
- Se restauran proveedor, monto, URL, observaciones y metadata de soportes existentes por opción.

### Changed
- `vite.config.js` deja de parchear condiciones internas de `ExpenseForm`; durante la transición importa el componente modular y elimina del bundle la definición legacy completa.
- El componente modular rehidrata por `draft.request_id`/`flow_id`; no se inyecta una `key` mediante reemplazo textual del montaje.

### Testing
- `test_frontend_revision_contract.py` ahora verifica el componente modular, inferencia MULTI_QUOTE, restauración de soportes y extracción del formulario legacy durante build.

---

## 2026-08-17 — Corrección MULTI_QUOTE usa tipo efectivo autoritativo

### Fixed
- Una solicitud en `QUOTATION_VOTING` ya no puede renderizar el formulario SIMPLE durante **Corregir / reenviar** por conservar temporalmente el estado React `requestType`.
- Durante una corrección, `effectiveRequestType` se deriva del draft/evidencia durable y gobierna render, validaciones, payload y uploads.
- El payload de `resubmit` ya no toma `request_type` del selector/pestaña de creación cuando existe un draft.
- La UI muestra el tipo de solicitud corregida como dato de solo lectura y no ofrece cambiar SIMPLE ↔ MULTI_QUOTE durante una corrección.

### Added
- `backend/tests/test_frontend_revision_contract.py` protege el contrato frontend durante la transición del monolito.

---

## 2026-08-17 — Enlaces de aprobación local usan el frontend Docker correcto

### Fixed
- Docker Compose ya no permite que un `PUBLIC_URL=http://localhost:5173` heredado desde `backend/.env` genere enlaces inválidos mientras el frontend real está publicado en `localhost:3000`.
- El backend recibe por defecto `PUBLIC_URL=http://localhost:3000` bajo Compose.
- `CORS_ALLOWED_ORIGINS` local incluye `localhost:3000` y `localhost:5173` para soportar Compose y Vite directo.

### Added
- `.env.example` raíz documenta `LOCAL_PUBLIC_URL` y `LOCAL_CORS_ALLOWED_ORIGINS`.
- Regresión en `test_container_portability.py` que exige coherencia entre el puerto publicado por Compose y el `PUBLIC_URL` usado por los correos.
- Documentación de diagnóstico para `ERR_CONNECTION_REFUSED` causado por desalineación entre puerto 3000/5173.

### Behavior
- Docker Compose → links nuevos `http://localhost:3000/email-action/...`.
- Vite directo → `http://localhost:5173/email-action/...` si ese es el `PUBLIC_URL` configurado.
- Producción → URL HTTPS de Vercel configurada en Render.

---

## 2026-08-17 — Correo por ambiente: Google SMTP local / Brevo producción

### Changed
- Desarrollo local pasa a documentarse con `EMAIL_MODE=smtp` para enviar correos reales mediante Gmail/Google Workspace.
- Producción conserva `EMAIL_MODE=brevo` en el backend desplegado en Render.
- Las credenciales de correo permanecen exclusivamente en backend; Vercel/frontend no recibe `SMTP_PASSWORD` ni `BREVO_API_KEY`.

### Added
- `docs/EMAIL_CONFIGURATION.md` con matriz de ambientes, configuración SMTP y diagnóstico.
- `specs/004-email-delivery-by-environment/` con spec, plan técnico y criterios de aceptación.
- `python -m scripts.test_email --to <correo>` para probar el transporte configurado sin depender del workflow de solicitudes.

### Local configuration
- Google SMTP recomendado: `smtp.gmail.com`, puerto `465`, `ssl`.
- Alternativa: puerto `587`, `starttls`.
- `SMTP_PASSWORD` se documenta como App Password de Google; nunca se versiona.

### Diagnostics
- `EMAIL_MODE=console` se reconoce explícitamente como modo sin entrega real.
- La entrega de correo se puede validar por separado antes de probar SIMPLE o MULTI_QUOTE.

---

## 2026-08-17 — Correcciones MULTI_QUOTE preservan el flujo

### Fixed
- **Corregir / reenviar** ya no depende de la pestaña SIMPLE/MULTI_QUOTE seleccionada antes de editar.
- Si **Solicitud sencilla** está activa y se corrige una solicitud MULTI_QUOTE, el editor se remonta y abre directamente como MULTI_QUOTE.
- El frontend deriva el tipo inicial desde la solicitud/evidencia durable y no reutiliza el estado React de creación.
- El frontend restaura opciones de cotización y soportes existentes al hidratar una corrección.
- El backend canónico deriva un tipo canónico de solicitud y rechaza con `409` cualquier intento real de cambiarlo durante `resubmit`.
- Registros legacy con `request_type=SIMPLE` pero evidencia MULTI_QUOTE se reconocen y reparan correctamente.
- Una corrección MULTI_QUOTE reinicia correctamente la ronda: nuevo `flow_id`, votos vigentes limpiados, invitaciones reemplazadas y estado `QUOTATION_VOTING`.
- Los attachments existentes permanecen asociados a sus opciones.

### Added
- `backend/app/api/revision_actions.py` como ruta canónica de correcciones registrada antes del router legacy.
- `backend/tests/test_multi_quote_revision.py` con regresión HTTP de preservación/reparación de tipo, evidencia y ronda.
- Test específico de fila legacy con `request_type=SIMPLE` y evidencia MULTI_QUOTE.
- `20260817_0003_backfill_multi_quote_request_type.py` para reparar solicitudes históricas inconsistentes.
- `specs/003-request-correction-invariants/`.
- `docs/REQUEST_CORRECTIONS.md`.

### Behavior
- `SIMPLE → corrección → SIMPLE`.
- `MULTI_QUOTE → corrección → MULTI_QUOTE`.
- La pestaña seleccionada antes de pulsar **Corregir / reenviar** no influye en el editor.
- Durante esta feature una MULTI_QUOTE corregida conserva la misma cantidad de opciones; se pueden editar proveedor, monto, URL y observaciones.
- Cambiar deliberadamente SIMPLE ↔ MULTI_QUOTE queda fuera de `Corregir / reenviar`.

### Migrations
- La cadena Alembic pasa a `0000 → 0001 → 0002 → 0003`.
- `0003` cambia a `MULTI_QUOTE` filas con `QUOTATION_VOTING` o dos/más opciones que aún tengan el default `SIMPLE`.

### Compatibility / Technical debt
- `modularExpenseFormPlugin` es temporal y debe retirarse cuando `main.jsx` importe directamente `frontend/src/expense-form.jsx`.
- Editar estructuralmente una ronda (agregar/eliminar opciones con evidencia/versionado explícito) requiere una feature separada.

---

## 2026-08-17 — IAM configurable + FastAPI hardening

### Added
- Modelo IAM persistido: Permissions, Roles, Groups, Memberships, direct Roles/Permissions, Positions y System Accounts.
- Permisos atómicos `requests:read`, `requests:create`, `requests:approve`, `requests:close`, `config:manage`.
- Consola gráfica **Configuración → Accesos**.
- API neutral `/api/iam/*` y `/api/iam/users`.
- Vista de permisos efectivos y fuentes de herencia.
- Política ambiental explícita para `TECHNICAL_ADMIN`.
- `UserOut.permission_codes` y alias temporal `can_close`.
- Pydantic Settings centralizado con distinción entre `is_production_environment` e `is_production`.
- Argon2 mediante `pwdlib` con upgrade transparente de PBKDF2 legacy.
- Alembic y migraciones versionadas con baseline explícito para bases nuevas.
- Entry point Docker que migra/bootstrap antes de Uvicorn.
- `FastAPI TestClient` para matriz de autorización IAM.
- Tests específicos de política productiva/no-productiva de la cuenta técnica.
- Test de topología que exige un solo head Alembic y la cadena esperada.
- Test de regresión de portabilidad Windows→Linux para scripts y healthchecks de Docker Compose.
- Smoke tests Docker de entrypoint Linux e import de `scripts.bootstrap_admin`.
- Servicios canónicos para resolución de aprobadores, documentos y votación.
- `docs/IAM_MODEL.md` y `docs/FASTAPI_ARCHITECTURE.md`.
- Spec/plan/checklist de `002-configurable-iam-fastapi-hardening`.

### Changed
- Autorización runtime consulta permisos efectivos/política de cuenta técnica; `UserRole.ADMIN` no es autoridad.
- **Producción:** la cuenta técnica queda limitada a `config:manage` + `requests:read`.
- **No producción:** la cuenta técnica recibe todos los permisos atómicos activos para pruebas end-to-end.
- Fuera de producción la cuenta técnica puede participar en poblaciones de aprobación/votación.
- En producción las asignaciones financieras accidentales a la cuenta técnica siguen siendo filtradas.
- `RENDER=true` mantiene endurecimiento de secretos/CORS, pero ya no implica por sí solo política funcional de producción; solo `ENVIRONMENT=production` activa segregación financiera.
- Login y `current_user()` derivan permisos efectivos para el contrato del frontend.
- Población canónica de aprobadores/votantes se resuelve por `requests:approve`, no por cargos fijos.
- Crear solicitudes exige `requests:create`.
- Cerrar/reemplazar factura exige `requests:close`.
- Configuración de acceso se administra desde la UI y no mediante nombres codificados.
- `app/main.py` queda como alias mínimo del application factory.
- Lifespan deja de crear/migrar esquemas y hacer backfills.
- Operaciones canónicas con SQLAlchemy/filesystem síncrono utilizan path functions `def`.
- Modelos de clasificación se movieron fuera de `api/areas.py`.
- Servicio de correo usa Settings y branding organizacional neutral.
- Docker Compose local espera a que `/api/health` del backend esté sano antes de iniciar Nginx.
- `.gitattributes` fuerza LF y Docker normaliza CRLF.
- El bootstrap técnico se ejecuta como `python -m scripts.bootstrap_admin`.

### Security
- En producción System Accounts filtran permisos financieros incluso ante asignaciones accidentales.
- Fuera de producción el acceso completo de la cuenta técnica se concede únicamente por política `SystemAccount + ENVIRONMENT` para testing.
- Roles técnicos `system_managed` no se pueden modificar desde la interfaz.
- Default deny para usuarios operativos.
- Backend mantiene autoridad sobre acciones aunque el frontend o campos legacy indiquen otra cosa.

### Testing
- No-producción: cuenta técnica obtiene todos los permisos activos.
- No-producción: login expone `permission_codes`, `can_request`, `can_approve`, `can_view`, `can_configure` y `can_close` efectivos.
- No-producción: cuenta técnica puede entrar en población `requests:approve`.
- Producción: cuenta técnica queda en config/read.
- Producción: `requests:close` directo accidental es filtrado y el endpoint de cierre devuelve 403.
- Producción: cuenta técnica queda fuera de población de aprobación.

### Migrations
- `20260817_0000_application_baseline.py` define un baseline property-free para instalaciones limpias y conserva tablas productivas que ya existen.
- `20260817_0001_iam_foundation.py` crea IAM y migra flags legacy a permisos como operación única de compatibilidad.
- `20260817_0002_system_accounts.py` identifica cuentas técnicas existentes.
- `20260817_0003_backfill_multi_quote_request_type.py` repara el tipo de solicitudes MULTI_QUOTE históricas.
- La cadena Alembic es lineal: `0000 → 0001 → 0002 → 0003`.
- `scripts.bootstrap_admin` crea/asocia idempotentemente la cuenta técnica fuera del lifespan.
- El smoke test contra PostgreSQL/Neon real continúa siendo requisito previo al despliegue productivo.

### Compatibility / Technical debt
- `UserRole`, `title` y `can_*` permanecen temporalmente como metadatos/puente; no son autoridad de acceso.
- `/api/users` legacy permanece mientras migra el frontend operacional.
- `frontend/src/main.jsx` continúa monolítico en otras áreas.
- El monolito todavía contiene bypasses visuales legacy `user.role === "ADMIN"` y `canClose={true}`; el backend no confía en ellos y deben migrarse a `permission_codes`.
- `domain-normalization.js` sigue temporalmente.
- El refactor no declara corregida la fórmula legacy de quorum/mayoría ni la regla de empate MULTI_QUOTE.

---

## 2026-08-17 — Normalización de dominio

### Added
- Catálogo global de Categorías independiente de Áreas.
- Relación configurable Área ↔ Categoría.
- Terminología canónica **Usuario / Usuarios**.
- Constitución del proyecto y documentación gobernada por specs/checklists.

### Changed
- Segundo selector funcional → **Categoría**.
- Primer nivel → **Área**.
- Documentación forma parte del Definition of Done.
- CI ejecuta regresión backend, build frontend e imágenes Docker.

### Compatibility
- `expenses.expense_type` → Área.
- `expenses.expense_subcategory` → Categoría.
- Tablas legacy de clasificación permanecen como puente temporal.

### Removed / Retired
- Retiro progresivo de conceptos inmobiliarios específicos.
- `Subárea` deja de ser término funcional del segundo nivel.
- `Persona / Personas` deja de ser término funcional del módulo de cuentas.