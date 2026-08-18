# Terminología funcional

Este documento define los términos canónicos visibles y técnicos del producto.

## Usuario

Cuenta que interactúa con el sistema.

Uso correcto:

- Usuarios
- Crear usuario
- Editar usuario
- Usuario activo/inactivo
- Permisos del usuario

No usar **Persona/Personas** como nombre del módulo de cuentas.

## Grupo

Conjunto configurable de usuarios que comparten una responsabilidad o contexto organizacional. Un Grupo puede heredar uno o más Roles; sus miembros activos heredan los permisos de esos Roles.

Ejemplos posibles del cliente:

- Junta Directiva
- Finanzas
- Procurement
- Operaciones

Los ejemplos son datos configurables. Ningún nombre de Grupo autoriza por sí mismo.

## Rol

Conjunto configurable y reutilizable de Permisos.

Ejemplos posibles:

- Aprobador
- Gestión de solicitudes
- Consulta

Un mismo Rol puede asociarse a Usuarios, Grupos o Cargos/Posiciones.

El backend no debe tomar decisiones por el nombre del Rol. Solo importan sus Permisos efectivos.

## Permiso

Capacidad atómica implementada por el producto.

Permisos actuales:

- `requests:read` — Consultar solicitudes/documentos autorizados; baseline para usuarios activos.
- `requests:create` — Crear/corregir solicitudes y cargar soportes.
- `requests:approve` — Votar/aprobar/rechazar/solicitar corrección según el flujo.
- `requests:close` — Cargar/reemplazar factura y cerrar.
- `config:manage` — Administrar configuración e IAM.

Los permisos efectivos son la autoridad de acceso.

## Permiso efectivo

Permiso que un Usuario posee después de combinar:

- baseline de producto aplicable;
- permisos directos;
- permisos de Roles directos;
- permisos de Roles heredados por Grupos activos;
- permisos de Roles heredados por Cargos/Posiciones activos;
- políticas especiales aplicables a cuentas técnicas según el ambiente.

Las fuentes pueden mostrarse como:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

## Cargo / Posición

Elemento configurable de la estructura organizacional.

Ejemplos:

- Presidente
- Tesorero
- Gerente
- Director
- Analista

Un Cargo **puede heredar Roles**. Todos los usuarios asignados a ese Cargo heredan los permisos de esos Roles mientras Cargo y Rol estén activos.

La regla importante es:

> El nombre del Cargo no autoriza; la relación persistida `Cargo → Rol → Permiso` sí puede otorgar autorización.

Ejemplo válido:

```text
Cargo Tesorero → Rol Aprobador → requests:approve
```

Ejemplo prohibido:

```text
si cargo == TESORERO → aprobar
```

Por tanto, cambiar el Cargo de un Usuario sí puede cambiar sus permisos efectivos cuando el Cargo tiene Roles asociados.

## Cuenta técnica / Administrador del sistema

Cuenta de sistema creada mediante bootstrap para administrar la plataforma.

Su política depende del ambiente:

- `ENVIRONMENT=production`: `config:manage` + `requests:read`; no participa en el flujo financiero aunque reciba accidentalmente Roles por Grupo/Cargo/directos.
- cualquier otro `ENVIRONMENT`: todos los permisos atómicos activos para pruebas end-to-end.

La condición se basa en `SystemAccount + ENVIRONMENT`, no en nombre, email, Cargo o `UserRole.ADMIN`.

La capacidad de cancelar una solicitud abierta en producción es una excepción administrativa del ciclo de vida basada en `system_accounts`, no un permiso financiero heredado.

## Área

Unidad, departamento o función organizacional asociada al gasto.

Ejemplos:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing

## Categoría

Naturaleza del bien o servicio adquirido.

Ejemplos:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias
- Mobiliario
- Capacitación

Área y Categoría son catálogos independientes relacionados de forma configurable.

## Solicitud sencilla / SIMPLE

Solicitud que utiliza una única opción de compra/proveedor y su evidencia correspondiente.

## Múltiples cotizaciones / MULTI_QUOTE

Solicitud que contiene varias opciones de cotización y pasa por una ronda de selección/votación antes de continuar con el flujo definido.

## Selector de tipo de nueva solicitud

Control de UI que permite elegir **Solicitud sencilla** o **Múltiples cotizaciones** mientras se está creando una solicitud nueva.

Ese selector representa intención de **creación**. No es autoridad sobre una solicitud existente y su estado no debe heredarse al entrar en una corrección.

## Corrección / Corregir y reenviar

Acción que modifica datos de una solicitud existente y reinicia el flujo que corresponda **sin cambiar su tipo de solicitud**.

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Al entrar en corrección, el editor deriva el tipo desde la solicitud seleccionada y descarta el estado previo del selector de nueva solicitud. Una conversión entre SIMPLE y MULTI_QUOTE no debe llamarse corrección; requeriría una acción funcional explícita diferente.

## Cancelación / Cancelar solicitud

Acción que termina una solicitud aún abierta.

Solo puede ejecutarla:

- el solicitante original; o
- la cuenta protegida Administrador del sistema.

No se hereda mediante `requests:create`, Cargo, Grupo o Rol.

## Tipo canónico de solicitud

Tipo de flujo derivado de la persistencia y evidencia durable. Durante la compatibilidad legacy, una solicitud se considera MULTI_QUOTE si está marcada como tal, está en `QUOTATION_VOTING` o posee dos o más `quotation_options`.

## Términos legacy

Los siguientes términos pueden aparecer temporalmente en código/migraciones de compatibilidad, pero no representan la arquitectura objetivo:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`;
- `title` usado como mezcla histórica de cargo/perfil;
- `AccessProfile` como mezcla de cargo/permisos;
- `BOARD_CODES` como lista hardcodeada de cargos;
- Persona/Personas;
- Subárea para representar Categoría.

Una migración versionada puede leer estos datos una sola vez para convertirlos a IAM canónico. El runtime nuevo no debe utilizarlos como autoridad.

## Regla de consistencia

Nuevos componentes, APIs, specs y documentación deben usar:

- **Usuario** para cuentas;
- **Grupo** para agrupación de usuarios con posible herencia de Roles;
- **Rol** para conjuntos reutilizables de Permisos;
- **Permiso** para capacidades de autorización;
- **Cargo/Posición** para estructura organizacional configurable con posible herencia de Roles;
- **Área** para contexto organizacional del gasto;
- **Categoría** para naturaleza del gasto;
- **Solicitud sencilla / SIMPLE** y **Múltiples cotizaciones / MULTI_QUOTE** para los tipos de solicitud;
- **Selector de tipo de nueva solicitud** solo para la elección durante creación;
- **Corrección / Corregir y reenviar** para editar sin cambiar el tipo de solicitud;
- **Cancelar solicitud** para la transición explícita de una solicitud abierta.
