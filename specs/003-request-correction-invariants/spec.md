# Especificación funcional — Correcciones de solicitudes

**Feature:** 003-request-correction-invariants  
**Estado:** Implementada y extendida por Feature 007  
**Fecha:** 2026-08-18  
**Constitución:** 2.6.0

## Objetivo

Garantizar que **Corregir / reenviar** modifique los datos de una solicitud sin cambiar accidentalmente la naturaleza de su flujo, sin depender del estado previo de las pestañas de creación y sin permitir que un tercero edite una solicitud ajena.

Feature 003 conserva los invariants SIMPLE/MULTI_QUOTE. Feature 007 define la autoridad de corrección y el handoff **Enviar a revisión → solicitante corrige**.

## Historias de usuario

### US-001 — Corregir una solicitud propia

Como solicitante original, cuando debo corregir una solicitud quiero volver a editarla y reenviarla conservando el tipo y la evidencia existente.

### US-002 — Administración excepcional

Como Administrador del sistema protegido, necesito poder corregir/reenviar una solicitud abierta como acción administrativa del ciclo de vida, sin adquirir permisos financieros en producción.

### US-003 — Preservar el tipo

Como responsable del proceso quiero que una corrección conserve el tipo real del flujo para que un valor por defecto del frontend o un dato legacy inconsistente no cambie las reglas de negocio.

### US-004 — Aislar el editor del estado previo

Como usuario autorizado a corregir quiero que el editor sea el mismo independientemente de si antes estaba seleccionada la pestaña **Solicitud sencilla** o **Múltiples cotizaciones**.

### US-005 — Reiniciar la ronda MULTI_QUOTE

Como aprobador quiero que una MULTI_QUOTE corregida inicie una ronda nueva, con `flow_id` nuevo, sin reutilizar votos ni invitaciones de la ronda anterior.

### US-006 — Conservar evidencia

Como auditor quiero que los soportes/cotizaciones ya cargados permanezcan asociados a sus opciones cuando una corrección solo modifica proveedor, monto, URL u observaciones.

## Autoridad para corregir

**Corregir / reenviar es una capacidad por recurso.** Solo pueden ejecutarla:

1. el solicitante original; o
2. el Administrador del sistema identificado mediante `system_accounts`.

No autorizan corrección de solicitudes ajenas:

- `requests:create`;
- `requests:approve`;
- `config:manage`;
- Grupo;
- Rol;
- Cargo/Posición;
- `UserRole` o `can_*` legacy.

Un aprobador que detecte un problema debe usar **Enviar a revisión** con comentario obligatorio. Esa transición y el handoff al solicitante pertenecen a Feature 007.

El backend expone `can_correct` por solicitud para UX y vuelve a autorizar siempre en `PUT /api/expenses/{request_id}/resubmit`.

## Reglas funcionales

1. `SIMPLE` corregida MUST permanecer `SIMPLE`.
2. `MULTI_QUOTE` corregida MUST permanecer `MULTI_QUOTE`.
3. El estado de las pestañas de creación MUST descartarse al entrar en modo corrección.
4. El editor MUST decidir su layout completo desde el tipo canónico de la solicitud seleccionada.
5. Si el tipo canónico es `MULTI_QUOTE`, el formulario SIMPLE MUST NOT renderizarse como estructura principal.
6. Cambiar a otra solicitud en corrección MUST volver a derivar el tipo desde esa solicitud.
7. `PUT /api/expenses/{request_id}/resubmit` MUST devolver 403 a un actor que no sea solicitante ni Administrador del sistema.
8. `PUT /api/expenses/{request_id}/resubmit` MUST rechazar con 409 un cambio real del tipo canónico.
9. Si una fila legacy tiene `request_type=SIMPLE` pero evidencia durable de flujo múltiple, MUST tratarse/repararse como `MULTI_QUOTE`.
10. Una corrección MULTI_QUOTE MUST restaurar cotizaciones y soportes existentes.
11. Una corrección MULTI_QUOTE MUST generar `flow_id` nuevo.
12. Votos e invitaciones vigentes de la ronda anterior MUST dejar de ser estado activo.
13. Las invitaciones nuevas MUST resolverse desde `requests:approve` y MUST excluir al **solicitante original**, incluso si el Administrador del sistema ejecutó la corrección.
14. Los eventos históricos append-only MUST conservarse.
15. Por ahora la corrección MULTI_QUOTE conserva la cantidad de opciones y permite editar su contenido.
16. Cambiar deliberadamente `SIMPLE ↔ MULTI_QUOTE` requiere una operación funcional distinta.

## Estados corregibles

Por los actores autorizados:

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

## Resolución del tipo canónico

Para compatibilidad histórica:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Alembic `20260817_0003_backfill_multi_quote_request_type.py` repara las filas persistidas inconsistentes y el endpoint conserva la inferencia defensiva.

## Evidencia/archivos

Los navegadores no permiten prellenar `<input type="file">`. El frontend representa un soporte ya existente mediante metadata (`existing_attachment`) y no obliga a volver a cargarlo para validar la corrección.

## Frontend modular

El formulario canónico vive en:

```text
frontend/src/expense-form.jsx
```

`resolveRequestType(draft)` y `effectiveRequestType` gobiernan layout, validación, payload y uploads.

Mientras `ExpenseTable` permanezca en `main.jsx`, la visibilidad de **Corregir / reenviar** se adapta temporalmente en build a `x.can_correct`. La autoridad real es el backend.

## Migraciones

Feature 003 usa `0003` para reparar `request_type`. Feature 007 no agrega columnas/tablas nuevas.

La cadena global de la rama es actualmente:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

`0004` corresponde a Feature 006 y es independiente de la autorización de corrección.

## Fuera de alcance

- cambiar la cantidad de cotizaciones durante una corrección;
- convertir una solicitud entre SIMPLE y MULTI_QUOTE;
- una entidad `RequestRevision` inmutable separada;
- cambiar la fórmula de mayoría de aprobación salvo la interrupción específica `REVISION_REQUESTED` definida en Feature 007.
