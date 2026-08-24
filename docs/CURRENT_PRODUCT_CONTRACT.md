# Contrato vigente del producto

Este documento es el mapa rápido entre Constitución, código y Specs. No sustituye la Constitución; resume el estado que una implementación correcta debe observar.

## Producto

Flujo de Control de Gastos digitaliza solicitudes y decisiones con evidencia, auditoría y responsabilidades explícitas. La configuración organizacional vive en PostgreSQL y no se codifican nombres organizacionales en reglas de autorización.

## Identidad y acceso

```text
Usuario
├─ requests:read si está activo
├─ 0..1 Cargo (informativo)
├─ 0..N Roles globales
└─ Roles agrupados
     └─ máximo 1 Rol por Grupo
          ├─ Permisos propios del Rol
          └─ Permisos heredados del Grupo
```

Cardinalidades:

```text
Grupo   0..N Roles
Rol     0..1 Grupo
Usuario 0..1 Rol por Grupo
Usuario 0..N Roles globales
Usuario 0..1 Cargo
```

Un Rol sin Grupo es global. La membresía del Grupo es una proyección únicamente de Roles agrupados y `GroupMember` aislado no autoriza. Cargo tampoco participa en autorización.

En Configuración > Accesos, la lista de Usuarios activos presenta como máximo 10 coincidencias. La búsqueda acepta cédula, nombres, apellidos, correo, Rol o Grupo asignado y no distingue mayúsculas ni acentos.

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

Los permisos efectivos ordinarios pueden venir de Permisos propios de Roles globales o, en un Rol agrupado dentro de un Grupo activo, de la unión `RolePermission ∪ GroupPermission`. Es herencia aditiva sin `DENY`; los Permisos propios se conservan al editar o desvincular el Grupo. `config:manage` continúa reservado a la política técnica protegida.

## UX principal

```text
Inicio        → mis acciones + mis solicitudes
Solicitudes   → consulta de procesos; crear solo con requests:create
Seguimiento   → carga de equipo, solo lectura
Configuración → Accesos / Áreas / Reglas / Auditoría según permisos
```

Accesos:

```text
Usuario → selector de Rol por Grupo + Roles globales → Guardar cambios
Grupo   → Permisos heredables + Roles opcionales; miembros derivados
Rol     → Permisos propios + herencia visible; global o agrupado
```

El Rol global técnico `Administrador del sistema` no pertenece a ningún Grupo. El bootstrap lo asigna a la cuenta técnica como representación, pero la autorización privilegiada sigue dependiendo de `system_accounts`.

## Flujo

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

`MULTI_QUOTE` congela por ronda a los usuarios activos con `requests:approve`, excluye al solicitante y requiere soporte en cada opción. Cada invitado tiene un voto activo; la ronda espera a todos y solo selecciona una cotización si existe ganador único. Los empates permanecen en `QUOTATION_VOTING`.

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
→ 0004 allow_global_roles
→ 0005 activity_periods
→ 0006 period_snapshot_values
→ 0007 period_audit_metadata
→ 0008 normalize_period_timestamps
→ 0009 group_permission_inheritance
```

`0004` permite Roles globales manteniendo la protección de máximo un Rol por Usuario/Grupo.
`0005` agrega períodos para Usuario, Área, Rol y Grupo. `0006` incorpora la
instantánea JSON: cada modificación cierra la versión anterior y abre una fila
nueva con llave propia. Usuario conserva cédula, contacto y Roles; Rol conserva
el Grupo asociado.
`0007` agrega actor, timestamp, tipo de evento, campos modificados y valores
anterior/nuevo. Las operaciones autenticadas usan al usuario de la sesión y los
procesos internos quedan marcados como `SYSTEM:*`.
`0008` normaliza toda vigencia y evento a timestamps con zona horaria UTC.
`0009` agrega `group_permissions` vacía y no altera `role_permissions` ni accesos preexistentes.

## Recuperación de entidades inactivas

Usuario, Área, Rol y Grupo desaparecen de sus listas al quedar inactivos. Las
rutas `/recovery` permiten localizar únicamente registros inactivos por cédula,
código o nombre normalizado. La UI solicita confirmación, completa el formulario
y usa `PATCH` sobre el ID recuperado; nunca crea otra identidad ni borra auditoría.
El flujo existe tanto en la consola IAM como en la pantalla principal de Personas.

Neon pooled es compatible porque tablas, tipos ENUM y SQL crudo se califican explícitamente y no se envía `search_path` mediante startup options. Los contadores de identificadores usan el nombre completo derivado de `AreaCounter.__table__.fullname`; los Enum ORM usan `inherit_schema=True`.

## Archivos de referencia en código

Backend:

```text
app/services/iam_service.py
app/api/iam_users.py
app/api/iam_group_assignments.py
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
