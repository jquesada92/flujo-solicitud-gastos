# Plan técnico — Correcciones de solicitudes

**Constitución:** 2.6.0

## Arquitectura

```text
frontend/src/expense-form.jsx
        ↓ PUT /api/expenses/{request_id}/resubmit
revision_actions.py
        ↓
can_correct_expense(request, user)
        ↓
Expense + QuotationOption + votes/invitations
```

La pestaña SIMPLE/MULTI_QUOTE de creación no es fuente de verdad para una corrección y `requests:create` tampoco es autoridad para editar una solicitud existente.

## Backend canónico

`app/api/revision_actions.py` es responsable de:

1. autenticar mediante `current_user`;
2. localizar la solicitud y validar `can_correct_expense()`;
3. autorizar únicamente solicitante original o Administrador del sistema (`system_accounts`);
4. validar Área + Categoría;
5. impedir corrección de `CLOSED`/`CANCELLED`;
6. derivar el tipo canónico desde `request_type` + evidencia durable;
7. rechazar cambios del tipo canónico;
8. invalidar aprobaciones abiertas del flujo anterior;
9. generar `flow_id` nuevo;
10. actualizar campos comunes;
11. reiniciar el flujo según el tipo canónico.

Un tercero con `requests:create`, `requests:approve` o `config:manage` recibe 403 y debe usar **Enviar a revisión** si tiene una aprobación asignada.

### Capacidad por recurso

```text
can_correct = status corregible
              AND (
                current_user.email == requested_by
                OR current_user ∈ system_accounts
              )
```

`tracking.py` expone `can_correct` por solicitud para que la tabla no infiera edición desde permisos globales.

### SIMPLE

- permanece `SIMPLE`;
- actualiza monto/proveedor/URL;
- conserva soportes existentes;
- reinicia aprobación cuando existe soporte suficiente.

### MULTI_QUOTE

- permanece `MULTI_QUOTE`;
- conserva la cantidad actual de `QuotationOption`;
- actualiza cada opción por orden existente;
- conserva attachments vinculados;
- limpia `QuotationVote` vigente;
- reemplaza `QuotationVotingInvitation`;
- conserva eventos históricos;
- limpia ganador/proveedor/monto seleccionado;
- vuelve a `QUOTATION_VOTING`;
- crea nuevas invitaciones desde `users_with_permission('requests:approve')`;
- siempre excluye `expense.requested_by`, no el correo del actor que ejecutó la corrección.

## Handoff desde revisión

Feature 007 define:

```text
Aprobador → Enviar a revisión + comentario
          → NEEDS_REVISION
          → solicitante recibe CORRECT_REQUEST
          → solicitante/Admin pueden Corregir / reenviar
```

`CORRECT_REQUEST` se calcula por propiedad de la solicitud, no por `requests:create`.

## Reparación de datos

Alembic `20260817_0003_backfill_multi_quote_request_type.py` repara filas históricas con evidencia MULTI_QUOTE y flag SIMPLE. No elimina evidencia.

Cadena global vigente:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

## Frontend canónico

`frontend/src/expense-form.jsx` calcula:

```text
effectiveRequestType = draft ? resolveRequestType(draft) : requestType
```

Durante corrección gobierna layout, validaciones, payload y uploads.

Mientras `ExpenseTable` siga en `main.jsx`, `vite.config.js` mantiene un bridge temporal para:

- usar `x.can_correct` al mostrar **Corregir / reenviar**;
- permitir montar `ExpenseForm` cuando existe `revision`, aunque el Administrador del sistema productivo no tenga `requests:create`;
- conservar la extracción estructural del `ExpenseForm` modular.

La autorización nunca depende de ese bridge: `resubmit` vuelve a validar en backend.

## Testing

`test_multi_quote_revision.py` verifica:

- solicitante/Admin pueden corregir;
- tercero aprobador no puede corregir;
- propiedad de la solicitud no depende de `requests:create` global;
- tipo SIMPLE/MULTI_QUOTE se conserva;
- evidencia se conserva;
- votos/invitaciones se reinician;
- solicitante original queda fuera de la nueva ronda.

`test_frontend_revision_contract.py` protege el editor modular y `test_frontend_dashboard_contract.py` protege el bridge `can_correct` mientras la tabla siga legacy.

## Validación manual

Además de la regresión de tipo:

1. aprobador ajeno no debe ver **Corregir / reenviar**;
2. solicitante debe verlo para su solicitud corregible;
3. Administrador del sistema debe poder verlo/ejecutarlo;
4. una solicitud enviada a revisión debe entregar la tarea al solicitante;
5. una MULTI_QUOTE corregida por Admin debe excluir al solicitante original de la nueva votación.

## Retiro futuro

Cuando `ExpenseTable` y el shell estén modularizados, retirar los transforms de compatibilidad de Vite y consumir `can_correct` directamente desde componentes normales.
