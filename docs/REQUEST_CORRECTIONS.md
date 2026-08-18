# Correcciones y reenvío de solicitudes

## Principio

**Corregir / reenviar modifica una solicitud sin cambiar su tipo de flujo.**

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Cambiar deliberadamente entre tipos no forma parte de una corrección y requeriría una acción funcional diferente.

## La pestaña previa no manda

Las pestañas **Solicitud sencilla** y **Múltiples cotizaciones** pertenecen al modo de creación. Al pulsar **Corregir / reenviar**, el editor debe descartar ese estado y derivar su tipo desde la solicitud seleccionada.

Por tanto, estos dos recorridos deben producir exactamente el mismo resultado:

```text
Pestaña SIMPLE activa
→ Corregir una MULTI_QUOTE
→ editor MULTI_QUOTE
```

```text
Pestaña MULTI_QUOTE activa
→ Corregir una MULTI_QUOTE
→ editor MULTI_QUOTE
```

La corrección no puede depender de qué pestaña estaba seleccionada antes del clic.

## Tipo efectivo durante la corrección

La reproducción manual demostró que no basta con ejecutar `setRequestType()` al hidratar el draft. El formulario legacy contiene múltiples decisiones de render, validación y payload que consultaban directamente ese estado React.

Por eso se define un tipo efectivo:

```text
si existe draft:
    effectiveRequestType = tipo canónico/inferido del draft
si es nueva solicitud:
    effectiveRequestType = pestaña seleccionada
```

Durante una corrección, **`effectiveRequestType` es la única autoridad frontend** para:

- decidir si se muestran campos SIMPLE o el editor MULTI_QUOTE;
- validar soportes;
- construir `request_type` del payload;
- construir `quotation_options`;
- cargar archivos asociados al tipo correcto.

El estado React `requestType` puede seguir existiendo temporalmente por compatibilidad con el formulario monolítico, pero no puede gobernar una corrección.

La UI muestra además el tipo real como dato de solo lectura:

```text
Tipo de solicitud: Múltiples cotizaciones
El tipo no cambia durante una corrección.
```

No se muestra un selector de tipo durante la corrección porque convertir SIMPLE ↔ MULTI_QUOTE no forma parte de esta acción.

## SIMPLE

Al corregir una solicitud sencilla se pueden actualizar sus datos de negocio. Los soportes existentes se conservan. Si ya existe evidencia suficiente, el flujo de aprobación puede reiniciarse sin exigir que el usuario vuelva a cargar el mismo archivo.

## MULTI_QUOTE

Al corregir una solicitud de múltiples cotizaciones:

- el formulario vuelve a abrir en modo **Múltiples cotizaciones** aunque antes estuviera activa la pestaña SIMPLE;
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

## Compatibilidad con datos históricos

Algunos registros antiguos pueden contener `request_type=SIMPLE` por el default original aunque realmente sean flujos múltiples.

Se considera evidencia durable de `MULTI_QUOTE` cualquiera de las siguientes condiciones:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR existen 2 o más quotation_options
```

La migración Alembic:

```text
20260817_0003_backfill_multi_quote_request_type.py
```

repara esas filas persistidas. El endpoint canónico de corrección aplica además la misma inferencia defensiva mientras dure la transición.

## Por qué no se permite cambiar la cantidad de opciones todavía

Quitar una cotización que ya tiene documentos o votos implica decisiones de versionado y evidencia. Esta feature evita eliminar evidencia de forma implícita. La edición estructural de una ronda debe especificarse separadamente antes de implementarse.

## Defensa backend

La API canónica compara el payload contra el **tipo canónico** de la solicitud, no contra el estado visual del formulario.

Si el usuario intenta convertir realmente una MULTI_QUOTE en SIMPLE o viceversa durante `resubmit`, devuelve `409 Conflict`.

Esto evita que un valor por defecto de frontend pueda convertir silenciosamente una MULTI_QUOTE en SIMPLE o viceversa.

## Compatibilidad del frontend actual

El formulario operativo sigue dentro de `frontend/src/main.jsx`, que está pendiente de modularización. Mientras tanto, `frontend/vite.config.js` aplica una transformación estricta durante `vite dev` y `vite build` que:

- deriva el tipo inicial desde el draft y su evidencia durable;
- define `effectiveRequestType` como autoridad cuando existe un draft;
- fuerza un remount de `ExpenseForm` cuando se entra a corregir o cambia la solicitud;
- restaura las opciones existentes;
- evita heredar la pestaña de creación anterior;
- usa el tipo efectivo en render, validación, payload y uploads;
- muestra el tipo de corrección como solo lectura.

El transform falla el build si los fragmentos legacy esperados cambian, evitando que el parche deje de aplicarse silenciosamente.

Además, `backend/tests/test_frontend_revision_contract.py` verifica estáticamente que el transform conserve los puntos críticos del contrato.

Cuando `ExpenseForm` sea extraído a un componente propio, esta transformación deberá eliminarse y la hidratación de drafts tendrá tests frontend dedicados.
