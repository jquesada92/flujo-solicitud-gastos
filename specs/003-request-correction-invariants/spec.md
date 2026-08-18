# Especificación funcional — Correcciones de solicitudes

**Feature:** 003-request-correction-invariants  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17  
**Constitución:** 2.3.3

## Objetivo

Garantizar que **Corregir / reenviar** modifique los datos de una solicitud sin cambiar accidentalmente la naturaleza de su flujo y sin depender del estado previo de las pestañas de creación.

## Problema detectado

El formulario legacy mantenía `requestType` como estado React compartido entre creación y corrección. La pestaña por defecto al entrar a Solicitudes es `SIMPLE`. En pruebas manuales se confirmó que una solicitud en `QUOTATION_VOTING` podía seguir renderizando el formulario sencillo al pulsar **Corregir / reenviar**.

La protección mediante reemplazos granulares en `vite.config.js` no era una frontera suficientemente mantenible: el source real de `ExpenseForm` seguía siendo el legacy y podían existir discrepancias entre lo esperado por la regla funcional y el formulario visible.

## Historias de usuario

### US-001 — Corregir una solicitud MULTI_QUOTE

Como usuario con permiso `requests:create`, cuando corrijo una solicitud de múltiples cotizaciones quiero volver a ver las opciones existentes y editarlas sin que la solicitud se convierta en sencilla.

### US-002 — Preservar el tipo de solicitud

Como responsable del proceso quiero que una corrección conserve el tipo real del flujo para que un valor por defecto del frontend o un dato legacy inconsistente no pueda cambiar las reglas de negocio.

### US-003 — Aislar el editor del estado previo

Como usuario quiero que el resultado de pulsar **Corregir / reenviar** sea exactamente el mismo independientemente de si antes estaba seleccionada la pestaña **Solicitud sencilla** o **Múltiples cotizaciones**.

### US-004 — Reiniciar la votación corregida

Como aprobador quiero que una solicitud MULTI_QUOTE corregida inicie una ronda nueva, con un `flow_id` nuevo, sin reutilizar votos ni invitaciones de la ronda anterior.

### US-005 — Conservar evidencia existente

Como auditor quiero que los soportes/cotizaciones ya cargados permanezcan asociados a sus opciones cuando una corrección solo modifica proveedor, monto, URL u observaciones.

## Reglas funcionales

1. `SIMPLE` corregida MUST permanecer `SIMPLE`.
2. `MULTI_QUOTE` corregida MUST permanecer `MULTI_QUOTE`.
3. El estado de las pestañas de creación MUST descartarse al entrar en modo corrección.
4. El editor de corrección MUST decidir su layout completo desde el tipo canónico de la solicitud seleccionada.
5. Si el tipo canónico es `MULTI_QUOTE`, el formulario sencillo MUST NOT renderizar monto/proveedor/soporte único como estructura principal; MUST renderizar las opciones de cotización.
6. Cambiar de una solicitud en corrección a otra MUST volver a derivar el tipo desde la nueva solicitud.
7. `PUT /api/expenses/{request_id}/resubmit` MUST rechazar con `409` un intento real de cambiar el tipo canónico de la solicitud.
8. Si una fila legacy tiene `request_type=SIMPLE` pero posee evidencia durable de flujo múltiple —dos o más `quotation_options` o estado `QUOTATION_VOTING`— MUST tratarse y repararse como `MULTI_QUOTE`.
9. Una corrección MULTI_QUOTE MUST restaurar en la UI las cotizaciones existentes.
10. Una corrección MULTI_QUOTE MUST conservar los soportes existentes de cada opción.
11. Una corrección MULTI_QUOTE MUST generar un `flow_id` nuevo.
12. Los votos actuales (`quotation_votes`) de la ronda anterior MUST invalidarse/eliminarse como estado vigente.
13. Las invitaciones actuales MUST reemplazarse por nuevas invitaciones para la nueva ronda.
14. El historial append-only de eventos de rondas anteriores no debe reescribirse.
15. La población nueva se resuelve mediante el permiso efectivo `requests:approve`.
16. La corrección conserva por ahora la cantidad de opciones existente. Puede editar proveedor, monto, URL y observaciones de cada opción.
17. Cambiar deliberadamente `SIMPLE ↔ MULTI_QUOTE` será, si se requiere, una operación funcional explícita distinta; no forma parte de `Corregir / reenviar`.

## Resolución del tipo canónico

Para compatibilidad con datos históricos, el sistema reconoce `MULTI_QUOTE` cuando se cumple cualquiera de estas condiciones durables:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Alembic repara las filas persistidas inconsistentes y el endpoint canónico mantiene la misma inferencia defensiva durante la transición.

## Evidencia/archivos

Los navegadores no permiten prellenar un `<input type="file">`. Por ello, el frontend representa un soporte ya existente mediante metadata (`existing_attachment`) y no obliga al usuario a volver a cargarlo para validar la corrección.

La evidencia existente se preserva. Cargar un archivo nuevo sigue siendo una acción explícita posterior al resubmit mediante el endpoint de documentos correspondiente.

## Frontend modular

El formulario canónico vive en:

```text
frontend/src/expense-form.jsx
```

`resolveRequestType(draft)` deriva el tipo canónico del draft y `effectiveRequestType` gobierna de forma única:

- layout/renderizado;
- validaciones;
- payload `request_type`;
- campos SIMPLE;
- opciones MULTI_QUOTE;
- carga posterior de soportes.

Durante una corrección no existe selector editable de tipo; se muestra el tipo como dato de solo lectura.

Mientras `main.jsx` siga conteniendo la definición legacy, `vite.config.js` realiza una única extracción de transición: importa el componente modular y elimina del bundle la función legacy completa. Ya no modifica granularmente condiciones internas del formulario.

## Migración de datos

`20260817_0003_backfill_multi_quote_request_type.py` corrige filas históricas cuyo `request_type` no refleja la evidencia de múltiples cotizaciones. Es una migración de reparación de datos, no una transformación destructiva de evidencia.

## Fuera de alcance

- cambiar la cantidad de cotizaciones durante una corrección;
- reglas nuevas de quorum/empate;
- convertir una solicitud entre SIMPLE y MULTI_QUOTE;
- revisión inmutable completa mediante una entidad `RequestRevision` separada.
