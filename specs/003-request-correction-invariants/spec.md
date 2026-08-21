# Spec 003 — Corrección de solicitudes

**Estado:** Implementada  
**Constitución:** 2.11.0

## Objetivo

Permitir corregir y reenviar una solicitud sin cambiar accidentalmente su tipo, propiedad ni evidencia.

## Autoridad

Solo:

```text
solicitante original
OR Administrador del sistema protegido
```

`requests:create`, `requests:approve` o pertenecer a un Grupo no otorgan propiedad de una solicitud ajena.

## Invariantes

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

No corregibles: `CLOSED`, `CANCELLED`.

## MULTI_QUOTE

La corrección restaura opciones/evidencias vigentes, crea una nueva ronda/`flow_id` y no reutiliza votos o invitaciones como estado activo. Los aprobadores de la nueva ronda se resuelven por `requests:approve`, excluyendo al solicitante.

## Frontend

`expense-form.jsx` deriva el modo de corrección desde la solicitud seleccionada, no desde la pestaña de creación que el usuario visitó antes.
