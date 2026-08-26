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

- un ganador único selecciona una cotización **provisional**, pero conserva la solicitud en `QUOTATION_VOTING`;
- un empate mantiene la ronda abierta, elimina cualquier selección provisional y bloquea la carga de factura;
- cada invitado puede cambiar su voto y el resultado se recalcula sin crear un segundo voto activo;
- una opción ajena se rechaza con 422;
- un usuario fuera de la población recibe 403;
- votar cuando la ronda ya cerró recibe 409.

La ronda no termina al completar los votos. El ganador sigue siendo provisional
porque un invitado puede cambiar su decisión. La carga de factura es el evento de
finalización: FastAPI bloquea la solicitud, vuelve a contar los votos y solo si
todos votaron y existe un ganador único persiste la factura y pasa directamente
a `CLOSED`. Ante empate o voto pendiente responde 409 y no crea el adjunto.

## Inicio y Seguimiento

`QUOTATION_VOTE` aparece en Inicio como **Votar o cambiar voto** para todo
invitado mientras la ronda esté abierta, incluso después de votar. La UI marca
el voto actual, permite escoger otra opción y avisa si existe empate o ganador
provisional. Seguimiento conserva la visibilidad de la solicitud.

En la columna **Monto**, Seguimiento usa un valor operativo: antes del primer
voto muestra el máximo de las cotizaciones, durante la votación muestra el monto
del líder único y, si hay empate, vuelve a mostrar el máximo presentado. Este
valor no selecciona proveedor ni sustituye el monto financiero de cierre.

El solicitante original, la cuenta técnica o el delegado activo pueden registrar
la factura conforme a la autoridad de cierre por recurso. El botón solo se
ofrece cuando hay ganador provisional; el backend siempre revalida el resultado.

## Corrección

Corregir una solicitud múltiple conserva el tipo, rehidrata opciones y soportes, crea un nuevo `flow_id`, congela una población nueva y no reutiliza votos/invitaciones anteriores como estado activo.

## Escenarios locales

`docker compose exec -T backend python -m app.demo_monitoring` deja dos casos persistentes únicamente en el PostgreSQL local aislado:

- votación abierta con tres opciones y cero votos;
- votación abierta con tres opciones y un voto parcial.

Las credenciales y el procedimiento están en [VALIDACION_LOCAL.md](VALIDACION_LOCAL.md).

La migración `20260825_0012_keep_quotation_voting_open` devuelve a
`QUOTATION_VOTING` las solicitudes múltiples antiguas en `APPROVED` que no tienen
factura. Solicitudes ya cerradas o con factura no se modifican.
