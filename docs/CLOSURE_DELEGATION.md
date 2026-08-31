# Cierre, factura y delegación por solicitud

## Regla

Cerrar una solicitud, registrar su factura o reemplazarla es una capacidad por recurso.

```text
actor autorizado =
    solicitante original
 OR Administrador del sistema
 OR delegado activo de esa solicitud
```

## Estados

### APPROVED

En `SIMPLE`, un actor autorizado puede adjuntar factura, registrar notas y cerrar.

### QUOTATION_VOTING

En `MULTI_QUOTE`, un actor autorizado puede adjuntar factura solo cuando todos
los invitados votaron y existe un ganador único provisional. La API recalcula
bajo bloqueo; votos pendientes o empate producen 409 sin guardar archivo. Una
factura válida lleva la solicitud directamente a `CLOSED`.

### CLOSED

Un actor autorizado puede reemplazar/corregir la factura vigente con motivo, conservando la evidencia anterior.

## Capacidades

```text
can_close
can_delegate_close
```

`can_close` exige `APPROVED` para `SIMPLE`, ganador provisional en
`QUOTATION_VOTING` para `MULTI_QUOTE`, o `CLOSED` para corregir factura, además
de la relación autorizada. `can_delegate_close` corresponde al solicitante
original cuando esa misma operación es viable.

## Delegación

Persistencia: `expense_closure_delegations`.

- una sola delegación activa por solicitud;
- cambiar delegado revoca la anterior antes de crear la nueva;
- el historial no se borra;
- delegado debe estar activo, no ser el solicitante ni una cuenta técnica;
- el delegado no administra la delegación;
- la autoridad no se extiende a otras solicitudes.

API:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
POST   /api/expenses/{request_id}/close
PUT    /api/expenses/{request_id}/invoice
```

## Inicio y Solicitudes

Cuando existe `CLOSE_REQUEST`, Inicio puede ofrecer carga de factura/cierre y, si `can_delegate_close`, el botón de delegación. La misma regla se reutiliza en la vista de Solicitudes.

## Seguridad

El backend llama al resolver de autoridad por recurso y no confía en botones visibles. La capacidad no se deriva de Cargo, nombre de Rol ni flags de sesión.

## Pruebas manuales

1. solicitante de SIMPLE/APPROVED puede cerrar/delegar;
2. MULTI_QUOTE empatada rechaza factura y no ofrece cierre;
3. MULTI_QUOTE con ganador provisional puede cerrar con factura;
4. delegado activo puede cerrar pero no administrar delegación;
5. tercero no delegado no puede cerrar;
6. revocación elimina inmediatamente la autoridad del delegado;
7. reemplazo en CLOSED conserva versión anterior y motivo.
