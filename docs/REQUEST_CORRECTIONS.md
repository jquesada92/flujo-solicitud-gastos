# Correcciones y reenvío de solicitudes

## Principio

**Corregir / reenviar modifica una solicitud sin cambiar su tipo de flujo.**

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Cambiar deliberadamente entre tipos no forma parte de una corrección y requeriría una acción funcional diferente.

## SIMPLE

Al corregir una solicitud sencilla se pueden actualizar sus datos de negocio. Los soportes existentes se conservan. Si ya existe evidencia suficiente, el flujo de aprobación puede reiniciarse sin exigir que el usuario vuelva a cargar el mismo archivo.

## MULTI_QUOTE

Al corregir una solicitud de múltiples cotizaciones:

- el formulario vuelve a abrir en modo **Múltiples cotizaciones**;
- se restauran las opciones existentes;
- se pueden editar proveedor, monto, URL y observaciones;
- los soportes ya cargados siguen vinculados a sus opciones;
- por ahora se conserva la misma cantidad de opciones;
- el `flow_id` cambia;
- los votos vigentes de la ronda anterior se invalidan;
- las invitaciones anteriores se reemplazan;
- se calcula nuevamente la población desde `requests:approve`;
- la solicitud vuelve a `QUOTATION_VOTING`.

Los eventos históricos previos se conservan para trazabilidad.

## Por qué no se permite cambiar la cantidad de opciones todavía

Quitar una cotización que ya tiene documentos o votos implica decisiones de versionado y evidencia. Esta feature evita eliminar evidencia de forma implícita. La edición estructural de una ronda debe especificarse separadamente antes de implementarse.

## Defensa backend

La API canónica aplica:

```text
payload.request_type == stored_request.request_type
```

Si no coincide, devuelve `409 Conflict`.

Esto evita que un valor por defecto de frontend pueda convertir silenciosamente una MULTI_QUOTE en SIMPLE o viceversa.

## Compatibilidad del frontend actual

El formulario operativo sigue dentro de `frontend/src/main.jsx`, que está pendiente de modularización. Mientras tanto, `frontend/vite.config.js` aplica una transformación estricta durante `vite dev` y `vite build` para restaurar correctamente el estado de una corrección MULTI_QUOTE.

El transform falla el build si los fragmentos legacy esperados cambian, evitando que el parche deje de aplicarse silenciosamente.

Cuando `ExpenseForm` sea extraído a un componente propio, esta transformación deberá eliminarse y la hidratación de drafts tendrá tests frontend dedicados.
