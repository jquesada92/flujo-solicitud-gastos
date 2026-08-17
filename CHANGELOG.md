# Changelog

## 2026-08-17 — IAM configurable + FastAPI hardening

### Added
- Modelo IAM persistido: Permissions, Roles, Groups, Memberships, direct Roles/Permissions, Positions y System Accounts.
- Permisos atómicos `requests:read`, `requests:create`, `requests:approve`, `requests:close`, `config:manage`.
- Consola gráfica **Configuración → Accesos**.
- API neutral `/api/iam/*` y `/api/iam/users`.
- Vista de permisos efectivos y fuentes de herencia.
- Protección explícita de cuentas técnicas.
- Pydantic Settings centralizado.
- Argon2 mediante `pwdlib` con upgrade transparente de PBKDF2 legacy.
- Alembic y migraciones versionadas con baseline explícito para bases nuevas.
- Entry point Docker que migra/bootstrap antes de Uvicorn.
- `FastAPI TestClient` para matriz de autorización IAM.
- Test de topología que exige un solo head Alembic y la cadena esperada.
- Servicios canónicos para resolución de aprobadores, documentos y votación.
- `docs/IAM_MODEL.md` y `docs/FASTAPI_ARCHITECTURE.md`.
- Spec/plan/checklist de `002-configurable-iam-fastapi-hardening`.

### Changed
- Autorización runtime consulta permisos efectivos persistidos; desaparece el bypass automático de `ADMIN`.
- Cuenta técnica queda limitada a configuración + consulta.
- Población canónica de aprobadores/votantes se resuelve por `requests:approve`, no por cargos fijos.
- Crear solicitudes exige `requests:create`.
- Cerrar/reemplazar factura exige `requests:close`.
- Configuración de acceso se administra desde la UI y no mediante nombres codificados.
- `app/main.py` queda como alias mínimo del application factory.
- Lifespan deja de crear/migrar esquemas y hacer backfills.
- Operaciones canónicas con SQLAlchemy/filesystem síncrono utilizan path functions `def`.
- Modelos de clasificación se movieron fuera de `api/areas.py`.
- Servicio de correo usa Settings y branding organizacional neutral.
- README, prompt maestro, Constitución, terminología e historia se actualizan al nuevo modelo.

### Security
- System Accounts filtran permisos financieros incluso ante una asignación accidental.
- Roles técnicos `system_managed` no se pueden modificar desde la interfaz.
- Default deny cuando falta un permiso efectivo.
- Backend mantiene autoridad sobre acciones aunque el frontend o campos legacy indiquen otra cosa.

### Migrations
- `20260817_0000_application_baseline.py` define un baseline property-free para instalaciones limpias y conserva tablas productivas que ya existen.
- `20260817_0001_iam_foundation.py` crea IAM y migra flags legacy a permisos como operación única de compatibilidad.
- `20260817_0002_system_accounts.py` identifica cuentas técnicas existentes.
- La cadena Alembic es lineal: `0000 → 0001 → 0002`.
- `scripts/bootstrap_admin.py` crea/asocia idempotentemente la cuenta técnica fuera del lifespan.
- El smoke test contra PostgreSQL/Neon real continúa siendo requisito previo al despliegue productivo; el CI actual valida topología, compilación y tests de aplicación.

### Compatibility / Technical debt
- `UserRole`, `title` y `can_*` permanecen temporalmente como metadatos/puente para UI/router legacy; no son autoridad de acceso.
- `/api/users` legacy permanece detrás de `config:manage` mientras migra el frontend operacional.
- `frontend/src/main.jsx` continúa monolítico y `domain-normalization.js` sigue temporalmente.
- El refactor no declara corregida la fórmula legacy de quorum/mayoría del motor de aprobación.
- La regla exacta de quorum/empate de MULTI_QUOTE queda para una spec funcional separada.

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
