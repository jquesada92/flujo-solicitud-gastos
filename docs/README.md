# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución](../.specify/memory/constitution.md) — versión vigente **2.6.0**.
- [Política documental](DOCUMENTATION_POLICY.md).
- [Feature 001 — normalización de dominio](../specs/001-domain-normalization/spec.md)
- [Feature 002 — IAM configurable + FastAPI](../specs/002-configurable-iam-fastapi-hardening/spec.md)
- [Feature 003 — invariants de corrección](../specs/003-request-correction-invariants/spec.md)
- [Feature 004 — correo por ambiente](../specs/004-email-delivery-by-environment/spec.md)
- [Feature 005 — dashboard/seguimiento](../specs/005-universal-dashboard-tracking/spec.md)
- [Feature 006 — Cargo/Grupo → Rol → Permiso](../specs/006-position-group-role-inheritance/spec.md)
- [Feature 007 — Enviar a revisión + propiedad de corrección](../specs/007-revision-handoff-correction-ownership/spec.md)

Cada feature mantiene `spec.md`, `plan.md` y `checklists/acceptance.md`.

## Documentos funcionales/técnicos

- [Modelo IAM](IAM_MODEL.md)
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md)
- [Área + Categoría](CLASSIFICATION_MODEL.md)
- [Correcciones, reenvío y handoff](REQUEST_CORRECTIONS.md)
- [Seguimiento y acciones pendientes](REQUEST_TRACKING.md)
- [Correo por ambiente](EMAIL_CONFIGURATION.md)
- [Terminología](TERMINOLOGY.md)
- [Historial](HISTORY.md)
- [Changelog](../CHANGELOG.md)
- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)

## Modelo IAM vigente

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ baseline requests:read
```

Cargo/Grupo pueden heredar Roles. El nombre de un Cargo nunca autoriza.

La consola autoritativa es **Configuración → Accesos**.

## Capacidades por recurso

No son permisos IAM:

```text
can_cancel
can_correct
```

Ambas se calculan por solicitud.

```text
can_cancel → solicitante original OR system_accounts, estado cancelable
can_correct → solicitante original OR system_accounts, estado corregible
```

`requests:create` no concede corrección/cancelación de solicitudes ajenas.

## Enviar a revisión

Distinción canónica:

```text
Aprobador
→ Enviar a revisión + comentario
→ NEEDS_REVISION inmediato
→ otros pasos PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST

Solicitante/Admin del sistema
→ Corregir / reenviar
```

Una revisión no espera mayoría y no concede `can_correct` al aprobador.

## Dashboard

Todo usuario activo recibe `requests:read`.

Los KPIs superiores son informativos. Interacción:

```text
fila de Acciones pendientes → modal contextual
Ver todas                    → Solicitudes
```

Tareas actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

`CORRECT_REQUEST` pertenece al solicitante de una solicitud `NEEDS_REVISION`; no depende de `requests:create`.

## Cuenta técnica

```text
ENVIRONMENT=production
→ IAM: config:manage + requests:read
→ no approval/vote/close
→ puede cancelar/corregir como excepciones administrativas por recurso

ENVIRONMENT!=production
→ todos los permisos activos para testing E2E
```

## Corrección

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

Una MULTI_QUOTE corregida reinicia la ronda y **excluye siempre al solicitante original**, aunque el Administrador del sistema haya ejecutado la corrección.

## Alembic

```text
0000 → 0001 → 0002 → 0003 → 0004
```

- `0003`: reparación `request_type` MULTI_QUOTE.
- `0004`: `position_roles` + importación única de configuración legacy a IAM.
- Feature 007 no agrega migración.

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

Correo de aprobación usa:

```text
Aprobar
Rechazar
Enviar a revisión
```

El solicitante recibe el comentario de revisión.

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

Permanecen temporalmente sin ser autoridad:

```text
UserRole
can_*
AccessProfile
BOARD_CODES
/api/users legacy
main.jsx monolítico
domain-normalization.js
bridges Vite
```

Deuda funcional separada: fórmula completa de mayoría APPROVED/REJECTED, empate MULTI_QUOTE, edición estructural de opciones y outbox/retry persistente.

## Regla de mantenimiento

Todo cambio funcional/técnico debe sincronizar Constitución, specs, checklists, planes, README, prompt maestro, docs, HISTORY, CHANGELOG y PR cuando aplique.
