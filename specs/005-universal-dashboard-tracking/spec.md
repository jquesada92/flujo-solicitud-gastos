# Especificación funcional — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.5.0

## Objetivo

Todo usuario activo y autenticado debe poder entrar al producto y entender el estado general de las solicitudes sin depender de su rol, grupo, cargo o de haber creado personalmente la solicitud.

La visibilidad de seguimiento es una capacidad base del producto. Las acciones mutables continúan controladas por permisos configurables o reglas explícitas de propiedad de la solicitud.

## Historia principal

**Como usuario activo**, quiero ver un dashboard al iniciar sesión y consultar las solicitudes de la organización, **para dar seguimiento al estado de los gastos aunque no los haya creado ni tenga permiso para aprobarlos o cerrarlos**.

## Reglas funcionales

### F-005-01 — Inicio disponible para todos

Todo usuario activo y autenticado puede acceder a **Inicio** y cargar el dashboard.

No se requiere pertenecer a un grupo ni tener un rol configurado.

### F-005-02 — Solicitudes disponibles para todos

Todo usuario activo y autenticado puede entrar a **Solicitudes** y consultar las solicitudes visibles de seguimiento de la organización.

La identidad del solicitante no limita la visibilidad:

```text
Usuario A crea solicitud X
Usuario B inicia sesión
→ Usuario B puede ver X para seguimiento
```

No debe existir una condición equivalente a:

```text
si role == REQUESTER:
    mostrar solo requested_by == current_user.email
```

### F-005-03 — `requests:read` es baseline

`requests:read` es un permiso atómico implementado por el producto, pero su concesión a usuarios activos no depende de roles/grupos/asignaciones.

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

Un usuario que solo tenga el baseline puede consultar, pero no puede:

- crear/corregir solicitudes sin `requests:create`;
- aprobar/votar sin `requests:approve`;
- subir factura/cerrar sin `requests:close`;
- administrar configuración sin `config:manage`.

La cancelación no se concede por `requests:create`: se rige por F-005-07.

### F-005-05 — Dashboard compartido + acciones personales

El dashboard muestra métricas generales de la organización para todos los usuarios activos.

La tarjeta **Acciones que requieren mi atención** solo cuenta acciones vigentes que el usuario actual puede ejecutar y que están asignadas a ese usuario dentro del workflow:

- aprobación pendiente asignada al usuario con `requests:approve`;
- invitación de votación MULTI_QUOTE aún no respondida con `requests:approve`;
- solicitud propia en `NEEDS_REVISION` cuando conserva `requests:create`;
- solicitud `APPROVED` pendiente de factura/cierre cuando el usuario tiene `requests:close`.

Tener el permiso general no basta si la acción concreta no está asignada al usuario. Por ejemplo, `requests:approve` no convierte todas las solicitudes pendientes en acciones personales.

Un usuario de solo lectura debe ver las métricas generales y `0` acciones personales si no tiene tareas ejecutables.

### F-005-06 — Usuarios inactivos

Un usuario inactivo no puede iniciar sesión ni usar el baseline.

### F-005-07 — Cancelación de una solicitud abierta

Una solicitud abierta solo puede ser cancelada por:

1. el **solicitante original** de esa solicitud; o
2. el **Administrador del sistema**, identificado canónicamente mediante `system_accounts`.

Ningún rol, grupo, cargo o permiso configurable —incluidos `requests:create`, `requests:approve` y `config:manage`— amplía por sí mismo la facultad de cancelar solicitudes ajenas.

Se consideran abiertas para cancelación:

- `QUOTATION_VOTING`;
- `SUBMITTED`;
- `PENDING_APPROVAL`;
- `NEEDS_REVISION`;
- `APPROVED` mientras todavía no esté cerrada.

No pueden cancelarse:

- `CLOSED`;
- `CANCELLED`;
- `REJECTED`.

La cancelación requiere motivo, registra `cancelled_at`, `cancelled_by` y `cancellation_reason`, y expira aprobaciones abiertas asociadas.

El listado de solicitudes debe exponer una capacidad calculada `can_cancel` para que la interfaz muestre **Cancelar solicitud** solo cuando el backend autorice esa acción. La UI no debe inferir cancelación desde `can_request` ni desde una lista local de cargos/roles.

### F-005-08 — Seleccionar una acción pendiente abre su acción contextual

Las filas de **Inicio → Acciones pendientes** no son simples accesos a la lista de Solicitudes.

Al seleccionar una fila, la interfaz debe abrir una **ventana/modal contextual** para esa solicitud y consultar nuevamente al backend las acciones que siguen vigentes para el usuario autenticado.

El modal muestra únicamente controles correspondientes a acciones actualmente ejecutables por ese usuario:

```text
APPROVAL_DECISION
→ Aprobar
→ Rechazar
→ Solicitar corrección

QUOTATION_VOTE
→ revisar opciones y soportes
→ votar una cotización

CLOSE_REQUEST
→ cargar factura
→ notas de cierre
→ cerrar solicitud

CORRECT_REQUEST
→ abrir la solicitud propia para corregir y reenviar
```

**Ver todas** conserva su función independiente de navegar a **Solicitudes**.

El frontend no debe deducir la acción a partir del estado solamente. Debe consumir una respuesta backend específica del usuario, porque una solicitud puede estar globalmente pendiente y no requerir ninguna acción del usuario actual.

Antes de ejecutar una acción y después de registrarla, el sistema debe revalidar el estado vigente. Esto cubre, por ejemplo, que el usuario haya respondido desde un correo, otra pestaña o una sesión distinta.

Después de una mutación exitosa, el dashboard y el detalle del modal se refrescan. Si ya no existe una tarea vigente, el modal informa que no quedan acciones pendientes para esa solicitud.

## Alcance de seguimiento

Esta feature mantiene el comportamiento vigente de la lista operativa:

- solicitudes abiertas/en proceso;
- solicitudes cerradas recientes según la ventana implementada;
- datos necesarios para seguimiento y expediente bajo `requests:read`.

No introduce todavía un buscador histórico paginado de todas las solicitudes cerradas; eso pertenece a la evolución de reporting/paginación.

## Interfaz

La navegación principal **Inicio** y **Solicitudes** debe estar disponible para cualquier usuario autenticado activo.

La interfaz puede seguir derivando temporalmente:

```text
can_view = requests:read
```

pero `can_view` no es autoridad; el backend resuelve el baseline.

Para cancelación, la tabla debe usar exclusivamente `can_cancel` retornado por el backend. Esto permite que una solicitud `QUOTATION_VOTING` pueda cancelarse por su solicitante o por el Administrador del sistema sin habilitar la acción para los demás usuarios que solo la observan.

Para acciones pendientes, cada fila debe mostrar la acción concreta devuelta por backend —por ejemplo **Responder aprobación** o **Votar cotización**— y abrir el modal contextual al seleccionarla.

En la consola IAM, los permisos efectivos deben mostrar que `requests:read` proviene de:

```text
Acceso base del producto para usuarios activos
```

aunque el usuario no tenga un rol o permiso directo de consulta.

## Seguridad

La visibilidad universal aplica dentro del contexto organizacional actual del producto. No autoriza acceso anónimo ni acceso de usuarios inactivos.

La lectura compartida no puede convertir acciones de propietario en acciones globales. En particular, un usuario que pueda ver una solicitud ajena o tenga `requests:create` no puede cancelarla por ese hecho.

La API contextual de acciones debe requerir autenticación y devolver exclusivamente acciones que correspondan al usuario actual. Las decisiones de aprobación no deben requerir exponer al frontend el token bearer usado por los enlaces de correo.

Una futura implementación multi-tenant debe preservar aislamiento entre organizaciones; el baseline no implica lectura entre tenants.

## Fuera de alcance

- cambiar quorum/mayorías;
- cambiar edición MULTI_QUOTE;
- hacer `requests:create`, `requests:approve`, `requests:close` o `config:manage` universales;
- implementar tenancy/multi-organización;
- implementar historial paginado completo;
- retirar todos los campos `UserRole` legacy en esta feature.
