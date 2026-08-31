# Spec 021 — Reglas de aprobación por Área, audiencia y quórum

**Estado:** Implementada; modalidad sin ronda ampliada por Spec 022  
**Constitución:** 2.25.0
**Fecha:** 2026-08-27

## Objetivo

Permitir que una regla de monto determine, sin crear autoridad paralela a IAM,
qué Roles/Grupos participan y cuándo una votación `MULTI_QUOTE` puede cerrarse
con factura, manteniendo un fallback seguro cuando no exista regla aplicable.

Esta Spec sustituye las reglas de población y resolución de `MULTI_QUOTE` de la
Spec 013 y amplía la política de monto de la Spec 019. Las garantías de
invitación, auditoría, autorización efectiva y atomicidad de aquellas Specs se
conservan salvo donde esta Spec las reemplaza expresamente.

## Bandas y resolución de política

1. Una política activa pertenece a un Área concreta o al scope fallback `ALL`.
2. Su intervalo es `(min_amount, max_amount]`; `max_amount=NULL` no tiene límite
   superior y `max_amount` finito debe ser estrictamente mayor que `min_amount`.
3. Dos políticas activas del mismo scope no se superponen. Pueden tocarse en un
   límite porque ese monto pertenece únicamente al máximo de la banda anterior.
4. Políticas del Área concreta tienen precedencia sobre `ALL`. `ALL` solo se
   consulta cuando ninguna banda específica del Área contiene el monto.
5. Los huecos son válidos. Si no coincide una regla específica ni `ALL`, se usa
   el fallback IAM sin regla.
6. La validación anterior se aplica al crear, editar y activar, y el backend usa
   exactamente las mismas fronteras al resolver.

Estas bandas comparten scope con `NO_APPROVAL`: la Spec 022 agrega esa modalidad
sin ronda y la misma prohibición de overlap se aplica entre todas las políticas
activas, aunque tengan modalidades distintas. El resto de esta Spec describe
únicamente `ANY`, `MAJORITY` y `ALL`, que sí seleccionan participantes.

Para `SIMPLE`, el monto de evaluación es `Expense.amount`. Para `MULTI_QUOTE`,
es `max(QuotationOption.amount)`, calculado por FastAPI sobre todas las opciones
antes de congelar participantes. El cliente no decide ni puede sobrescribir ese
valor.

## Targets IAM

La política guarda `approver_role_ids` y `approver_group_ids` como identidades
persistentes, no nombres visibles. Esos targets acotan la población, pero nunca
conceden `requests:approve`.

Un participante debe cumplir simultáneamente:

- Usuario activo;
- permiso efectivo `requests:approve`;
- asignación activa a un Rol seleccionado o a un Rol activo perteneciente a un
  Grupo seleccionado;
- ser distinto del Solicitante.

Seleccionar un Grupo expande todos sus Roles activos y sus Usuarios activos
asignados. Si, por ejemplo, Junta Directiva contiene cinco Roles, los Usuarios
elegibles de los cinco quedan invitados. Un Usuario alcanzado por varios targets
recibe una sola invitación. `GroupMember` aislado, Cargo, nombres de entidades,
perfiles legacy y permisos directos a Usuario no participan.

Una regla aplicable sin ningún participante elegible no permite iniciar la
ronda. La creación falla como una unidad y no deja solicitud, opciones, soportes
o invitaciones huérfanos.

## Umbral e instantánea

Sea `N` la población deduplicada congelada al abrir la ronda:

```text
ANY      = 1
MAJORITY = floor(N / 2) + 1
ALL      = N
```

La solicitud conserva como evidencia inmutable de esa ronda:

```text
approval_policy_id       # identidad histórica, sin FK destructiva
approval_policy_mode
policy_evaluation_amount
minimum_votes_required
```

Editar, desactivar o eliminar la política después no recalcula una ronda
abierta. Corregir y reenviar crea un `flow_id` nuevo, vuelve a evaluar monto y
política, y congela población y umbral nuevos.

## MULTI_QUOTE con regla

1. Cada opción conserva proveedor, monto y soporte válido.
2. Cada invitado mantiene un voto activo y todo cambio de opción agrega evento.
3. Alcanzar el umbral no cambia el estado: la solicitud sigue en
   `QUOTATION_VOTING`.
4. El cierre anticipado requiere simultáneamente quórum y un líder único.
5. Solo el Solicitante original recibe `can_close` en ese estado. La cuenta
   técnica y un delegado conservan su autoridad ordinaria únicamente desde
   `APPROVED`/`CLOSED`.
6. Mientras no se haya cargado la factura y el estado siga abierto, todos los
   invitados pueden votar o cambiar su voto, también después del quórum.
7. Un cambio posterior puede crear o romper el empate; `can_close` se recalcula
   desde el conteo vigente.
8. Cerrar adjunta la factura, fija el ganador final y pasa directamente a
   `CLOSED` en una sola unidad de éxito. Después, votar recibe `409`.

## Fallback MULTI_QUOTE sin regla

Sin política aplicable se invita a todos los Usuarios activos con
`requests:approve`, excluyendo al Solicitante. Se exige el voto de los `N`
invitados y un líder único. Cumplir ambas condiciones no cambia el estado: la
solicitud permanece en `QUOTATION_VOTING` hasta que la factura la lleva
directamente a `CLOSED`. Como no se trata de un cierre anticipado, pueden cerrar
el Solicitante, `system_accounts` o un delegado activo. Mientras falte un voto o
exista empate, el `POST` de cierre responde `409`, no escribe una factura y no
fija `selected_quotation_id`.

## SIMPLE

Una política aplicable usa los mismos targets y su `approval_mode` para la ronda
de decisiones. Sin política, `SIMPLE` conserva el fallback de la Spec 019: todos
los Usuarios activos con `requests:approve`, menos el Solicitante, y modalidad
`MAJORITY`.

## Compatibilidad

`approver_profile_codes` queda como metadata física sin autoridad y deja de ser
un control de la pantalla. La migración `20260827_0012` desactiva políticas
legacy cuyos nuevos targets están vacíos. El resolver también las considera no
aplicables, de modo que nunca habilitan quórum o cierre anticipado; esas
solicitudes usan el fallback IAM hasta que un Administrador reconfigure y active
la regla con targets válidos.
