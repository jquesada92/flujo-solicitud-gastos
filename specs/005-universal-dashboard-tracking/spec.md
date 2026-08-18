# Especificación funcional — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.4.0

## Objetivo

Todo usuario activo y autenticado debe poder entrar al producto y entender el estado general de las solicitudes sin depender de su rol, grupo, cargo o de haber creado personalmente la solicitud.

La visibilidad de seguimiento es una capacidad base del producto. Las acciones mutables continúan controladas por permisos configurables.

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
  ∪ technical-account policy when applicable
```

Eliminar `requests:read` de un rol, grupo o asignación directa no puede retirarlo del usuario activo.

### F-005-04 — Lectura no concede acciones

Un usuario que solo tenga el baseline puede consultar, pero no puede:

- crear/corregir solicitudes sin `requests:create`;
- aprobar/votar sin `requests:approve`;
- subir factura/cerrar sin `requests:close`;
- administrar configuración sin `config:manage`.

### F-005-05 — Dashboard compartido + acciones personales

El dashboard muestra métricas generales de la organización para todos los usuarios activos.

La tarjeta **Acciones que requieren mi atención** solo cuenta acciones que el usuario actual puede realizar:

- aprobaciones asignadas y votaciones pendientes cuando tiene `requests:approve`;
- solicitudes aprobadas pendientes de cierre cuando tiene `requests:close`.

Un usuario de solo lectura debe ver las métricas generales y `0` acciones personales si no tiene tareas ejecutables.

### F-005-06 — Usuarios inactivos

Un usuario inactivo no puede iniciar sesión ni usar el baseline.

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

En la consola IAM, los permisos efectivos deben mostrar que `requests:read` proviene de:

```text
Acceso base del producto para usuarios activos
```

aunque el usuario no tenga un rol o permiso directo de consulta.

## Seguridad

La visibilidad universal aplica dentro del contexto organizacional actual del producto. No autoriza acceso anónimo ni acceso de usuarios inactivos.

Una futura implementación multi-tenant debe preservar aislamiento entre organizaciones; el baseline no implica lectura entre tenants.

## Fuera de alcance

- cambiar quorum/mayorías;
- cambiar edición MULTI_QUOTE;
- hacer `requests:create`, `requests:approve`, `requests:close` o `config:manage` universales;
- implementar tenancy/multi-organización;
- implementar historial paginado completo;
- retirar todos los campos `UserRole` legacy en esta feature.
