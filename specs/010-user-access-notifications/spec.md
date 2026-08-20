# Especificación funcional — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución vigente:** 2.9.0

## Objetivo

Mantener informado al usuario sobre su configuración de acceso cuando se crea su cuenta o cambia su Cargo/Posición desde la superficie canónica **Configuración → Accesos**.

## F-010-01 — Invitación de usuario

Cuando se crea un usuario activo desde **Accesos**, el correo que contiene la contraseña temporal incluye:

- Cargo(s) activo(s) asignado(s);
- permisos efectivos vigentes después de aplicar Cargo, Grupo, Rol y permisos directos;
- código técnico del permiso junto a nombre legible;
- enlace de acceso.

La contraseña temporal conserva cambio obligatorio al primer inicio.

## F-010-02 — Cambio de Cargo

Cuando `position_ids` cambia realmente para un usuario activo desde **Accesos**, recibe **Actualización de cargo y permisos** con:

- Cargo(s) activo(s) resultante(s);
- permisos efectivos recalculados;
- aclaración de que el acceso puede provenir de Cargo, Grupo, Rol o asignación directa;
- enlace al sistema.

Guardar exactamente el mismo conjunto de Cargos no genera correo duplicado.

## F-010-03 — Fuente de verdad

El correo nunca usa `can_*`, `UserRole`, `title` legacy ni nombres hardcodeados como fuente de permisos.

Fuentes:

```text
Permisos → effective_permission_codes()
Cargos   → UserPosition → Position
```

## F-010-04 — Múltiples Cargos

Si el usuario tiene varios Cargos, el correo lista todos los Cargos activos ordenados por nombre. Si no tiene Cargo, muestra **Sin cargo asignado**.

## F-010-05 — Fallo de entrega

- invitación inicial fallida → creación no se confirma;
- cambio de Cargo fallido → rollback + 502.

La política puede evolucionar a outbox/reintentos persistentes.

## F-010-06 — Superficie administrativa vigente

Feature 011 consolidó Usuarios/Personas y Organigrama en Accesos.

Por tanto, esta feature no requiere ni documenta una pantalla Usuario independiente. Cualquier UX de creación/cambio de Cargo debe quedar disponible dentro de Accesos.

## Seguridad

- nunca incluir hashes o secretos internos;
- contraseña temporal solo en invitación inicial;
- correo de cambio de Cargo nunca incluye contraseña;
- `config:manage` system-only no aparece como permiso efectivo de usuarios ordinarios;
- notificar no sustituye autorización backend.

## Fuera de alcance

- notificar cada cambio de Grupo/Rol/permiso directo sin cambio de Cargo;
- notificar cambios de Roles de un Cargo a todos sus ocupantes;
- outbox/reintentos persistentes;
- historial de emails dentro de UI.
