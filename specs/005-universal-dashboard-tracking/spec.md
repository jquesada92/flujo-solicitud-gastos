# Especificación funcional — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.7.0

## Objetivo

Todo usuario activo y autenticado debe poder entrar al producto y entender el estado general de las solicitudes sin depender de rol, grupo, cargo o de haber creado personalmente la solicitud.

La visibilidad de seguimiento es una capacidad base. Las acciones mutables continúan controladas por permisos configurables o reglas/delegaciones por recurso.

## Historia principal

Como usuario activo, quiero ver un dashboard al iniciar sesión y consultar las solicitudes de la organización para dar seguimiento aunque no las haya creado.

## Reglas funcionales

### F-005-01 — Inicio disponible para todos

Todo usuario activo y autenticado accede a **Inicio** sin requerir grupo/rol.

### F-005-02 — Solicitudes disponibles para todos

Todo usuario activo consulta solicitudes de la organización. No filtrar por `UserRole.REQUESTER` ni `requested_by == current_user.email`.

### F-005-03 — `requests:read` baseline

```text
effective_permissions(active_user)
  = {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
```

No puede revocarse a un usuario activo.

### F-005-04 — Lectura no concede mutaciones

Solo lectura no concede crear (`requests:create`), aprobar/votar (`requests:approve`), configurar (`config:manage`), corregir/cancelar solicitudes ajenas ni gestionar cierre/factura ajena.

Corrección se rige por Feature 007. Cierre/factura/delegación se rige por Feature 008.

### F-005-05 — Dashboard compartido + acciones personales

Tareas vigentes:

- `APPROVAL_DECISION`: `requests:approve` + aprobación PENDING asignada;
- `QUOTATION_VOTE`: `requests:approve` + invitación vigente sin voto;
- `CORRECT_REQUEST`: solicitud propia `NEEDS_REVISION`;
- `CLOSE_REQUEST`: solicitud `APPROVED` propia o con delegación activa al usuario.

`CORRECT_REQUEST` no depende de `requests:create`.

`CLOSE_REQUEST` **no depende de `requests:close`**. Feature 008 retira ese permiso como autoridad global. El Administrador del sistema conserva facultad administrativa de cierre desde Solicitudes, pero no recibe todas las solicitudes aprobadas como tareas personales.

### F-005-06 — Usuarios inactivos

Un usuario inactivo no puede autenticarse ni usar baseline/delegación.

### F-005-07 — Cancelación

Solo solicitante original o Administrador del sistema. Cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`. No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

### F-005-08 — Acción pendiente contextual

Una fila de **Acciones pendientes** reconsulta:

```text
GET /api/expenses/{request_id}/my-actions
```

El modal muestra únicamente acciones ejecutables:

```text
APPROVAL_DECISION → Aprobar / Rechazar / Enviar a revisión
QUOTATION_VOTE    → revisar/votar
CLOSE_REQUEST     → factura/notas/cerrar
CORRECT_REQUEST   → abrir propia para corregir/reenviar
```

Enviar a revisión es interrupción inmediata según Feature 007.

**Ver todas** navega a Solicitudes.

### F-005-09 — KPIs superiores informativos

**Acciones que requieren mi atención**, **Solicitudes en proceso** y **Cerradas en 24 horas** no son botones ni tienen `onClick`.

## Interfaz

La tabla usa capacidades backend:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

- `can_correct`: solicitante/Admin en estados corregibles.
- `can_close`: solicitante/Admin/delegado activo en `APPROVED`/`CLOSED`.
- `can_delegate_close`: solicitante original.

Ver una solicitud ajena nunca habilita acciones por sí solo.

## Seguridad

La API contextual devuelve solo tareas del usuario actual. Aprobación contextual no expone tokens bearer de correo. Cierre y factura vuelven a validar el actor en backend aunque la UI esté manipulada.

## Dependencias posteriores

- Feature 007 define Enviar a revisión y propiedad de corrección.
- Feature 008 define cierre/factura por solicitante/Admin/delegación y desactiva `requests:close` como autoridad global.

## Fuera de alcance

- fórmula completa quorum/mayoría APPROVED/REJECTED;
- edición estructural MULTI_QUOTE;
- tenancy/multi-organización;
- historial paginado completo;
- retiro físico completo de legacy.
