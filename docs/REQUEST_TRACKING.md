# Seguimiento universal y cancelación de solicitudes

## Objetivo

Todo usuario activo y autenticado puede consultar el dashboard y las solicitudes de la organización para dar seguimiento, sin que la lectura dependa de haber creado la solicitud ni de pertenecer a un rol/grupo específico.

La lectura compartida no convierte las acciones mutables en universales.

## Baseline de lectura

`requests:read` es una capacidad base del producto para todo usuario activo.

```text
active user
  → requests:read
  → GET /api/expenses/dashboard
  → GET /api/expenses
```

Los demás permisos continúan siendo configurables:

```text
requests:create
requests:approve
requests:close
config:manage
```

## Dashboard

`GET /api/expenses/dashboard` muestra métricas compartidas de la organización.

`pending_my_action` es personal y solo incluye acciones ejecutables por el usuario actual:

- aprobaciones/votaciones cuando tiene `requests:approve` y está asignado/invitado;
- cierres cuando tiene `requests:close`.

## Lista de solicitudes

`GET /api/expenses` no filtra por `UserRole.REQUESTER` ni por `requested_by`.

La lista conserva el alcance operativo vigente y agrega capacidades por recurso. Actualmente:

```json
{
  "can_cancel": true
}
```

`can_cancel` es informativo para la UX; el endpoint de cancelación vuelve a autorizar siempre.

## Regla de cancelación

Una solicitud abierta puede ser cancelada únicamente por:

1. el solicitante original; o
2. el Administrador del sistema persistido en `system_accounts`.

No autoriza cancelación ajena tener:

- `requests:create`;
- `requests:approve`;
- `config:manage`;
- un cargo particular;
- un rol/grupo con un nombre específico;
- un `UserRole` legacy determinado.

### Estados abiertos cancelables

- `QUOTATION_VOTING`
- `SUBMITTED`
- `PENDING_APPROVAL`
- `NEEDS_REVISION`
- `APPROVED`

`APPROVED` sigue abierto porque aprobado no significa cerrado.

### Estados no cancelables

- `CLOSED`
- `CANCELLED`
- `REJECTED`

## API de cancelación

```text
POST /api/expenses/{request_id}/cancel
```

Payload:

```json
{
  "reason": "Motivo de la cancelación"
}
```

El motivo debe tener entre 3 y 1000 caracteres.

La operación:

1. bloquea la solicitud;
2. valida estado;
3. valida solicitante o `system_accounts`;
4. expira aprobaciones abiertas;
5. cambia estado a `CANCELLED`;
6. persiste `cancelled_at`, `cancelled_by` y `cancellation_reason`.

## Administrador del sistema en producción

La cuenta técnica conserva como permisos IAM efectivos únicamente:

```text
requests:read
config:manage
```

No recibe `requests:create`, `requests:approve` ni `requests:close` y no participa en decisiones financieras.

La cancelación administrativa es una regla explícita de ciclo de vida basada en la identidad protegida `system_accounts`; no se modela como uno de esos permisos financieros.

## Frontend

Mientras `ExpenseTable` permanezca dentro de `main.jsx`, el build reemplaza la condición legacy de cancelación por:

```text
x.can_cancel
```

El reemplazo es transitorio. El objetivo final es que el componente modular consuma directamente el contrato `can_cancel` sin transform de Vite.

## Pruebas

Cobertura principal:

- `backend/tests/test_universal_tracking.py`
- `backend/tests/test_request_cancellation.py`

Deben demostrar lectura universal sin mutación universal y la regla exacta solicitante/admin para cancelación.
