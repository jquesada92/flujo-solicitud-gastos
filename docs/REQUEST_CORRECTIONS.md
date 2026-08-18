# Correcciones y reenvío de solicitudes

## Principio

**Corregir / reenviar modifica una solicitud sin cambiar su tipo de flujo.**

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

Cambiar deliberadamente entre tipos no forma parte de una corrección y requeriría una acción funcional diferente.

## La pestaña previa no manda

Las pestañas **Solicitud sencilla** y **Múltiples cotizaciones** pertenecen únicamente al modo de creación. Al pulsar **Corregir / reenviar**, el editor descarta ese estado y deriva su tipo desde la solicitud seleccionada.

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

## Formulario canónico

La implementación mantenible vive en:

```text
frontend/src/expense-form.jsx
```

El componente calcula un único tipo efectivo:

```text
effectiveRequestType = draft ? resolveRequestType(draft) : requestType
```

Durante una corrección ese valor, y no la pestaña ni un estado React previo, gobierna:

- layout visible;
- validaciones;
- payload enviado al backend;
- campos SIMPLE;
- opciones MULTI_QUOTE;
- carga posterior de soportes.

`resolveRequestType(draft)` considera MULTI_QUOTE si se cumple cualquiera de estas condiciones:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR existen 2 o más quotation_options
```

El propio componente rehidrata cuando cambia `draft.request_id` o `draft.flow_id`; no necesita una `key` inyectada por un reemplazo textual de build.

## Cómo debe verse una corrección MULTI_QUOTE

Debe aparecer explícitamente:

```text
Tipo de solicitud: Múltiples cotizaciones
```

seguido del bloque:

```text
Opciones para votación
  Opción 1
  Opción 2
  ...
```

Cada opción muestra proveedor, monto, URL, archivo y observaciones.

No debe aparecer el formulario sencillo como estructura principal con:

- un único `Monto (USD)` de solicitud;
- un único `Proveedor`;
- un único `URL del producto o servicio`;
- un único input de `Cotización`.

Los montos/proveedores de una MULTI_QUOTE pertenecen a cada opción de cotización.

## SIMPLE

Al corregir una solicitud sencilla se pueden actualizar sus datos de negocio. Los soportes existentes se conservan. Si ya existe evidencia suficiente, el flujo de aprobación puede reiniciarse sin exigir volver a cargar el mismo archivo.

## MULTI_QUOTE

Al corregir una solicitud de múltiples cotizaciones:

- el formulario abre en modo **Múltiples cotizaciones** aunque antes estuviera activa la pestaña SIMPLE;
- se restauran las opciones existentes;
- se pueden editar proveedor, monto, URL y observaciones;
- los soportes ya cargados siguen vinculados a sus opciones;
- la UI indica `Soporte existente conservado` cuando corresponde;
- por ahora se conserva la misma cantidad de opciones;
- el `flow_id` cambia;
- los votos vigentes de la ronda anterior se invalidan;
- las invitaciones anteriores se reemplazan;
- se calcula nuevamente la población desde `requests:approve`;
- la solicitud vuelve a `QUOTATION_VOTING`.

Los eventos históricos previos se conservan para trazabilidad.

## Compatibilidad con datos históricos

Algunos registros antiguos pueden contener `request_type=SIMPLE` por el default original aunque realmente sean flujos múltiples. La migración:

```text
20260817_0003_backfill_multi_quote_request_type.py
```

repara esas filas persistidas. El endpoint canónico de corrección aplica además la misma inferencia defensiva mientras dure la transición.

## Defensa backend

La API canónica compara el payload contra el **tipo canónico** de la solicitud, no contra el estado visual del formulario.

Si el usuario intenta convertir realmente una MULTI_QUOTE en SIMPLE o viceversa durante `resubmit`, devuelve `409 Conflict`.

## Integración temporal con main.jsx

`main.jsx` todavía contiene una definición legacy de `ExpenseForm` por deuda histórica. Para evitar que esa implementación vuelva a gobernar la aplicación, `vite.config.js` hace una transformación estructural mínima:

1. importa `ExpenseForm` desde `./expense-form.jsx`;
2. elimina del bundle la función legacy completa comprendida entre `function ExpenseForm` y `function ClosurePanel`;
3. no parchea el punto de montaje `<ExpenseForm>` ni depende de espacios, indentación o saltos de línea de ese JSX.

El build falla si no puede aislar la función antigua. CI inspecciona además el `dist/` generado y exige que el bundle contenga las marcas del formulario modular.

Esta decisión corrige un fallo reproducido en Docker local donde un reemplazo exacto del mount (`ExpenseForm mount`) dejó de coincidir con `main.jsx` y abortó `vite build`.

## Por qué no se permite cambiar la cantidad de opciones todavía

Quitar una cotización que ya tiene documentos o votos implica decisiones de versionado y evidencia. Esta feature evita eliminar evidencia de forma implícita. La edición estructural de una ronda debe especificarse separadamente antes de implementarse.

## Prueba manual obligatoria

```text
1. Entrar a Solicitudes.
2. Dejar seleccionada Solicitud sencilla.
3. Buscar una solicitud en Votación de cotizaciones.
4. Pulsar Corregir / reenviar.
5. Verificar Tipo de solicitud: Múltiples cotizaciones.
6. Verificar que aparezca Opciones para votación con las opciones existentes.
7. Verificar que no aparezca el formulario sencillo como estructura principal.
```

## Validación del bundle local Docker

Después de reconstruir el frontend:

```bash
docker compose exec frontend sh -c "grep -R -l 'El tipo no cambia durante una corrección' /usr/share/nginx/html/assets || true"
```

Debe devolver el archivo `index-*.js` servido por Nginx. Una salida vacía indica que el contenedor no contiene el formulario modular esperado.
