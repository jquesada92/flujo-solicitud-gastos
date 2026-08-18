# Terminología funcional

Este documento define los términos canónicos visibles y técnicos del producto.

## Usuario

Cuenta que interactúa con el sistema. No usar **Persona/Personas** como nombre del módulo de cuentas.

## Grupo

Conjunto configurable de usuarios que puede heredar Roles. Nombres como Junta Directiva, Finanzas o Procurement son datos del cliente; no autorizan por sí mismos.

## Rol

Conjunto configurable y reutilizable de Permisos. Puede asociarse a Usuarios, Grupos o Cargos/Posiciones. El nombre del Rol no autoriza; importan sus Permisos.

## Permiso

Capacidad atómica implementada por el producto.

Permisos actuales:

- `requests:read` — Consultar dashboard/solicitudes/evidencia; baseline para usuarios activos.
- `requests:create` — Crear **nuevas solicitudes** y cargar soportes asociados.
- `requests:approve` — Votar/aprobar/rechazar/**enviar a revisión** según asignación del workflow.
- `requests:close` — Cargar/reemplazar factura y cerrar.
- `config:manage` — Administrar configuración e IAM.

**`requests:create` no significa “puede corregir cualquier solicitud”.** La corrección de una solicitud existente es una capacidad por recurso.

## Permiso efectivo

Unión de:

- baseline;
- permisos directos;
- Roles directos;
- Roles heredados por Grupos;
- Roles heredados por Cargos/Posiciones;
- política técnica aplicable al ambiente.

Fuentes visibles, por ejemplo:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

## Cargo / Posición

Elemento configurable de estructura organizacional. Puede heredar Roles.

```text
Cargo Tesorero → Rol Aprobador → requests:approve
```

El nombre del Cargo nunca autoriza directamente.

## Cuenta técnica / Administrador del sistema

Cuenta protegida persistida en `system_accounts`.

- producción: IAM efectivo máximo `config:manage + requests:read`;
- no producción: todos los permisos atómicos activos para pruebas E2E.

En producción conserva dos excepciones administrativas por recurso:

- cancelar solicitud abierta;
- corregir / reenviar solicitud corregible.

No son permisos financieros heredados.

## Área

Unidad/departamento/función organizacional asociada al gasto.

## Categoría

Naturaleza del bien o servicio adquirido. Área y Categoría son catálogos independientes relacionados de forma configurable.

## Solicitud sencilla / SIMPLE

Solicitud con una única opción/proveedor y su evidencia.

## Múltiples cotizaciones / MULTI_QUOTE

Solicitud con varias opciones que pasa por una ronda de selección/votación antes de continuar el flujo.

## Selector de tipo de nueva solicitud

Control UI para elegir SIMPLE/MULTI_QUOTE durante **creación**. No es autoridad sobre solicitudes existentes.

## Enviar a revisión

Acción de un **aprobador/revisor** que detecta un problema y necesita devolver la solicitud al solicitante para que este la corrija.

Requiere comentario indicando qué debe revisar/corregir el solicitante.

Su decisión técnica es:

```text
REVISION_REQUESTED
```

Semántica vigente:

```text
una revisión válida
→ solicitud NEEDS_REVISION inmediatamente
→ otros pasos PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST
```

**Enviar a revisión no significa editar la solicitud** y no concede `can_correct` al aprobador.

No usar **Solicitar corrección** como etiqueta de esta acción si puede confundirse con **Corregir / reenviar**.

## Corrección / Corregir y reenviar

Acción que modifica una solicitud existente sin cambiar su tipo.

Solo puede ejecutarla:

- el solicitante original; o
- el Administrador del sistema protegido.

No se hereda mediante `requests:create`, `requests:approve`, `config:manage`, Cargo, Grupo o Rol.

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Cuando la solicitud llega a `NEEDS_REVISION`, la tarea personal `CORRECT_REQUEST` pertenece al solicitante original. El Administrador del sistema conserva facultad administrativa, pero no es el responsable normal de esa tarea.

## `can_correct`

Capacidad calculada por solicitud para UX:

```text
estado corregible
AND (solicitante original OR system_accounts)
```

No es un permiso IAM y el backend vuelve a validar al ejecutar `resubmit`.

## Cancelación / Cancelar solicitud

Acción que termina una solicitud abierta. Solo solicitante original o Administrador del sistema.

No se hereda mediante `requests:create`, Cargo, Grupo o Rol.

## `can_cancel`

Capacidad calculada por solicitud para mostrar la acción de cancelación. No es un permiso IAM.

## Acción pendiente

Tarea contextual concreta que requiere intervención del usuario actual; no es un permiso IAM.

Códigos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Tipo canónico de solicitud

Tipo derivado de persistencia/evidencia durable. Durante compatibilidad legacy, se considera MULTI_QUOTE si está marcado como tal, está en `QUOTATION_VOTING` o posee dos o más `quotation_options`.

## Términos legacy

Pueden aparecer temporalmente, pero no son arquitectura objetivo:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`;
- `title` como mezcla histórica de cargo/perfil;
- `AccessProfile`;
- `BOARD_CODES`;
- Persona/Personas;
- Subárea para Categoría.

Una migración puede leerlos una sola vez para convertirlos a IAM canónico; runtime nuevo no debe usarlos como autoridad.

## Regla de consistencia

Usar siempre:

- **Usuario** para cuentas;
- **Grupo** para agrupaciones de usuarios;
- **Rol** para conjuntos de Permisos;
- **Permiso** para capacidades IAM;
- **Cargo/Posición** para estructura organizacional configurable;
- **Área** y **Categoría** para clasificación;
- **SIMPLE / MULTI_QUOTE** para tipos de solicitud;
- **Enviar a revisión** para devolver una aprobación al solicitante con comentarios;
- **Corregir / reenviar** para la edición por solicitante/Admin sin cambiar el tipo;
- **Cancelar solicitud** para finalizar una solicitud abierta.
