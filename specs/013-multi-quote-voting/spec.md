# Spec 013 — Solicitudes múltiples y votación

**Estado:** Implementada
**Constitución:** 2.13.0

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
6. Solo un ganador único lleva la solicitud a `APPROVED`.
7. Un empate conserva `QUOTATION_VOTING`.
8. Una ronda cerrada rechaza nuevos votos.
9. Corregir conserva `MULTI_QUOTE`, cambia `flow_id` y no reutiliza votos/invitaciones activos.

## Acciones pendientes

`QUOTATION_VOTE` existe únicamente para un invitado que todavía no votó en la ronda activa. Completar el voto elimina la acción personal, no la visibilidad de Seguimiento.

## Persistencia

```text
expenses.request_type = MULTI_QUOTE
quotation_options
quotation_voting_invitations
quotation_votes
quotation_vote_events
```

## Validación local

`python -m app.demo_monitoring` crea una ronda abierta sin votos y otra con voto parcial, ambas con tres opciones y datos persistentes visibles.
