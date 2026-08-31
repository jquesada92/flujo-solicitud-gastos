# Terminología funcional

## Usuario
Cuenta autenticable que interactúa con el producto.

## Grupo
Ámbito organizacional opcional que puede tener cero o más Roles y Permisos heredables. La membresía de un Usuario se deriva únicamente de sus Roles agrupados y no autoriza por sí sola.

## Rol
Conjunto de Permisos propios. Puede ser global o pertenecer a máximo un Grupo. Un Usuario puede tener máximo un Rol por Grupo; si está agrupado, suma los Permisos del Grupo sin `DENY`. Puede definir un máximo opcional de Usuarios activos asignados; los inactivos conservan el Rol sin consumir cupo.

## Rol global
Rol sin Grupo. Puede asignarse a un Usuario sin crear membresía de Grupo. Un Usuario puede tener varios Roles globales ordinarios.

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
Baseline del usuario activo, más Permisos propios de sus Roles globales activos y la unión de Permisos propios/heredados de sus Roles agrupados activos dentro de Grupos activos, aplicando la política de cuenta técnica/system-only. Un Grupo inactivo suspende ambas contribuciones de sus Roles agrupados.

## Cargo / Posición
Metadato organizacional descriptivo. Un Usuario puede tener máximo un Cargo. Cargo no concede acceso.

## Accesos
Consola de Usuarios, Grupos, Roles y Permisos. El Usuario recibe acceso mediante máximo un Rol por Grupo y cero o más Roles globales, guardando explícitamente.

## Inicio
Vista personal: mis acciones, mis solicitudes y métricas propias.

## Seguimiento
Vista de equipo de solo lectura: Grupos, miembros derivados de Roles agrupados, Roles y cantidades de acciones pendientes. Los Roles globales no crean membresía en esta vista.

## Área
Contexto organizacional asociado al gasto. Campo: `expense_area`.

## Categoría
Naturaleza del bien/servicio. Campo: `expense_category`.

## Solicitud SIMPLE
Una opción principal de compra/proveedor.

## Solicitud MULTI_QUOTE
Varias opciones que pasan por votación/selección antes de continuar el flujo.

## Regla de aprobación

Política de un Área o `ALL` y una banda `(min_amount,max_amount]`. En modalidades
`ANY`, `MAJORITY` o `ALL` acota por Roles/Grupos a Usuarios que ya tienen
`requests:approve` y define el quórum. `NO_APPROVAL` no tiene targets ni ronda.

## Gasto directo

Registro final de Área, proveedor, ítem, monto y factura bajo una banda
`NO_APPROVAL`. No es una Solicitud, no crea `Expense` y no tiene estado,
aprobadores, votantes, corrección, delegación o cierre.

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
Cuenta protegida por `system_accounts`. También se representa mediante el Rol global técnico `system-administrator`, sin Grupo. En producción la autoridad protegida tiene política `requests:read + areas:manage + config:manage`.

## Compatibilidad

Pueden existir campos/tablas/bridges legacy en código mientras se completa modularización. Solo deben documentarse como compatibilidad cuando realmente existan y nunca redefinen los términos anteriores.
