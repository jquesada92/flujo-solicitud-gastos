# Especificación funcional — Correcciones de solicitudes

**Feature:** 003-request-correction-invariants  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17  
**Constitución:** 2.3.2

## Objetivo

Garantizar que **Corregir / reenviar** modifique los datos de una solicitud sin cambiar accidentalmente la naturaleza de su flujo y sin depender del estado previo de las pestañas de creación.

## Problema detectado

El formulario legacy mantiene `requestType` como estado React compartido entre la creación y la corrección. La pestaña por defecto al entrar a Solicitudes es `SIMPLE`. Si el usuario pulsaba **Corregir / reenviar** sobre una solicitud `MULTI_QUOTE` mientras esa pestaña seguía activa, el editor podía heredar `SIMPLE`. Si antes de corregir el usuario seleccionaba manualmente **Múltiples cotizaciones**, la misma corrección aparecía correctamente como múltiple.

Ese comportamiento demuestra que la pestaña de creación estaba actuando como fuente accidental de verdad. Además, algunos registros históricos pueden conservar el default persistido `request_type=SIMPLE` aunque tengan dos o más `quotation_options` o estén en `QUOTATION_VOTING`.

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
4. El componente/editor de corrección MUST inicializarse desde la solicitud seleccionada, no desde el `requestType` que estuviera activo antes.
5. Cambiar de una solicitud en corrección a otra MUST volver a derivar el tipo desde la nueva solicitud.
6. `PUT /api/expenses/{request_id}/resubmit` MUST rechazar con `409` un intento real de cambiar el tipo canónico de la solicitud.
7. Si una fila legacy tiene `request_type=SIMPLE` pero posee evidencia durable de flujo múltiple —dos o más `quotation_options` o estado `QUOTATION_VOTING`— MUST tratarse y repararse como `MULTI_QUOTE`.
8. Una corrección MULTI_QUOTE MUST restaurar en la UI las cotizaciones existentes.
9. Una corrección MULTI_QUOTE MUST conservar los soportes existentes de cada opción.
10. Una corrección MULTI_QUOTE MUST generar un `flow_id` nuevo.
11. Los votos actuales (`quotation_votes`) de la ronda anterior MUST invalidarse/eliminarse como estado vigente.
12. Las invitaciones actuales MUST reemplazarse por nuevas invitaciones para la nueva ronda.
13. El historial append-only de eventos de rondas anteriores no debe reescribirse.
14. La población nueva se resuelve mediante el permiso efectivo `requests:approve`.
15. La corrección conserva por ahora la cantidad de opciones existente. Puede editar proveedor, monto, URL y observaciones de cada opción.
16. Cambiar deliberadamente `SIMPLE ↔ MULTI_QUOTE` será, si se requiere, una operación funcional explícita distinta; no forma parte de `Corregir / reenviar`.

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

## Compatibilidad frontend

Mientras `frontend/src/main.jsx` siga siendo monolítico, Vite aplica una transformación de compatibilidad estricta que:

- deriva el tipo inicial desde el `draft` y evidencia durable;
- fuerza un remount de `ExpenseForm` cuando cambia la solicitud en corrección;
- restaura `draft.request_type`/tipo inferido;
- restaura `draft.quotation_options`;
- reconoce soportes existentes;
- impide agregar/eliminar slots de cotización durante una corrección;
- falla el build si los fragmentos legacy esperados dejan de existir.

La `key` del formulario de corrección incluye la identidad/flujo de la solicitud, evitando que el estado de una pestaña de creación anterior sobreviva al cambio de modo.

Esta transformación es temporal y debe retirarse cuando `ExpenseForm` sea extraído a un módulo mantenible.

## Migración de datos

`20260817_0003_backfill_multi_quote_request_type.py` corrige filas históricas cuyo `request_type` no refleja la evidencia de múltiples cotizaciones. Es una migración de reparación de datos, no una transformación destructiva de evidencia.

## Fuera de alcance

- cambiar la cantidad de cotizaciones durante una corrección;
- reglas nuevas de quorum/empate;
- convertir una solicitud entre SIMPLE y MULTI_QUOTE;
- rediseño completo del formulario legacy;
- revisión inmutable completa mediante una entidad `RequestRevision` separada.
