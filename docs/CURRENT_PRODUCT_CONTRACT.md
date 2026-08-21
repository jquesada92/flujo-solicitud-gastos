# Contrato vigente del producto

Este documento es el mapa rápido entre Constitución, código y Specs. No sustituye la Constitución; resume el estado que una implementación correcta debe observar.

## Producto

Flujo de Control de Gastos digitaliza solicitudes y decisiones con evidencia, auditoría y responsabilidades explícitas. La configuración organizacional vive en PostgreSQL y no se codifican nombres organizacionales en reglas de autorización.

## Identidad y acceso

```text
Usuario
├─ requests:read si está activo
├─ 0..1 Cargo (informativo)
└─ Roles asignados
     └─ cada Rol pertenece a un Grupo
          └─ cada Rol contiene Permisos
```

Cardinalidades:

```text
Rol     N:1 Grupo
Usuario 0..1 Rol por Grupo
Usuario 0..1 Cargo
```

La membresía del Grupo es una proyección de la asignación de Rol del Usuario. Cargo no participa en autorización.

## Permisos

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

`config:manage` está protegido para `system_accounts`; `config:read` es lectura ordinaria. `requests:close` no es una capacidad operativa vigente.

## UX principal

```text
Inicio        → mis acciones + mis solicitudes
Solicitudes   → consulta de procesos; crear solo con requests:create
Seguimiento   → carga de equipo, solo lectura
Configuración → Accesos / Áreas / Reglas / Auditoría según permisos
```

Accesos:

```text
Usuario → selector de Rol por Grupo → Guardar cambios
Grupo   → Roles disponibles; miembros derivados
Rol     → Permisos
```

## Flujo

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

Estados relevantes:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
APPROVED
REJECTED
NEEDS_REVISION
CANCELLED
CLOSED
```

Acciones contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Clasificación

```text
expense_area
expense_category
```

Área y Categoría son independientes y su habilitación conjunta usa una relación N:M.

## Responsabilidad por recurso

El backend calcula `can_cancel`, `can_correct`, `can_close`, `can_delegate_close`. Estas capacidades dependen de estado y relación con la solicitud, no de un permiso IAM global.

## Seguridad de sesión

- rutas privadas requieren token;
- token inválido/expirado/inactivo devuelve 401;
- `session_version` permite revocación;
- inactividad expira sesión;
- contraseña temporal bloquea operación normal hasta cambio;
- un 401 en frontend limpia sesión y retorna Login.

## Red frontend

No polling agresivo. GET iguales se deduplican en vuelo y las repeticiones automáticas usan caché corta. Las mutaciones invalidan lecturas. Las acciones de usuario pueden solicitar datos frescos.

## Persistencia

```text
ph_torre_delta.administracion
```

Alembic:

```text
0001 initial_schema
→ 0002 group_scoped_roles
→ 0003 single_user_position
```

Neon pooled es compatible porque el schema se califica explícitamente y no se envía `search_path` mediante startup options.

## Archivos de referencia en código

Backend:

```text
app/services/iam_service.py
app/api/iam_users.py
app/api/iam_access_policy.py
app/core/security.py
app/api/organization_overview.py
```

Frontend:

```text
iam-admin.jsx
home-dashboard.jsx
user-tracking.jsx
auth-route-guard.js
request-governor.js
expense-form.jsx
```
