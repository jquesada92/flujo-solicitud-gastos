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

Un actor autorizado puede adjuntar factura, registrar notas y cerrar.

### CLOSED

Un actor autorizado puede reemplazar/corregir la factura vigente con motivo, conservando la evidencia anterior.

## Capacidades

```text
can_close
can_delegate_close
```

`can_close` exige estado `APPROVED` o `CLOSED` y relación autorizada con la solicitud. `can_delegate_close` corresponde al solicitante original cuando la delegación es operativamente válida.

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

1. solicitante de APPROVED puede cerrar/delegar;
2. delegado activo puede cerrar pero no administrar delegación;
3. tercero no delegado no puede cerrar;
4. revocación elimina inmediatamente la autoridad del delegado;
5. reemplazo en CLOSED conserva versión anterior y motivo.
