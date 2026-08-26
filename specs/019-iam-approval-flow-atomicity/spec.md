# Spec 019 — Población IAM y creación atómica del flujo

**Estado:** Implementada

**Constitución:** 2.19.0

## Problema

Una solicitud `SIMPLE` podía ignorar usuarios con permiso efectivo
`requests:approve` cuando no existía una fila `ApprovalPolicy` aplicable y caer
en reglas legacy por correo. Si el soporte se cargaba en una segunda llamada y
el flujo no podía iniciarse, también podía quedar una solicitud sin ronda.

## Contrato

1. La población de una ronda `SIMPLE` se resuelve desde todos los Usuarios
   activos con permiso efectivo `requests:approve`, excluyendo al Solicitante.
2. Son equivalentes como fuente de ese permiso: Permiso propio de Rol global,
   Permiso propio de Rol agrupado y Permiso heredado de su Grupo activo.
3. La ausencia de `ApprovalPolicy` no deshabilita IAM ni obliga a usar una regla
   legacy. Sin política aplicable, la modalidad predeterminada es `MAJORITY`.
4. Si existe una política aplicable, puede definir la modalidad, pero sus
   nombres de perfiles legacy no seleccionan ni autorizan participantes.
5. Una solicitud nueva `SIMPLE` solo queda persistida cuando su soporte válido y
   su ronda de aprobación quedan confirmados. Si no puede crearse la ronda, la
   API responde con error y no deja `Expense`, `ExpenseAttachment` ni `Approval`.
6. Las notificaciones se intentan después del commit del flujo. Un fallo del
   proveedor de correo no revierte una ronda ya creada; requiere observabilidad
   y reintento, no una transacción distribuida ficticia.
7. Reglas secuenciales legacy por correo pueden permanecer físicamente, pero no
   crean aprobadores ni sustituyen el permiso efectivo `requests:approve`.

## Fuera de alcance

- Rediseñar la configuración visual de reglas de monto.
- Implementar outbox transaccional para correo.
- Eliminar las tablas físicas legacy en esta corrección.
