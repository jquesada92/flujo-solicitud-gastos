# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución](../.specify/memory/constitution.md) — versión vigente **2.9.0**.
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
- [Feature 010 — notificaciones de Cargo y permisos efectivos](../specs/010-user-access-notifications/spec.md)
- [Feature 011 — consolidación de Usuarios/Organigrama en Accesos](../specs/011-access-console-consolidation/spec.md)

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
config:read
config:manage  # system-only
```

`requests:close` es un registro legacy inactivo y no autoriza runtime.

## Configuración vigente

```text
System Admin
→ Accesos
→ Áreas
→ Reglas
→ Auditoría / configuración técnica

Usuario con config:read
→ Accesos (solo lectura)
→ Áreas (solo lectura salvo areas:manage)
→ Reglas (solo lectura)
→ Auditoría (solo lectura)

Usuario con areas:manage sin config:read
→ Áreas solamente
```

**Usuarios/Personas y Organigrama no son pantallas independientes.** La creación y configuración de usuarios, Grupos, Roles, Permisos y Cargos vive dentro de **Accesos**.

`config:manage` solo es efectivo para `system_accounts`. `config:read` es lectura. `areas:manage` es configurable por Rol/Grupo/Cargo/usuario.

## Navegación desde Accesos

Accesos usa temporalmente `#access-management`, pero la navegación global debe seguir funcionando.

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

`frontend/src/access-navigation-bridge.js` elimina el hash antes de continuar la navegación y se carga antes de `main.jsx`.

## Clasificación canónica

```text
expense_area
expense_category
```

Área y Categoría son dimensiones independientes. `expense_type` / `expense_subcategory` quedan solo como compatibilidad legacy.

Alembic `0008` renombra las columnas físicas de `expenses` a los nombres canónicos.

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

## Acciones pendientes

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

## Cuenta técnica

```text
ENVIRONMENT=production
→ IAM: config:manage + config:read + areas:manage + requests:read
→ no approval/vote
→ puede cancelar/corregir/cerrar como excepciones por recurso

ENVIRONMENT!=production
→ puede recibir todos los permisos IAM activos para testing E2E
```

## Notificaciones IAM

Al crear un usuario activo, la invitación incluye Cargo(s) y permisos efectivos.

Cuando cambia realmente `position_ids`, se recalculan permisos efectivos y se envía **Actualización de cargo y permisos**. Guardar el mismo Cargo no duplica correo.

## Alembic

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

- `0003`: reparación de MULTI_QUOTE.
- `0004`: `position_roles` + import legacy a IAM.
- `0005`: `expense_closure_delegations` + retiro operativo de `requests:close`.
- `0006`: `areas:manage` + Gestor de áreas.
- `0007`: `config:read` + Visor de configuración.
- `0008`: `expense_area` / `expense_category` físicos.

Contrato de arranque:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## Gates locales

```text
cd backend
alembic heads
alembic current
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

Después de cambios en Accesos, validar manualmente la topbar desde la consola IAM.

## Deuda explícita

Permanecen temporalmente sin ser autoridad o arquitectura objetivo:

- `UserRole`;
- flags `can_*` legacy;
- `AccessProfile`;
- `BOARD_CODES`;
- `/api/users` legacy;
- vistas internas `people` / `organization` no navegables;
- `main.jsx`, `domain-normalization.js` y bridges Vite.

## Regla de mantenimiento

Todo cambio funcional/técnico sincroniza Constitución, specs, checklists, planes, README, prompt maestro, docs, HISTORY, CHANGELOG y PR cuando aplique.
