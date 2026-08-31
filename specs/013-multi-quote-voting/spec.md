# Spec 013 — Solicitudes múltiples y votación

**Estado:** Implementada; población y quórum ampliados por Spec 021
**Constitución:** 2.25.0

## Objetivo

Permitir comparar varias cotizaciones mediante una ronda auditable cuya población y opciones pertenezcan a una solicitud concreta.

## Creación

Una solicitud `MULTI_QUOTE`:

- contiene entre 2 y 10 opciones;
- exige proveedor, monto y soporte por opción;
- rechaza URLs duplicadas;
- entra en `QUOTATION_VOTING`;
- congela invitaciones según la regla aplicable y el fallback definidos por la
  Spec 021, siempre con `requests:approve` efectivo y excluyendo al solicitante.

## Autoridad

Para votar se requiere permiso efectivo `requests:approve` e invitación de la ronda. Cargo, flags legacy, nombres de Rol y permisos directos no autorizan.

## Invariantes

1. La opción votada pertenece a la solicitud.
2. Todas las opciones tienen soporte válido.
3. Existe un solo voto activo por usuario/solicitud.
4. Cada cambio de voto agrega un evento inmutable.
5. Toda ronda conserva `QUOTATION_VOTING` hasta que la factura la lleva
   directamente a `CLOSED`; un líder provisional nunca produce `APPROVED`.
6. Con regla, quórum y líder único habilitan cierre anticipado exclusivamente al
   Solicitante original.
7. Sin regla, se requieren todos los votos y líder único; entonces aplican las
   relaciones ordinarias de cierre por recurso.
8. Un empate conserva `QUOTATION_VOTING`, limpia la selección provisional y
   bloquea la factura.
9. Todo invitado conserva **Votar o cambiar voto** mientras la ronda siga abierta;
   cada cambio agrega un evento.
10. El cierre recalcula bajo bloqueo población, quórum y líder, persiste ganador
    y factura como una unidad y hace que votos posteriores reciban `409`.
11. Corregir conserva `MULTI_QUOTE`, cambia `flow_id`, reevalúa política/quórum y
    no reutiliza votos/invitaciones activos.

## Acciones pendientes

`QUOTATION_VOTE` existe para todo invitado durante la ronda activa y se presenta
como **Votar o cambiar voto**. Votar no elimina la acción: solo la factura y el
cierre de la ronda lo hacen. Con política, el Solicitante recibe `CLOSE_REQUEST`
al alcanzar quórum y líder único. Sin política, aparece para las relaciones
ordinarias solo cuando todos votaron y existe líder único. El backend revalida
siempre las condiciones.

## Monto operativo en Seguimiento

El monto mostrado para una solicitud `MULTI_QUOTE` no convierte una cotización
en selección definitiva. Sin votos muestra el máximo de las opciones
presentadas; con votos y un líder único muestra el monto de esa opción; si los
líderes están empatados muestra nuevamente el máximo de todas las opciones.
`Expense.amount` conserva su significado financiero canónico y no se modifica
para completar esta visualización.

## Persistencia

```text
expenses.request_type = MULTI_QUOTE
quotation_options
quotation_voting_invitations
quotation_votes
quotation_vote_events
```

La revisión `20260825_0012_keep_quotation_voting_open` normaliza solicitudes
anteriores `MULTI_QUOTE` en `APPROVED` sin factura para devolverlas a la ronda
abierta sin reescribir migraciones desplegadas.

La revisión `20260828_0014_merge_main_layout_heads` une esa rama con
`20260827_0012_scoped_approval_policies → 20260828_0013_direct_expenses` y deja
un único head sin reescribir ninguna revisión anterior.

## Validación local

La prueba automatizada `tests.test_multi_quote_open_voting` cubre empate, cambio
de voto, selección provisional, bloqueo de factura y cierre. PostgreSQL local
debe confirmar `20260828_0014` como único head. `app.demo_monitoring` conserva escenarios
visibles de ronda sin votos y voto parcial cuando se solicita esa validación mutante.
