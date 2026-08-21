# Terminología funcional

## Usuario
Cuenta autenticable que interactúa con el producto.

## Grupo
Ámbito organizacional que agrupa Roles disponibles. La membresía de un Usuario se deriva de su Rol en ese Grupo.

## Rol
Conjunto de Permisos. Pertenece a un único Grupo. Un Usuario puede tener máximo un Rol por Grupo.

## Permiso
Capacidad IAM atómica.

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

## Permiso efectivo
Baseline del usuario activo más Permisos de sus Roles dentro de Grupos activos, aplicando la política de cuenta técnica/system-only.

## Cargo / Posición
Metadato organizacional descriptivo. Un Usuario puede tener máximo un Cargo. Cargo no concede acceso.

## Accesos
Consola de Usuarios, Grupos, Roles y Permisos. El Usuario recibe acceso seleccionando un Rol dentro de cada Grupo y guardando explícitamente.

## Inicio
Vista personal: mis acciones, mis solicitudes y métricas propias.

## Seguimiento
Vista de equipo de solo lectura: Grupos, miembros, Roles y cantidades de acciones pendientes.

## Área
Contexto organizacional asociado al gasto. Campo: `expense_area`.

## Categoría
Naturaleza del bien/servicio. Campo: `expense_category`.

## Solicitud SIMPLE
Una opción principal de compra/proveedor.

## Solicitud MULTI_QUOTE
Varias opciones que pasan por votación/selección antes de continuar el flujo.

## Enviar a revisión
Decisión de un aprobador que lleva la solicitud a `NEEDS_REVISION`, expira decisiones restantes y solicita corrección al solicitante.

## Corregir / reenviar
Modificar una solicitud corregible conservando su tipo. Autoridad: solicitante original o Administrador del sistema.

## Acción pendiente
Tarea contextual:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No es un Permiso IAM.

## Delegación de cierre/factura
Autoridad explícita sobre una solicitud concreta para gestionar factura/cierre. No es un Rol ni un Permiso global.

## Administrador del sistema
Cuenta protegida por `system_accounts`. En producción tiene política `requests:read + areas:manage + config:manage`.

## Compatibilidad

Pueden existir campos/tablas/bridges legacy en código mientras se completa modularización. Solo deben documentarse como compatibilidad cuando realmente existan y nunca redefinen los términos anteriores.
