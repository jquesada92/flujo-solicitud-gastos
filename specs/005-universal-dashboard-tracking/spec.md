# Especificación funcional — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.6.0

## Objetivo

Todo usuario activo y autenticado debe poder entrar al producto y entender el estado general de las solicitudes sin depender de su rol, grupo, cargo o de haber creado personalmente la solicitud.

La visibilidad de seguimiento es una capacidad base. Las acciones mutables continúan controladas por permisos configurables o reglas explícitas por recurso.

## Historia principal

**Como usuario activo**, quiero ver un dashboard al iniciar sesión y consultar las solicitudes de la organización, **para dar seguimiento aunque no las haya creado ni tenga permiso para aprobarlas o cerrarlas**.

## Reglas funcionales

### F-005-01 — Inicio disponible para todos

Todo usuario activo y autenticado puede acceder a **Inicio** y cargar el dashboard sin pertenecer a un grupo ni tener un rol configurado.

### F-005-02 — Solicitudes disponibles para todos

Todo usuario activo puede entrar a **Solicitudes** y consultar solicitudes de la organización para seguimiento. No se filtra por `UserRole.REQUESTER` ni por `requested_by == current_user.email`.

### F-005-03 — `requests:read` es baseline

```text
effective_permissions(active_user)
  = {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
  ∪ technical-account policy when applicable
```

Eliminar `requests:read` de un rol, grupo, cargo o asignación directa no puede retirarlo del usuario activo.

### F-005-04 — Lectura no concede acciones

Un usuario con solo baseline no puede:

- crear nuevas solicitudes sin `requests:create`;
- aprobar/votar sin `requests:approve`;
- subir factura/cerrar sin `requests:close`;
- administrar configuración sin `config:manage`.

**Corregir una solicitud existente no se concede por `requests:create` global.** Solo solicitante original o Administrador del sistema pueden hacerlo según Feature 007.

La cancelación tampoco se concede por `requests:create`; se rige por F-005-07.

### F-005-05 — Dashboard compartido + acciones personales

El dashboard muestra métricas generales de la organización y una bandeja personal de tareas vigentes:

- `APPROVAL_DECISION`: aprobación pendiente asignada al usuario con `requests:approve`;
- `QUOTATION_VOTE`: invitación MULTI_QUOTE vigente y no respondida con `requests:approve`;
- `CORRECT_REQUEST`: solicitud propia en `NEEDS_REVISION`;
- `CLOSE_REQUEST`: solicitud `APPROVED` para usuario con `requests:close`.

`CORRECT_REQUEST` se asigna por **propiedad de la solicitud**, no por `requests:create`. El Administrador del sistema conserva capacidad administrativa de corrección desde Solicitudes, pero no recibe automáticamente la tarea personal de solicitudes ajenas.

Tener un permiso general no basta si la acción concreta no está asignada al usuario.

### F-005-06 — Usuarios inactivos

Un usuario inactivo no puede iniciar sesión ni usar el baseline.

### F-005-07 — Cancelación de solicitud abierta

Solo pueden cancelar:

1. solicitante original; o
2. Administrador del sistema identificado mediante `system_accounts`.

Estados cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`.

No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

La cancelación exige motivo y el listado expone `can_cancel` calculado por backend.

### F-005-08 — Seleccionar una acción pendiente abre su acción contextual

Una fila de **Inicio → Acciones pendientes** abre un modal y reconsulta:

```text
GET /api/expenses/{request_id}/my-actions
```

El modal muestra únicamente acciones aún ejecutables:

```text
APPROVAL_DECISION
→ Aprobar
→ Rechazar
→ Enviar a revisión + comentario obligatorio

QUOTATION_VOTE
→ revisar opciones y soportes
→ votar una cotización

CLOSE_REQUEST
→ cargar factura
→ notas de cierre
→ cerrar solicitud

CORRECT_REQUEST
→ abrir la solicitud propia para corregir / reenviar
```

**Enviar a revisión** (`REVISION_REQUESTED`) es una interrupción inmediata del flujo según Feature 007: no espera mayoría, lleva la solicitud a `NEEDS_REVISION`, expira las demás aprobaciones vigentes y entrega `CORRECT_REQUEST` al solicitante original.

**Ver todas** conserva su función independiente de navegar a **Solicitudes**.

El frontend no deduce acciones solo por estado. Después de una mutación, dashboard y `my-actions` se refrescan para evitar acciones obsoletas.

### F-005-09 — KPIs superiores solo informativos

Las tarjetas superiores —incluidas **Acciones que requieren mi atención**, **Solicitudes en proceso** y **Cerradas en 24 horas**— son indicadores informativos.

No son botones, no tienen `onClick` y no ejecutan navegación ni workflow.

Interacción explícita:

```text
fila de Acciones pendientes → modal contextual
Ver todas                    → Solicitudes
```

## Interfaz

La navegación **Inicio** y **Solicitudes** está disponible para cualquier usuario activo.

La tabla usa capacidades backend por recurso:

```text
can_cancel
can_correct
```

`can_correct` solo puede ser true para solicitante original o Administrador del sistema en estados corregibles. Ver una solicitud ajena nunca habilita su edición.

## Seguridad

La API contextual exige autenticación y devuelve solo acciones del usuario actual.

La aprobación contextual no expone tokens bearer de links de correo. **Enviar a revisión** requiere comentario mínimo y el backend vuelve a validarlo.

Una futura implementación multi-tenant debe preservar aislamiento entre organizaciones.

## Fuera de alcance

- completar la fórmula constitucional de quorum/mayoría para aprobar/rechazar;
- cambiar estructura de una MULTI_QUOTE durante corrección;
- hacer permisos mutables universales;
- tenancy/multi-organización;
- historial paginado completo;
- retirar todo `UserRole` legacy en esta feature.
