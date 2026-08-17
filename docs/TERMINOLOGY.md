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

Conjunto configurable de usuarios que comparten una responsabilidad o contexto organizacional.

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

El backend no debe tomar decisiones por el nombre del Rol. Solo importan sus Permisos efectivos.

## Permiso

Capacidad atómica implementada por el producto.

Permisos actuales:

- `requests:read` — Consultar solicitudes/documentos autorizados.
- `requests:create` — Crear/corregir solicitudes y cargar soportes.
- `requests:approve` — Votar/aprobar/rechazar/solicitar corrección según el flujo.
- `requests:close` — Cargar/reemplazar factura y cerrar.
- `config:manage` — Administrar configuración e IAM.

Los permisos son la autoridad de acceso.

## Permiso efectivo

Permiso que un Usuario posee después de combinar:

- permisos directos;
- permisos de roles directos;
- permisos de roles heredados por grupos;
- restricciones especiales de seguridad aplicables a cuentas técnicas.

## Cargo / Posición

Metadato descriptivo de la estructura organizacional.

Ejemplos:

- Presidente
- Tesorero
- Gerente
- Director
- Analista

**Un Cargo no concede permisos.** Cambiar el Cargo de un Usuario no debe cambiar su autorización salvo que también se modifiquen sus Grupos/Roles/Permisos.

## Cuenta técnica / Administrador del sistema

Cuenta de sistema creada mediante bootstrap para administrar la plataforma.

No significa superusuario financiero. Su acceso máximo efectivo es:

- `config:manage`;
- `requests:read`.

No puede crear, aprobar ni cerrar solicitudes.

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

## Términos legacy

Los siguientes términos pueden aparecer temporalmente en código de compatibilidad, pero no representan la arquitectura objetivo:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`;
- `title` usado como cargo/perfil;
- `AccessProfile` como mezcla de cargo/permisos;
- Persona/Personas;
- Subárea para representar Categoría.

No introducir nuevas dependencias funcionales sobre estos conceptos.

## Regla de consistencia

Nuevos componentes, APIs, specs y documentación deben usar:

- **Usuario** para cuentas;
- **Grupo** para agrupación de usuarios;
- **Rol** para conjuntos de permisos;
- **Permiso** para autorización;
- **Cargo/Posición** para metadato organizacional;
- **Área** para contexto organizacional del gasto;
- **Categoría** para naturaleza del gasto.
