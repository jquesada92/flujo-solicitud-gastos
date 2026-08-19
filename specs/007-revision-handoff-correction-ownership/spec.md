# Especificación funcional — Propiedad de corrección y envío a revisión

**Feature:** 007  
**Constitución:** 2.6.0

## Objetivo

Separar de forma explícita dos responsabilidades distintas del flujo:

```text
Aprobador detecta un problema
→ Enviar a revisión + comentario

Solicitante recibe la revisión
→ Corregir / reenviar
```

Un usuario que revisa o aprueba una solicitud ajena nunca debe editar directamente esa solicitud por el solo hecho de tener permisos de creación/aprobación.

## F-007-01 — Quién puede corregir

**Corregir / reenviar** una solicitud solo puede ser ejecutado por:

1. el solicitante original; o
2. el Administrador del sistema protegido mediante `system_accounts`.

La autorización es por recurso y no deriva de un permiso global.

No autorizan corrección de solicitudes ajenas:

- `requests:create`;
- `requests:approve`;
- `config:manage`;
- Grupo;
- Rol;
- Cargo/Posición;
- `UserRole` o `can_*` legacy.

## F-007-02 — Capacidad `can_correct`

`GET /api/expenses` debe devolver `can_correct` calculado por backend para cada solicitud y usuario autenticado.

La interfaz muestra **Corregir / reenviar** solo cuando `can_correct=true`.

El endpoint de resubmit vuelve a autorizar siempre, aunque un cliente manipule la UI.

## F-007-03 — Estados corregibles

Son corregibles por los actores autorizados:

- `QUOTATION_VOTING`;
- `SUBMITTED`;
- `PENDING_APPROVAL`;
- `NEEDS_REVISION`;
- `APPROVED`;
- `REJECTED`.

No son corregibles:

- `CLOSED`;
- `CANCELLED`.

Las reglas existentes de preservación SIMPLE/MULTI_QUOTE continúan aplicando.

## F-007-04 — Enviar a revisión

Un aprobador con un paso `PENDING` que detecte un problema debe utilizar **Enviar a revisión** y escribir un comentario indicando qué debe revisar/corregir el solicitante.

El comentario es obligatorio y debe tener al menos 3 caracteres útiles.

`REVISION_REQUESTED` es una **interrupción inmediata del flujo**, no una respuesta sometida a mayoría.

Una sola acción válida debe:

1. marcar el paso del aprobador como `REVISION_REQUESTED`;
2. persistir su comentario y actor/timestamp;
3. llevar la solicitud inmediatamente a `NEEDS_REVISION`;
4. expirar las aprobaciones `PENDING/WAITING` restantes de esa ronda;
5. notificar al solicitante incluyendo el comentario;
6. crear para el solicitante la tarea contextual `CORRECT_REQUEST`.

## F-007-05 — Responsable de la tarea de corrección

Cuando una solicitud entra en `NEEDS_REVISION`, la tarea personal **Corregir / reenviar** pertenece al solicitante original.

El Administrador del sistema conserva facultad administrativa para ejecutar la corrección desde la lista de solicitudes, pero esa excepción no convierte al administrador en responsable normal de la tarea del dashboard.

Los demás aprobadores no reciben `CORRECT_REQUEST`.

## F-007-06 — Lenguaje de la interfaz

Los controles deben distinguir claramente:

- **Enviar a revisión**: acción del aprobador/revisor;
- **Corregir / reenviar**: acción del solicitante/Admin del sistema.

No utilizar **Solicitar corrección** como etiqueta de acción cuando pueda confundirse con el editor de corrección.

En el correo de aprobación deben existir opciones equivalentes a:

```text
Aprobar
Rechazar
Enviar a revisión
```

Al seleccionar **Enviar a revisión**, la pantalla debe exigir el comentario antes de confirmar.

## F-007-07 — Corrección MULTI_QUOTE por Administrador del sistema

Si el Administrador del sistema corrige una MULTI_QUOTE ajena, la nueva población de votación debe seguir excluyendo al **solicitante original**, no al actor administrativo que ejecutó la corrección.

## Seguridad

La ruta `PUT /api/expenses/{request_id}/resubmit` requiere autenticación y aplica la regla solicitante/Admin del sistema en backend.

No debe depender de `requests:create` para autorizar edición de una solicitud existente.

La cuenta técnica se reconoce por `system_accounts`, nunca por email, Cargo o `UserRole.ADMIN`.

## Fuera de alcance

- cambiar la fórmula de mayoría para `APPROVED`/`REJECTED` más allá de separar `REVISION_REQUESTED`;
- permitir que cualquier usuario de solo lectura envíe a revisión;
- crear un permiso IAM nuevo `requests:correct`;
- permitir editar una solicitud ajena por pertenecer a un Grupo/Cargo específico;
- cambiar SIMPLE ↔ MULTI_QUOTE durante corrección;
- agregar/eliminar opciones estructuralmente durante una corrección MULTI_QUOTE.
