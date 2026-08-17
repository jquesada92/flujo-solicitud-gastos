# Especificación funcional — Correcciones de solicitudes

**Feature:** 003-request-correction-invariants  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17

## Objetivo

Garantizar que **Corregir / reenviar** modifique los datos de una solicitud sin cambiar accidentalmente la naturaleza de su flujo.

## Problema detectado

El formulario legacy inicializaba siempre `requestType = SIMPLE`. Al abrir para corrección una solicitud `MULTI_QUOTE`, restauraba título, descripción y clasificación, pero no restauraba `request_type` ni `quotation_options`. Como resultado, la UI presentaba una solicitud sencilla y podía enviar un payload incompatible con el flujo original.

El endpoint legacy de `resubmit` tampoco reconstruía correctamente una ronda de múltiples cotizaciones.

## Historias de usuario

### US-001 — Corregir una solicitud MULTI_QUOTE

Como usuario con permiso `requests:create`, cuando corrijo una solicitud de múltiples cotizaciones quiero volver a ver las opciones existentes y editarlas sin que la solicitud se convierta en sencilla.

### US-002 — Preservar el tipo de solicitud

Como responsable del proceso quiero que una corrección conserve el `request_type` original para que un valor por defecto del frontend no pueda cambiar las reglas de negocio.

### US-003 — Reiniciar la votación corregida

Como aprobador quiero que una solicitud MULTI_QUOTE corregida inicie una ronda nueva, con un `flow_id` nuevo, sin reutilizar votos ni invitaciones de la ronda anterior.

### US-004 — Conservar evidencia existente

Como auditor quiero que los soportes/cotizaciones ya cargados permanezcan asociados a sus opciones cuando una corrección solo modifica proveedor, monto, URL u observaciones.

## Reglas funcionales

1. `SIMPLE` corregida MUST permanecer `SIMPLE`.
2. `MULTI_QUOTE` corregida MUST permanecer `MULTI_QUOTE`.
3. `PUT /api/expenses/{request_id}/resubmit` MUST rechazar con `409` un intento de cambiar el `request_type` original.
4. Una corrección MULTI_QUOTE MUST restaurar en la UI las cotizaciones existentes.
5. Una corrección MULTI_QUOTE MUST conservar los soportes existentes de cada opción.
6. Una corrección MULTI_QUOTE MUST generar un `flow_id` nuevo.
7. Los votos actuales (`quotation_votes`) de la ronda anterior MUST invalidarse/eliminarse como estado vigente.
8. Las invitaciones actuales MUST reemplazarse por nuevas invitaciones para la nueva ronda.
9. El historial append-only de eventos de rondas anteriores no debe reescribirse.
10. La población nueva se resuelve mediante el permiso efectivo `requests:approve`.
11. La corrección conserva por ahora la cantidad de opciones existente. Puede editar proveedor, monto, URL y observaciones de cada opción.
12. Cambiar deliberadamente `SIMPLE ↔ MULTI_QUOTE` será, si se requiere, una operación funcional explícita distinta; no forma parte de `Corregir / reenviar`.

## Evidencia/archivos

Los navegadores no permiten prellenar un `<input type="file">`. Por ello, el frontend representa un soporte ya existente mediante metadata (`existing_attachment`) y no obliga al usuario a volver a cargarlo para validar la corrección.

La evidencia existente se preserva. Cargar un archivo nuevo sigue siendo una acción explícita posterior al resubmit mediante el endpoint de documentos correspondiente.

## Compatibilidad frontend

Mientras `frontend/src/main.jsx` siga siendo monolítico, Vite aplica una transformación de compatibilidad estricta que:

- restaura `draft.request_type`;
- restaura `draft.quotation_options`;
- reconoce soportes existentes;
- impide agregar/eliminar slots de cotización durante una corrección;
- falla el build si los fragmentos legacy esperados dejan de existir.

Esta transformación es temporal y debe retirarse cuando `ExpenseForm` sea extraído a un módulo mantenible.

## Fuera de alcance

- cambiar la cantidad de cotizaciones durante una corrección;
- reglas nuevas de quorum/empate;
- convertir una solicitud entre SIMPLE y MULTI_QUOTE;
- rediseño completo del formulario legacy;
- revisión inmutable completa mediante una entidad `RequestRevision` separada.
