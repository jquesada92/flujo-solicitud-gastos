# Especificación funcional — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución:** 2.8.0

## Objetivo

Mantener informado al usuario sobre su configuración de acceso cuando se crea su cuenta o cambia su Cargo/Posición.

## F-010-01 — Invitación de usuario

Cuando se crea un usuario activo, el mismo correo que contiene la contraseña temporal debe incluir:

- Cargo(s) activo(s) asignado(s);
- permisos efectivos vigentes después de aplicar Cargo, Grupo, Rol y permisos directos;
- código técnico del permiso junto a un nombre legible;
- enlace de acceso.

La contraseña temporal conserva su política existente de cambio obligatorio al primer inicio de sesión.

## F-010-02 — Cambio de Cargo

Cuando `position_ids` cambia realmente para un usuario activo mediante IAM, el usuario recibe un correo de **Actualización de cargo y permisos** con:

- Cargo(s) activo(s) resultante(s);
- permisos efectivos recalculados;
- aclaración de que los permisos pueden provenir de Cargo, Grupo, Rol o asignación directa;
- enlace al sistema.

Guardar exactamente el mismo conjunto de Cargos no genera un correo duplicado.

## F-010-03 — Fuente de verdad

El correo nunca usa `can_*`, `UserRole`, `title` legacy ni nombres hardcodeados como fuente de permisos.

Los permisos mostrados salen de `effective_permission_codes()` y los Cargos de `UserPosition → Position`.

## F-010-04 — Múltiples Cargos

Si el usuario tiene varios Cargos, el correo lista todos los Cargos activos ordenados por nombre.

Si no tiene Cargo, se muestra **Sin cargo asignado**.

## F-010-05 — Fallo de entrega

La invitación inicial conserva el comportamiento actual: si no puede enviarse, la creación no se confirma.

El cambio de Cargo también requiere entrega exitosa para confirmarse; si el proveedor falla, la transacción se revierte y el endpoint devuelve error 502.

Esta política puede evolucionar a outbox/reintentos persistentes en una feature futura.

## Seguridad

- nunca incluir hashes, secretos internos ni fuentes sensibles en el correo;
- la contraseña temporal solo aparece en la invitación inicial;
- el correo de cambio de Cargo nunca incluye contraseña;
- `config:manage` system-only no aparece como permiso efectivo de usuarios ordinarios aunque exista una asignación legacy.

## Fuera de alcance

- notificar cada cambio de Grupo/Rol/permiso directo sin cambio de Cargo;
- notificar cambios de Roles asociados a un Cargo a todos sus ocupantes;
- outbox/reintentos persistentes;
- historial de emails dentro de la UI.
