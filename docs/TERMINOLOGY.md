# Terminología funcional

Este documento define los términos canónicos visibles y técnicos del producto.

## Usuario

Cuenta que interactúa con el sistema. No usar **Persona/Personas** como nombre del módulo de cuentas.

La creación y configuración de usuarios vive dentro de **Configuración → Accesos**.

## Accesos

Consola única para administrar o consultar, según permisos:

```text
Usuarios
Grupos
Roles
Permisos
Cargos/Posiciones
Asignaciones
Permisos efectivos y fuentes
```

No existen pantallas independientes de **Usuarios/Personas** u **Organigrama** en la navegación canónica.

## Grupo

Conjunto configurable de usuarios que puede heredar Roles. Nombres como Junta Directiva, Finanzas o Procurement son datos del cliente; no autorizan por sí mismos.

## Rol

Conjunto configurable y reutilizable de Permisos. Puede asociarse a Usuarios, Grupos o Cargos/Posiciones. El nombre del Rol no autoriza; importan sus Permisos.

## Permiso

Capacidad IAM atómica implementada por el producto.

Permisos vigentes:

- `requests:read` — seguimiento universal; baseline para usuarios activos.
- `requests:create` — crear nuevas solicitudes.
- `requests:approve` — votar/aprobar/rechazar/enviar a revisión según asignación.
- `areas:manage` — administrar Área + Categoría y sus relaciones.
- `config:read` — consultar Configuración sin mutarla.
- `config:manage` — administración técnica **system-only** reservada a `system_accounts`.

`requests:close` permanece como registro legacy inactivo. No autoriza cierre, factura ni delegación.

## Permiso efectivo

Unión de baseline, permisos directos, Roles directos, Roles heredados por Grupos/Cargos y política técnica aplicable, menos capacidades system-only no aplicables al actor.

Para usuario ordinario, una asignación de `config:manage` no se convierte en permiso efectivo.

## `config:read`

Permiso de consulta de Configuración. Permite ver Accesos, Áreas, Reglas y Auditoría en modo solo lectura. No concede mutaciones ni implica `config:manage` o `areas:manage`.

## Administración técnica

Funciones reservadas al Administrador del sistema protegido mediante `system_accounts`.

La navegación canónica es:

```text
Accesos
Áreas
Reglas
Auditoría / configuración técnica
```

No incluye Usuarios/Personas ni Organigrama como pantallas separadas.

## Gestión de Áreas

Configuración organizacional del catálogo Área + Categoría.

Permiso:

```text
areas:manage
```

Puede heredarse por Rol/Grupo/Cargo o asignarse directamente.

## Cargo / Posición

Elemento configurable de estructura organizacional que puede heredar Roles. El nombre del Cargo nunca autoriza directamente.

## Cuenta técnica / Administrador del sistema

Cuenta protegida persistida en `system_accounts`.

Producción: IAM máximo `config:manage + config:read + areas:manage + requests:read`, sin aprobación/votación. Conserva excepciones administrativas por recurso para cancelar, corregir y gestionar cierre/factura.

## Área

Unidad/departamento/función organizacional asociada al gasto.

Campo canónico de solicitud:

```text
expense_area
```

## Categoría

Naturaleza del bien o servicio adquirido. Área y Categoría son independientes.

Campo canónico:

```text
expense_category
```

`expense_type` y `expense_subcategory` son nombres legacy de compatibilidad, no terminología vigente.

## SIMPLE / Solicitud sencilla

Solicitud con una única opción/proveedor y evidencia.

## MULTI_QUOTE / Múltiples cotizaciones

Solicitud con varias opciones que pasa por selección/votación antes de continuar el flujo.

## Enviar a revisión

Acción del aprobador que detecta un problema y devuelve la solicitud al solicitante con comentario obligatorio.

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

Documento final asociado al cierre. Puede reemplazarse en `CLOSED` por un actor autorizado, conservando la versión anterior y el evento de cambio.

## Delegación de cierre/factura

Asignación explícita por una solicitud que el solicitante original otorga a otro usuario activo para registrar/corregir factura y cerrar.

## `can_close`

```text
status ∈ {APPROVED, CLOSED}
AND (solicitante original OR system_accounts OR delegado activo)
```

No es permiso IAM.

## `can_delegate_close`

Capacidad por solicitud que indica si el usuario actual puede administrar la delegación de cierre/factura. Solo el solicitante original.

## Acción pendiente

Tarea contextual concreta; no es permiso IAM.

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Navegación desde Accesos

Mientras Accesos esté abierto, Inicio, Solicitudes, Facturas, Auditoría, Configuración y Salir continúan siendo acciones normales del shell. Salir de Accesos implica retirar `#access-management` antes de continuar la navegación.

## Términos legacy

Pueden aparecer físicamente, pero no son arquitectura objetivo:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`, `can_close` de sesión;
- `requests:close` como permiso histórico inactivo;
- `title` como mezcla histórica;
- `AccessProfile`;
- `BOARD_CODES`;
- Persona/Personas;
- Organigrama como pantalla independiente;
- Subárea/Subcategoría como Categoría;
- `expense_type` / `expense_subcategory` como contrato nuevo.

## Regla de consistencia

Usar siempre Usuario, Accesos, Grupo, Rol, Permiso, Cargo/Posición, Área, Categoría, Gestión de Áreas, Administración técnica, SIMPLE/MULTI_QUOTE, Enviar a revisión, Corregir/reenviar, Cancelar solicitud y Delegación de cierre/factura según estas definiciones.
