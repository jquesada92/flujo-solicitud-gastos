# Solicitudes múltiples y votación de cotizaciones

## Contrato

Una solicitud `MULTI_QUOTE` entra en `QUOTATION_VOTING` y conserva al menos dos opciones. Cada opción requiere proveedor, monto y soporte mediante URL o archivo válido.

La población votante se congela al abrir cada ronda:

```text
Usuario activo
+ permiso efectivo requests:approve
- solicitante original
→ QuotationVotingInvitation
```

Cargo, nombres organizacionales y permisos directos no participan en la selección.

## Voto

Un voto requiere simultáneamente:

- solicitud en `QUOTATION_VOTING`;
- permiso efectivo `requests:approve`;
- invitación de la ronda vigente;
- opción perteneciente a la solicitud;
- soporte válido en todas las opciones.

Cada usuario mantiene un voto activo por solicitud. Cambiar de opción actualiza ese voto y registra un `QuotationVoteEvent` con la selección anterior y la nueva.

## Resolución

La ronda espera el voto de todas las invitaciones congeladas. Cuando todos han votado:

- un ganador único selecciona la cotización y lleva la solicitud a `APPROVED`;
- un empate mantiene la ronda abierta hasta que un participante cambie su voto;
- una opción ajena se rechaza con 422;
- un usuario fuera de la población recibe 403;
- votar cuando la ronda ya cerró recibe 409.

## Inicio y Seguimiento

`QUOTATION_VOTE` aparece en Inicio solo para un invitado que aún no votó. La solicitud continúa visible en Seguimiento para usuarios activos aunque la acción personal ya se haya completado.

## Corrección

Corregir una solicitud múltiple conserva el tipo, rehidrata opciones y soportes, crea un nuevo `flow_id`, congela una población nueva y no reutiliza votos/invitaciones anteriores como estado activo.

## Escenarios locales

`docker compose exec -T backend python -m app.demo_monitoring` deja dos casos persistentes únicamente en el PostgreSQL local aislado:

- votación abierta con tres opciones y cero votos;
- votación abierta con tres opciones y un voto parcial.

Las credenciales y el procedimiento están en [VALIDACION_LOCAL.md](VALIDACION_LOCAL.md).
