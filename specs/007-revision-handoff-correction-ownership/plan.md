# Plan técnico — Propiedad de corrección y envío a revisión

**Feature:** 007  
**Constitución:** 2.6.0

## Backend

### Capacidad por recurso

Agregar `can_correct` a `ExpenseOut`.

`can_correct_expense(db, expense, user)` debe devolver `true` únicamente cuando:

```text
status ∈ CORRECTABLE_STATUSES
AND (
  user.email == expense.requested_by
  OR user está en system_accounts
)
```

`CORRECTABLE_STATUSES`:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

`CLOSED` y `CANCELLED` deben devolver `false`.

`tracking.py` calcula `can_correct` una vez por solicitud usando el mismo `system_admin` precalculado que `can_cancel`.

### Resubmit

`PUT /api/expenses/{request_id}/resubmit` deja de depender de `require_permission('requests:create')` y usa `current_user` + `can_correct_expense()`.

Un tercero debe recibir `403` aun si tiene `requests:create` o `requests:approve`.

La cuenta técnica de producción puede corregir como excepción administrativa aunque su IAM efectivo no contenga `requests:create`.

### MULTI_QUOTE

Al regenerar votantes usar:

```text
exclude_email = expense.requested_by
```

No usar el correo del actor que ejecutó la corrección.

## Enviar a revisión

`approval_engine.apply_decision()` trata `REVISION_REQUESTED` antes de la evaluación de mayoría.

Secuencia:

```text
validar comentario >= 3
approval.status = REVISION_REQUESTED
expense.status = NEEDS_REVISION
record STEP_REVISION_REQUESTED
expire_open_approvals(except current approval)
commit
send_final_notification(expense)
```

No calcular `revision_count` ni exigir threshold para esta transición.

La aprobación/rechazo conservan la lógica de mayoría vigente y su deuda funcional documentada.

## Dashboard

`pending_action_service.py` genera `CORRECT_REQUEST` por propiedad:

```text
Expense.status == NEEDS_REVISION
AND Expense.requested_by == current_user.email
```

No requiere `requests:create` para esa tarea concreta.

El Administrador del sistema puede corregir por capacidad administrativa desde Solicitudes, pero no recibe automáticamente `CORRECT_REQUEST` para solicitudes ajenas.

## Frontend

Mientras `ExpenseTable` permanezca en `main.jsx`, el transform temporal de Vite sustituye la visibilidad legacy:

```text
canEdit + status
```

por:

```text
x.can_correct
```

El montaje de `ExpenseForm` debe permitir modo corrección cuando existe `revision`, incluso si el usuario no tiene `requests:create` global (caso de la cuenta técnica productiva).

El modal de acciones cambia la etiqueta a **Enviar a revisión** y deshabilita esa acción hasta que `comment.trim().length >= 3`.

Los KPIs del dashboard permanecen informativos; solo las filas pendientes son interactivas.

## Correo

`send_approval_request()` usa:

```text
APROBAR
RECHAZAR
ENVIAR A REVISIÓN
```

El link continúa enviando `action=REVISION_REQUESTED`.

`send_final_notification()` incluye el comentario de revisión enviado al solicitante.

## Migraciones

No se requieren columnas/tablas nuevas.

La cadena Alembic permanece:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

## Pruebas

Backend:

- tercero con `requests:approve` no puede resubmit;
- solicitante puede resubmit por propiedad aunque no tenga `requests:create` global;
- Administrador del sistema conserva resubmit;
- una `REVISION_REQUESTED` en ronda MAJORITY pasa inmediatamente a `NEEDS_REVISION`;
- comentario vacío devuelve error;
- otras aprobaciones quedan `EXPIRED`;
- solicitante recibe `CORRECT_REQUEST`;
- otro aprobador no conserva acción pendiente;
- MULTI_QUOTE regenerada excluye al solicitante original.

Frontend contract:

- Vite usa `x.can_correct`;
- `ExpenseForm` puede montarse cuando existe `revision`;
- build usa **Enviar a revisión**;
- acción de revisión requiere comentario mínimo;
- filas pendientes/modal continúan funcionando.

## Validación local mientras GitHub Actions no tenga cuota

```powershell
cd backend
python -m unittest tests.test_multi_quote_revision -v
python -m unittest tests.test_pending_actions -v
python -m unittest tests.test_frontend_dashboard_contract -v
cd ..

cd frontend
npm run build
cd ..

docker compose build --no-cache frontend backend
docker compose up -d
```

Pruebas manuales:

1. usuario aprobador abre solicitud ajena → no ve **Corregir / reenviar**;
2. ese usuario puede **Enviar a revisión** desde su aprobación y debe escribir comentario;
3. solicitud pasa inmediatamente a `NEEDS_REVISION`;
4. solicitante ve `CORRECT_REQUEST` y **Corregir / reenviar**;
5. otro aprobador deja de tener la aprobación vigente;
6. Administrador del sistema puede corregir la solicitud desde Solicitudes;
7. después de reenviar, el solicitante no entra en su propia población MULTI_QUOTE.
