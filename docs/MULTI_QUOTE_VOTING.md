# Solicitudes múltiples y votación de cotizaciones

## Contrato

Una solicitud `MULTI_QUOTE` entra en `QUOTATION_VOTING` y conserva al menos dos
opciones. Cada opción requiere proveedor, monto y soporte mediante URL o archivo
válido. FastAPI evalúa la regla usando el monto máximo de todas las opciones.

La población votante se congela al abrir cada ronda:

```text
Usuario activo
+ permiso efectivo requests:approve
- target de Rol/Grupo de la regla, cuando existe
- solicitante original
→ QuotationVotingInvitation
```

Una regla del Área precede a `ALL`. Seleccionar un Grupo expande Usuarios
asignados a cualquiera de sus Roles activos y las coincidencias se deduplican.
Cargo, `GroupMember`, nombres organizacionales, perfiles legacy y permisos
directos no participan. Sin regla aplicable se invita a toda la población IAM.

Regla, modalidad, monto máximo evaluado y quórum se congelan por ronda. Sobre
`N` invitados, `ANY=1`, `MAJORITY=floor(N/2)+1` y `ALL=N`.

## Voto

Un voto requiere simultáneamente:

- solicitud en `QUOTATION_VOTING`;
- permiso efectivo `requests:approve`;
- invitación de la ronda vigente;
- opción perteneciente a la solicitud;
- soporte válido en todas las opciones.

Cada usuario mantiene un voto activo por solicitud. Cambiar de opción actualiza ese voto y registra un `QuotationVoteEvent` con la selección anterior y la nueva.

## Resolución

Con una regla aplicable, alcanzar el quórum no cambia el estado: la ronda sigue
en `QUOTATION_VOTING`. Si además existe un líder único, solo el Solicitante
original obtiene cierre anticipado y puede cargar la factura. Los invitados que
faltan pueden votar y cualquiera puede cambiar su voto mientras no exista
factura y el estado siga abierto; cada cambio recalcula líder y capacidad de
cierre. Un empate nunca habilita el cierre.

Sin regla aplicable se requieren los votos de los `N` invitados y un líder único.
Cumplirlos tampoco cambia el estado: la ronda permanece en
`QUOTATION_VOTING`. Como ya no es un cierre anticipado, pueden registrar la
factura el Solicitante original, `system_accounts` o un delegado activo de esa
solicitud. Si falta un voto o hay empate, el cierre responde `409` sin persistir
factura ni fijar `selected_quotation_id`.

En ambos caminos:

- un líder único representa una selección provisional, nunca una aprobación;
- un empate elimina la selección provisional y bloquea la factura;
- cada invitado conserva **Votar o cambiar voto** y el resultado se recalcula sin
  crear un segundo voto activo;
- una opción ajena se rechaza con `422`;
- un Usuario fuera de la población recibe `403`;
- la carga de factura bloquea la solicitud y vuelve a calcular población, quórum
  y líder antes de persistir;
- cierre, ganador y factura son una unidad que pasa directamente a `CLOSED`;
- votar después del cierre recibe `409`.

## Inicio y Seguimiento

`QUOTATION_VOTE` aparece en Inicio como **Votar o cambiar voto** para todo
invitado mientras la ronda esté abierta, incluso después de votar. La UI marca
el voto actual, permite escoger otra opción y avisa si existe empate o ganador
provisional. Seguimiento conserva la visibilidad de la solicitud.

En la columna **Monto**, Seguimiento usa un valor operativo: antes del primer
voto muestra el máximo de las cotizaciones, durante la votación muestra el monto
del líder único y, si hay empate, vuelve a mostrar el máximo presentado. Este
valor no selecciona proveedor ni sustituye el monto financiero de cierre.

Con política, el botón de cierre anticipado solo se ofrece al Solicitante cuando
hay quórum y líder único. Sin política, se ofrece a las relaciones ordinarias de
cierre únicamente después de todos los votos y con líder único. El backend
siempre revalida el resultado.

## Corrección

Corregir una solicitud múltiple conserva el tipo, rehidrata opciones y soportes,
crea un nuevo `flow_id`, reevalúa el monto máximo y la política y congela nueva
población/quórum. No reutiliza votos o invitaciones anteriores como estado
activo.

## Escenarios locales

`docker compose exec -T backend python -m app.demo_monitoring` deja dos casos persistentes únicamente en el PostgreSQL local aislado:

- votación abierta con tres opciones y cero votos;
- votación abierta con tres opciones y un voto parcial.

Las credenciales y el procedimiento están en [VALIDACION_LOCAL.md](VALIDACION_LOCAL.md).

La migración `20260825_0012_keep_quotation_voting_open` devuelve a
`QUOTATION_VOTING` las solicitudes múltiples antiguas en `APPROVED` que no tienen
factura. Solicitudes ya cerradas o con factura no se modifican.

Esa revisión y la rama `20260827_0012_scoped_approval_policies →
20260828_0013_direct_expenses` permanecen inmutables. La revisión
`20260828_0014_merge_main_layout_heads` une ambas ramas y deja un solo head.
