# Correcciones, reenvío y handoff de revisión

## Principios

Dos acciones distintas:

```text
Aprobador detecta un problema
→ Enviar a revisión + comentario

Solicitante recibe NEEDS_REVISION
→ Corregir / reenviar
```

**Enviar a revisión** no permite al aprobador editar la solicitud. **Corregir / reenviar** está reservado al solicitante original o al Administrador del sistema protegido mediante `system_accounts`.

## Quién puede Corregir / reenviar

Solo:

```text
solicitante original
OR
Administrador del sistema
```

No autorizan la corrección de una solicitud ajena:

```text
requests:create
requests:approve
config:manage
Grupo
Rol
Cargo
UserRole/can_* legacy
```

El listado devuelve `can_correct` calculado por backend. La UI lo utiliza para mostrar **Corregir / reenviar**, pero `PUT /api/expenses/{request_id}/resubmit` vuelve a autorizar siempre.

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

Un aprobador con `Approval.PENDING` puede seleccionar **Enviar a revisión** cuando detecta un problema.

Requiere comentario útil de al menos 3 caracteres indicando qué debe revisar/corregir el solicitante.

`REVISION_REQUESTED` es una interrupción inmediata, no una decisión sometida a mayoría:

```text
aprobación actual → REVISION_REQUESTED
solicitud          → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
solicitante        → CORRECT_REQUEST
```

El solicitante recibe una notificación con el comentario. Los demás aprobadores dejan de tener una acción vigente en esa ronda.

El Administrador del sistema conserva facultad administrativa para corregir, pero la tarea personal `CORRECT_REQUEST` pertenece normalmente al solicitante original.

## Invariant del tipo

**Corregir / reenviar modifica una solicitud sin cambiar su tipo:**

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Cambiar deliberadamente entre tipos requiere otra operación funcional.

## La pestaña previa no manda

Las pestañas **Solicitud sencilla** y **Múltiples cotizaciones** solo pertenecen a creación. Al entrar en corrección, el editor deriva su tipo desde la solicitud.

```text
Pestaña SIMPLE activa
→ Corregir una MULTI_QUOTE
→ editor MULTI_QUOTE
```

## Formulario canónico

```text
frontend/src/expense-form.jsx
```

```text
effectiveRequestType = draft ? resolveRequestType(draft) : requestType
```

Durante corrección gobierna layout, validación, payload y uploads.

Se considera MULTI_QUOTE si:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

## MULTI_QUOTE corregida

- restaura opciones existentes;
- conserva soportes vinculados;
- permite editar proveedor, monto, URL y observaciones;
- conserva por ahora la cantidad de opciones;
- genera `flow_id` nuevo;
- elimina votos vigentes;
- reemplaza invitaciones;
- limpia ganador/proveedor/monto seleccionado;
- conserva historial;
- vuelve a `QUOTATION_VOTING`;
- resuelve población con `requests:approve`;
- **excluye siempre al solicitante original**, incluso si el Administrador del sistema ejecutó la corrección.

## Compatibilidad histórica

Alembic:

```text
20260817_0003_backfill_multi_quote_request_type.py
```

repara filas cuyo flag SIMPLE contradice evidencia durable de múltiples cotizaciones.

Feature 007 no requiere migración nueva.

## Backend

`backend/app/api/revision_actions.py`:

- autentica con `current_user`;
- calcula/valida `can_correct_expense()`;
- devuelve 403 a terceros;
- mantiene 409 para cambios reales del tipo;
- reinicia el flujo conservando evidencia/historial.

Un mensaje 403 orienta al aprobador a usar **Enviar a revisión** con comentarios.

## Frontend temporal

`ExpenseForm` es modular, pero `ExpenseTable` aún vive en `main.jsx`. Durante la transición, `vite.config.js`:

- importa/elimina la definición legacy de `ExpenseForm` estructuralmente;
- usa `x.can_correct` en la tabla legacy;
- permite montar el formulario si existe `revision`, de forma que el Administrador del sistema productivo pueda corregir aunque no tenga `requests:create`.

El wording de **Enviar a revisión** vive directamente en `home-dashboard.jsx`; no depende de un parche de Vite.

## Prueba manual

```text
1. Iniciar sesión como aprobador de una solicitud ajena.
2. Confirmar que NO aparece Corregir / reenviar.
3. Abrir la aprobación y seleccionar Enviar a revisión.
4. Confirmar que el comentario es obligatorio.
5. Enviar revisión y verificar NEEDS_REVISION inmediato.
6. Confirmar que otros aprobadores dejan de tener acción vigente.
7. Iniciar sesión como solicitante y confirmar CORRECT_REQUEST + Corregir / reenviar.
8. Confirmar que Administrador del sistema también puede corregir desde Solicitudes.
9. Para MULTI_QUOTE, reenviar y confirmar que el solicitante original no entra en su nueva votación.
```

## Validación Docker

Después del build:

```bash
docker compose exec frontend sh -c "grep -R -l 'Enviar a revisión' /usr/share/nginx/html/assets || true"
docker compose exec frontend sh -c "grep -R -l 'El tipo no cambia durante una corrección' /usr/share/nginx/html/assets || true"
```

Ambos comportamientos deben estar presentes en el bundle servido por Nginx.
