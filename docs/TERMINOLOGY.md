# Terminología funcional

Este documento define los términos canónicos visibles y técnicos del producto.

## Usuario

Cuenta que interactúa con el sistema. No usar **Persona/Personas** como nombre del módulo de cuentas.

## Grupo

Conjunto configurable de usuarios que puede heredar Roles. Nombres como Junta Directiva, Finanzas o Procurement son datos del cliente; no autorizan por sí mismos.

## Rol

Conjunto configurable y reutilizable de Permisos. Puede asociarse a Usuarios, Grupos o Cargos/Posiciones. El nombre del Rol no autoriza; importan sus Permisos.

## Permiso

Capacidad IAM atómica implementada por el producto.

Permisos operativos actuales:

- `requests:read` — Consultar dashboard/solicitudes/evidencia; baseline para usuarios activos.
- `requests:create` — Crear nuevas solicitudes y cargar soportes asociados.
- `requests:approve` — Votar/aprobar/rechazar/enviar a revisión según asignación.
- `config:manage` — Administrar configuración e IAM.

`requests:close` permanece como **registro legacy inactivo** para trazabilidad. No autoriza cierre, factura ni delegación.

## Permiso efectivo

Unión de baseline, permisos directos, Roles directos, Roles heredados por Grupos/Cargos y política técnica aplicable. Las capacidades por recurso y delegaciones no se convierten en permisos IAM.

## Cargo / Posición

Elemento configurable de estructura organizacional que puede heredar Roles. El nombre del Cargo nunca autoriza directamente.

## Cuenta técnica / Administrador del sistema

Cuenta protegida persistida en `system_accounts`.

Producción: IAM máximo `config:manage + requests:read` y exclusión de aprobación/votación. Conserva excepciones administrativas por recurso para cancelar, corregir y gestionar cierre/factura. No administra delegaciones ordinarias en nombre del solicitante.

## Área

Unidad/departamento/función organizacional asociada al gasto.

## Categoría

Naturaleza del bien o servicio adquirido. Área y Categoría son independientes.

## SIMPLE / Solicitud sencilla

Solicitud con una única opción/proveedor y evidencia.

## MULTI_QUOTE / Múltiples cotizaciones

Solicitud con varias opciones que pasa por selección/votación antes de continuar el flujo.

## Enviar a revisión

Acción del aprobador/revisor que detecta un problema y devuelve la solicitud al solicitante con comentario obligatorio.

```text
REVISION_REQUESTED
→ NEEDS_REVISION inmediato
→ otros PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST
```

No significa editar la solicitud ni concede `can_correct`.

## Corrección / Corregir y reenviar

Edición de una solicitud existente sin cambiar su tipo. Solo solicitante original o Administrador del sistema protegido.

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

## `can_correct`

Capacidad por solicitud:

```text
estado corregible AND (solicitante original OR system_accounts)
```

No es permiso IAM.

## Cancelación / Cancelar solicitud

Finaliza una solicitud abierta. Solo solicitante original o Administrador del sistema.

## `can_cancel`

Capacidad por solicitud para mostrar/autorizar cancelación. No es permiso IAM.

## Cierre de solicitud

Transición de `APPROVED` a `CLOSED` que exige factura final. La autoridad es por recurso, no por permiso global.

## Factura de cierre

Documento final asociado al cierre. Puede reemplazarse en `CLOSED` por un actor autorizado, conservando la versión anterior y un `InvoiceChangeEvent` con motivo.

## Delegación de cierre/factura

Asignación explícita por **una solicitud** que el solicitante original otorga a otro usuario activo para registrar/corregir la factura y cerrar.

Reglas:

- solo el solicitante crea/cambia/revoca;
- una delegación activa por solicitud;
- delegado distinto del solicitante y no cuenta de sistema;
- cambiar/revocar conserva historial (`revoked_at`, actor);
- no concede acceso de cierre a otras solicitudes;
- el solicitante mantiene su autoridad.

## `can_close`

Capacidad por solicitud:

```text
status ∈ {APPROVED, CLOSED}
AND (solicitante original OR system_accounts OR delegado activo)
```

No es `UserOut.can_close` legacy ni un permiso IAM.

## `can_delegate_close`

Capacidad por solicitud que indica si el usuario actual puede administrar su delegación de cierre/factura. Solo el solicitante original.

## Acción pendiente

Tarea contextual concreta; no es permiso IAM.

Códigos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

`CLOSE_REQUEST` significa solicitud `APPROVED` cuya responsabilidad corresponde al solicitante o delegado activo.

## Tipo canónico de solicitud

Tipo derivado de persistencia/evidencia durable. En compatibilidad legacy, MULTI_QUOTE si está marcado como tal, está en `QUOTATION_VOTING` o tiene 2+ opciones.

## Términos legacy

Pueden aparecer físicamente, pero no son arquitectura objetivo:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`, `can_close` de sesión;
- `requests:close` como permiso histórico inactivo;
- `title` como mezcla histórica;
- `AccessProfile`;
- `BOARD_CODES`;
- Persona/Personas;
- Subárea para Categoría.

## Regla de consistencia

Usar siempre Usuario, Grupo, Rol, Permiso, Cargo/Posición, Área, Categoría, SIMPLE/MULTI_QUOTE, Enviar a revisión, Corregir/reenviar, Cancelar solicitud y Delegación de cierre/factura según las definiciones anteriores.
