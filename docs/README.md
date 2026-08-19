# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución](../.specify/memory/constitution.md) — versión vigente **2.8.0**.
- [Política documental](DOCUMENTATION_POLICY.md).
- [Feature 001 — normalización de dominio](../specs/001-domain-normalization/spec.md)
- [Feature 002 — IAM configurable + FastAPI](../specs/002-configurable-iam-fastapi-hardening/spec.md)
- [Feature 003 — invariants de corrección](../specs/003-request-correction-invariants/spec.md)
- [Feature 004 — correo por ambiente](../specs/004-email-delivery-by-environment/spec.md)
- [Feature 005 — dashboard/seguimiento](../specs/005-universal-dashboard-tracking/spec.md)
- [Feature 006 — Cargo/Grupo → Rol → Permiso](../specs/006-position-group-role-inheritance/spec.md)
- [Feature 007 — Enviar a revisión + propiedad de corrección](../specs/007-revision-handoff-correction-ownership/spec.md)
- [Feature 008 — cierre/factura por propiedad o delegación](../specs/008-request-closure-delegation/spec.md)
- [Feature 009 — configuración técnica vs gestión de Áreas](../specs/009-technical-vs-area-configuration/spec.md)

Cada feature mantiene `spec.md`, `plan.md` y `checklists/acceptance.md`.

## Documentos funcionales/técnicos

- [Modelo IAM](IAM_MODEL.md)
- [Acceso a Configuración](CONFIGURATION_ACCESS.md)
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md)
- [Área + Categoría](CLASSIFICATION_MODEL.md)
- [Correcciones, reenvío y handoff](REQUEST_CORRECTIONS.md)
- [Seguimiento y acciones pendientes](REQUEST_TRACKING.md)
- [Cierre, factura y delegación](CLOSURE_DELEGATION.md)
- [Correo por ambiente](EMAIL_CONFIGURATION.md)
- [Terminología](TERMINOLOGY.md)
- [Historial](HISTORY.md)
- [Changelog](../CHANGELOG.md)
- [README principal](../README.md)
- [Prompt maestro](../PROMPT_RECONSTRUCCION.md)

## IAM vigente

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ baseline requests:read
       ↘ capacidades/delegaciones por recurso
```

Permisos vigentes:

```text
requests:read
requests:create
requests:approve
areas:manage
config:manage  # system-only
```

`requests:close` es un registro legacy inactivo desde migración `0005`; no autoriza runtime.

## Configuración

Frontera vigente:

```text
System Admin
→ Usuarios
→ Organigrama
→ Accesos
→ Áreas
→ Reglas/Auditoría técnica

Usuario ordinario con areas:manage
→ Áreas solamente
```

`config:manage` solo es efectivo para `system_accounts`. `areas:manage` es configurable por Rol/Grupo/Cargo/usuario.

Alembic `0006` crea el Rol neutral **Gestor de áreas**. La organización decide a qué Grupos/Cargos asociarlo; no existe autorización por nombres como Administración o Junta Directiva.

Ver [CONFIGURATION_ACCESS.md](CONFIGURATION_ACCESS.md).

## Capacidades por recurso

```text
can_cancel
→ estado cancelable + (solicitante OR system_accounts)

can_correct
→ estado corregible + (solicitante OR system_accounts)

can_close
→ APPROVED/CLOSED + (solicitante OR system_accounts OR delegado activo)

can_delegate_close
→ solicitante original
```

## Enviar a revisión

```text
Aprobador
→ Enviar a revisión + comentario
→ NEEDS_REVISION inmediato
→ otros PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST

Solicitante/Admin
→ Corregir / reenviar
```

## Dashboard

Todo usuario activo recibe baseline `requests:read`. KPIs superiores son informativos.

Tareas:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

`CORRECT_REQUEST` pertenece al solicitante. `CLOSE_REQUEST` pertenece al solicitante o delegado activo de una `APPROVED`; el Admin del sistema conserva capacidad administrativa desde Solicitudes sin recibir todas como tareas.

## Cierre/factura/delegación

Solo pueden gestionar cierre/factura:

```text
solicitante original
Administrador del sistema
delegado activo por esa solicitud
```

Solo el solicitante crea/cambia/revoca la delegación. Una sola delegación activa por solicitud y el historial se conserva.

Ver [CLOSURE_DELEGATION.md](CLOSURE_DELEGATION.md).

## Cuenta técnica

```text
ENVIRONMENT=production
→ IAM: config:manage + areas:manage + requests:read
→ no approval/vote
→ puede cancelar/corregir/cerrar como excepciones por recurso

ENVIRONMENT!=production
→ todos los permisos IAM activos para testing E2E
```

## Corrección

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

MULTI_QUOTE corregida reinicia ronda y excluye siempre al solicitante original.

## Alembic

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006
```

- `0003`: reparación `request_type` MULTI_QUOTE.
- `0004`: `position_roles` + import legacy a IAM.
- `0005`: `expense_closure_delegations` + retiro operativo de `requests:close`.
- `0006`: `areas:manage` + Rol Gestor de áreas + separación de configuración técnica.

Contrato de arranque:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## Correo

```text
Producción: Brevo / Render
Local: Google SMTP / Docker
```

## GitHub Actions sin cuota

Mientras la cuota esté agotada, gates locales obligatorios:

```text
python -m unittest discover -s tests -v
npm ci
npm run build
docker compose build --no-cache
docker compose up -d
```

No considerar verde un run que no pudo ejecutarse por cuota.

## Deuda explícita

Permanecen temporalmente sin ser autoridad: `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES`, `/api/users` legacy, `requests:close` inactivo, `main.jsx`, `domain-normalization.js` y bridges Vite.

Deuda funcional separada: fórmula completa de mayoría APPROVED/REJECTED, empate MULTI_QUOTE, edición estructural y outbox/retry.

## Regla de mantenimiento

Todo cambio funcional/técnico sincroniza Constitución, specs, checklists, planes, README, prompt maestro, docs, HISTORY, CHANGELOG y PR cuando aplique.
