# Spec 013 — Solicitudes múltiples y votación

**Estado:** Implementada
**Constitución:** 2.21.0

## Objetivo

Permitir comparar varias cotizaciones mediante una ronda auditable cuya población y opciones pertenezcan a una solicitud concreta.

## Creación

Una solicitud `MULTI_QUOTE`:

- contiene entre 2 y 10 opciones;
- exige proveedor, monto y soporte por opción;
- rechaza URLs duplicadas;
- entra en `QUOTATION_VOTING`;
- congela invitaciones para usuarios activos con `requests:approve`, excluyendo al solicitante.

## Autoridad

Para votar se requiere permiso efectivo `requests:approve` e invitación de la ronda. Cargo, flags legacy, nombres de Rol y permisos directos no autorizan.

## Invariantes

1. La opción votada pertenece a la solicitud.
2. Todas las opciones tienen soporte válido.
3. Existe un solo voto activo por usuario/solicitud.
4. Cada cambio de voto agrega un evento inmutable.
5. La ronda espera a todos los invitados.
6. Un ganador único es provisional y conserva `QUOTATION_VOTING`.
7. Un empate conserva `QUOTATION_VOTING`, limpia la selección provisional y bloquea la factura.
8. Todo invitado puede cambiar su voto mientras la ronda siga abierta; cada cambio agrega un evento.
9. Subir la factura exige población completa y ganador único recalculado bajo bloqueo; entonces pasa directamente a `CLOSED`.
10. Una ronda cerrada rechaza nuevos votos.
11. Corregir conserva `MULTI_QUOTE`, cambia `flow_id` y no reutiliza votos/invitaciones activos.

## Acciones pendientes

`QUOTATION_VOTE` existe para todo invitado durante la ronda activa y se presenta
como **Votar o cambiar voto**. Votar no elimina la acción: solo la factura y el
cierre de la ronda lo hacen. El solicitante recibe `CLOSE_REQUEST` únicamente
cuando hay ganador provisional; el backend vuelve a validar que no exista empate.

## Monto operativo en Seguimiento

El monto mostrado para una solicitud `MULTI_QUOTE` no convierte una cotización
en selección definitiva. Sin votos muestra el máximo de las opciones
presentadas; con votos y un líder único muestra el monto de esa opción; si los
líderes están empatados muestra nuevamente el máximo de todas las opciones.
`Expense.amount` conserva su significado financiero canónico y solo refleja una
cotización seleccionada cuando la ronda completa tiene ganador provisional.

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

## Validación local

La prueba automatizada `tests.test_multi_quote_open_voting` cubre empate, cambio
de voto, selección provisional, bloqueo de factura y cierre. PostgreSQL local
debe confirmar la migración como head. `app.demo_monitoring` conserva escenarios
visibles de ronda sin votos y voto parcial cuando se solicita esa validación mutante.
