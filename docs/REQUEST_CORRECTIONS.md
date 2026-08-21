# Correcciones, reenvío y handoff de revisión

## Dos acciones distintas

```text
Aprobador detecta problema
→ Enviar a revisión

Solicitante recibe NEEDS_REVISION
→ Corregir / reenviar
```

Enviar a revisión no concede edición al aprobador.

## Autoridad de corrección

```text
solicitante original
OR Administrador del sistema
```

El backend calcula `can_correct` y vuelve a autorizar en la mutación. Un permiso global o pertenecer a un Grupo no convierte al actor en propietario de una solicitud ajena.

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

No corregibles:

```text
CLOSED
CANCELLED
```

## Enviar a revisión

Requiere aprobación PENDING, autoridad de aprobación y comentario de al menos 3 caracteres.

Resultado:

```text
aprobación actual       → REVISION_REQUESTED
solicitud               → NEEDS_REVISION
otros PENDING/WAITING   → EXPIRED
solicitante             → CORRECT_REQUEST
```

## Tipo de solicitud

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

El estado previo de las pestañas de creación no decide el modo de corrección. `expense-form.jsx` rehidrata el request seleccionado y determina el layout.

## MULTI_QUOTE

La corrección:

- restaura opciones y soportes existentes;
- conserva la cantidad de opciones según el contrato actual;
- permite editar contenido;
- crea nueva ronda/`flow_id`;
- deja votos/invitaciones anteriores fuera del estado activo;
- vuelve a resolver participantes mediante `requests:approve`;
- excluye al solicitante original.

## Persistencia actual

La instalación vigente parte de `20260820_0001_initial_schema` y evoluciona con 0002/0003 para reglas IAM/organizacionales. La corrección es una regla de negocio sobre el modelo actual y no depende de reconstruir una historia de migraciones anterior.

## Validación manual

- aprobador no ve edición de solicitud ajena;
- Enviar a revisión exige comentario;
- requester recibe CORRECT_REQUEST;
- SIMPLE y MULTI_QUOTE conservan tipo;
- actor no autorizado recibe 403;
- CLOSED/CANCELLED no permiten corrección.
