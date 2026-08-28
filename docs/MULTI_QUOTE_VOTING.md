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

El cierre fija la opción ganadora vigente y la factura y pasa directamente a
`CLOSED` como una unidad. Desde entonces cualquier voto recibe 409.

Sin regla aplicable, la ronda exige todos los votos y el Solicitante no puede
cerrar desde `QUOTATION_VOTING`. Al completar `N`, un ganador único selecciona la
cotización y lleva la Solicitud a `APPROVED`; un empate permanece abierto hasta
que un participante cambie su voto. Antes de `APPROVED`, cualquier `POST` de
cierre responde `409` sin guardar factura ni fijar `selected_quotation_id`,
incluso si quien lo envía es el Solicitante. En ambos caminos:

- una opción ajena se rechaza con 422;
- un Usuario fuera de la población recibe 403;
- votar cuando la ronda ya cerró recibe 409.

## Inicio y Seguimiento

`QUOTATION_VOTE` aparece en Inicio solo para un invitado que aún no votó. Aunque
la acción desaparezca tras su primer voto, el detalle conserva la opción de
cambiarlo mientras la ronda configurada siga abierta. La Solicitud continúa
visible en Seguimiento para Usuarios activos.

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
