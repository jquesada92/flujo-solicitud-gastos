# Changelog

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
- `frontend/vite.config.js` con transform temporal y estricto que fuerza aislamiento/remount del estado de corrección.
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
- El transform Vite es temporal y debe retirarse cuando `ExpenseForm` salga de `frontend/src/main.jsx`.
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
- `frontend/src/main.jsx` continúa monolítico.
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
