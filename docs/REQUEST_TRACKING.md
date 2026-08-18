# Seguimiento universal, acciones pendientes y cancelación

## Objetivo

Todo usuario activo y autenticado puede consultar el dashboard y las solicitudes de la organización para dar seguimiento, sin que la lectura dependa de haber creado la solicitud ni de pertenecer a un rol/grupo específico.

La lectura compartida no convierte las acciones mutables en universales. El dashboard separa explícitamente:

```text
información compartida
vs
acciones concretas que requieren al usuario actual
```

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

Los permisos pueden provenir de asignación directa, Rol directo, Grupo → Rol o Cargo → Rol.

## Dashboard

`GET /api/expenses/dashboard` muestra métricas compartidas de la organización.

Los KPIs superiores son **solo informativos**. En particular:

```text
Acciones que requieren mi atención
Solicitudes en proceso
Cerradas en 24 horas
```

se renderizan como contenido (`article`) y no como botones. No navegan, no abren modales y no ejecutan ninguna acción mediante clic o teclado.

La interacción se concentra en controles explícitos:

```text
fila de Acciones pendientes → modal contextual
Ver todas                    → Solicitudes
```

`pending_my_action` es personal y cuenta acciones concretas vigentes, no simplemente solicitudes abiertas ni permisos abstractos.

El resolver canónico vive en:

```text
backend/app/services/pending_action_service.py
```

Acciones actuales:

### `APPROVAL_DECISION`

El usuario tiene `requests:approve` y existe un `Approval.PENDING` asignado a su correo para una solicitud todavía en `PENDING_APPROVAL`.

### `QUOTATION_VOTE`

El usuario tiene `requests:approve`, fue invitado a la ronda vigente de `QUOTATION_VOTING` y todavía no registró su voto.

### `CORRECT_REQUEST`

La solicitud está en `NEEDS_REVISION`, pertenece al usuario actual y el usuario conserva `requests:create`.

### `CLOSE_REQUEST`

La solicitud está `APPROVED` y el usuario tiene `requests:close`.

El dashboard devuelve el código concreto en cada fila:

```json
{
  "request_id": "...",
  "title": "Compra de prueba",
  "actions": ["APPROVAL_DECISION"]
}
```

## Modal contextual de acciones pendientes

**Inicio → Acciones pendientes** tiene dos comportamientos distintos:

```text
Ver todas
→ navegar a Solicitudes

clic en una solicitud pendiente
→ abrir modal de Mis acciones
```

La fila no debe reutilizar el handler de **Ver todas**.

Al seleccionar una fila, `frontend/src/home-dashboard.jsx` consulta:

```text
GET /api/expenses/{request_id}/my-actions
```

El backend vuelve a evaluar permiso + asignación + estado de workflow. Esto evita mostrar una acción obsoleta si el usuario ya respondió desde correo, otra pestaña o una sesión distinta.

El modal presenta el resumen de la solicitud y solo las acciones vigentes para ese usuario.

### Aprobación

```text
APPROVAL_DECISION
→ comentario opcional
→ Rechazar
→ Solicitar corrección
→ Aprobar
```

La decisión autenticada usa:

```text
POST /api/expenses/{request_id}/approval-decision
```

El frontend no necesita ni recibe el token bearer usado por los enlaces de correo.

El endpoint vuelve a comprobar:

- `requests:approve`;
- aprobación `PENDING` asignada al usuario;
- que el usuario no sea el solicitante de la misma solicitud;
- reglas del motor `approval_engine.apply_decision()`.

### Votación de cotizaciones

```text
QUOTATION_VOTE
→ ver proveedor/monto/notas
→ abrir URL/soportes
→ Votar por esta opción
```

Reutiliza:

```text
POST /api/expenses/{request_id}/quotation-vote
```

### Cierre

```text
CLOSE_REQUEST
→ seleccionar factura
→ notas opcionales
→ Subir factura y cerrar
```

Reutiliza:

```text
POST /api/expenses/{request_id}/close
```

### Corrección

```text
CORRECT_REQUEST
→ Abrir para corregir / reenviar
```

La edición continúa en el editor canónico de Solicitudes para preservar todas las reglas SIMPLE/MULTI_QUOTE de Feature 003.

### Después de ejecutar una acción

El frontend recarga en paralelo:

```text
GET /api/expenses/dashboard
GET /api/expenses/{request_id}/my-actions
```

Si la acción quedó atendida, el modal muestra:

> Ya no tienes acciones pendientes para esta solicitud.

Si el cambio de estado genera otra tarea válida para el mismo usuario, esa nueva acción puede aparecer en el mismo modal después del refresh.

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

Por la misma razón, el Administrador del sistema productivo no debe recibir `APPROVAL_DECISION`, `QUOTATION_VOTE` ni `CLOSE_REQUEST` en su bandeja de acciones personales.

## Frontend

Componentes relevantes:

```text
frontend/src/home-dashboard.jsx
frontend/src/home-dashboard.css
```

Los tres KPIs superiores usan elementos no interactivos. Las filas de `pending_items` sí son controles porque abren una acción concreta del usuario.

Mientras `main.jsx` conserve una implementación histórica de `HomeDashboard`, `vite.config.js` elimina la función completa durante build e importa el componente modular. No se parchea el `onClick` de cada fila por coincidencias de texto.

Mientras `ExpenseTable` permanezca dentro de `main.jsx`, el build todavía reemplaza la condición legacy de cancelación por `x.can_cancel`. Esa compatibilidad es independiente del modal de Inicio.

## Accesibilidad

Los KPIs informativos no deben entrar al orden de tabulación como botones.

El modal usa:

```text
role="dialog"
aria-modal="true"
```

Puede cerrarse con Escape, tiene botón explícito de cierre y adapta su layout a pantallas pequeñas.

## Pruebas

Cobertura principal:

- `backend/tests/test_universal_tracking.py`
- `backend/tests/test_request_cancellation.py`
- `backend/tests/test_pending_actions.py`
- `backend/tests/test_frontend_dashboard_contract.py`

Deben demostrar:

- lectura universal sin mutación universal;
- regla exacta solicitante/admin para cancelación;
- acciones pendientes determinadas por permiso + asignación + estado;
- decisión de aprobación contextual sin token de correo;
- votación/corrección/cierre personalizados;
- KPIs superiores informativos, sin botones ni handlers `onClick`;
- fila pendiente abre modal contextual y no el handler genérico de Solicitudes;
- **Ver todas** conserva navegación explícita;
- revalidación después de cada mutación.

Mientras la cuota de GitHub Actions esté agotada, estas pruebas, `npm run build` y los builds Docker deben ejecutarse localmente antes de merge/deploy.
