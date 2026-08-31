# Registro directo de gastos sin aprobación

## Cuándo aplica

Un gasto directo existe únicamente cuando una regla activa `NO_APPROVAL` cubre
el Área y monto mediante una banda `(min_amount,max_amount]`. Una regla del Área
concreta precede a `ALL`. La modalidad no lleva Roles o Grupos aprobadores porque
no crea una ronda.

`NO_APPROVAL` no es un tipo ni un estado de Solicitud. El registro se guarda en
`direct_expenses` y nunca crea `Expense`, aprobación, invitación, voto, acción
pendiente o `flow_id`.

## Uso de la pantalla

Un Usuario con `requests:create` abre **Registro directo → Gasto sin
aprobación**, selecciona el Área y completa:

- proveedor;
- ítem o descripción;
- monto positivo;
- factura PDF, JPEG, PNG o WEBP de hasta 10 MB.

La pantalla consulta `GET /api/direct-expenses/eligible-policies` y muestra las
bandas disponibles como ayuda. El navegador puede advertir si el monto no está
en `(min,max]`, pero no concede elegibilidad. Al enviar, FastAPI vuelve a validar
el Área activa, el monto, la precedencia Área/`ALL` y la política vigente.

Si el Usuario intenta primero crear una Solicitud dentro de una de esas bandas,
la interfaz conserva el borrador, muestra una orientación humana sin revelar la
ruta interna y resalta **Registro directo**. No cambia de pantalla por sí sola:
la navegación sigue su confirmación normal para no descartar datos sin permiso.

## Atomicidad y privacidad

El `POST /api/direct-expenses` valida firma, MIME y tamaño antes de confirmar.
La fila y la factura forman una unidad: ante fallo de archivo o base de datos no
queda un archivo físico ni una fila parcial.

El listado `GET /api/direct-expenses` devuelve solo registros propios para un
Usuario ordinario. La factura se descarga por
`GET /api/direct-expenses/{record_id}/invoice` y conocer el ID de otra persona no
autoriza su lectura. `system_accounts` puede listar todos y descargar cualquier
factura para su responsabilidad técnica. Los archivos no se publican como una
ruta estática.

## Layout para teléfonos y tabletas

La pantalla conserva introducción, Área, monto, proveedor, factura, ítem, bandas
y acción principal sin ocultar datos:

- de 320 a 720 px, introducción, campos y bandas se apilan en una columna;
- hasta 440 px, la descripción y el rango dentro de cada banda también se apilan;
- en 768, 820 y 1024 px puede usar dos columnas cuando ambas siguen legibles;
- inputs, selects y botones miden al menos 44 px y muestran foco visible;
- textos, nombres de archivo y rangos ajustan línea sin crear overflow horizontal.

La aceptación específica se ejecuta en Chrome a 320, 360, 390, 412, 440, 600,
640, 768, 820 y 1024 px, sin controles recortados ni información perdida. Después
del alta, la pantalla confirma el ID visible del registro. El listado privado
existe en el API, pero la pantalla actual no renderiza un panel de historial.

## Diferencia frente a una Solicitud

| Gasto directo | Solicitud `SIMPLE`/`MULTI_QUOTE` |
| --- | --- |
| Requiere banda `NO_APPROVAL` aplicable | Usa regla con ronda o fallback IAM |
| Registra factura en el alta | La factura llega al cierre |
| No crea participantes ni decisiones | Congela aprobadores o votantes |
| No tiene estado, corrección, delegación o cierre | Sigue el workflow de Solicitudes |
| Se consulta por autor; `system_accounts` ve todos | Se consulta según capacidades de Solicitud |

## API

```text
GET  /api/direct-expenses/eligible-policies
POST /api/direct-expenses
GET  /api/direct-expenses
GET  /api/direct-expenses/{record_id}/invoice
```

La definición normativa completa está en la
[Spec 022](../specs/022-direct-expense-registration/spec.md).
