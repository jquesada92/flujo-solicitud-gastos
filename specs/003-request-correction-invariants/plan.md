# Plan técnico — Correcciones de solicitudes

**Constitución:** 2.3.3

## Arquitectura

La corrección se implementa mediante una ruta backend canónica y un formulario frontend modular:

```text
frontend/src/expense-form.jsx
        ↓ PUT /api/expenses/{request_id}/resubmit
revision_actions.py
        ↓
Expense + QuotationOption + votes/invitations
```

La pestaña SIMPLE/MULTI_QUOTE de creación no es fuente de verdad para una corrección.

## Backend canónico

`app/api/revision_actions.py` es responsable de:

1. requerir `requests:create`;
2. validar Área + Categoría;
3. localizar y bloquear la solicitud;
4. impedir corrección de una solicitud cerrada;
5. derivar el tipo canónico desde `request_type` + evidencia durable de cotizaciones;
6. rechazar un payload que intente cambiar ese tipo canónico;
7. reparar defensivamente un `request_type` legacy inconsistente;
8. invalidar aprobaciones abiertas del flujo anterior;
9. generar un `flow_id` nuevo;
10. actualizar los campos comunes;
11. reiniciar el flujo según el tipo canónico.

La inferencia defensiva considera MULTI_QUOTE cuando:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options.length >= 2
```

### SIMPLE

- permanece `SIMPLE`;
- actualiza monto/proveedor/URL;
- conserva soportes existentes;
- reinicia aprobación cuando existe soporte suficiente.

### MULTI_QUOTE

- permanece `MULTI_QUOTE`;
- conserva la cantidad actual de `QuotationOption`;
- actualiza cada opción por orden existente;
- conserva attachments vinculados a IDs de opciones existentes;
- limpia `QuotationVote` vigente;
- reemplaza `QuotationVotingInvitation`;
- conserva eventos históricos de voto;
- limpia ganador/proveedor/monto seleccionado;
- vuelve a `QUOTATION_VOTING`;
- crea nuevas invitaciones desde `users_with_permission('requests:approve')`.

## Reparación de datos

Alembic `20260817_0003_backfill_multi_quote_request_type.py` cambia a `MULTI_QUOTE` filas históricas que todavía tienen el default `SIMPLE` pero presentan evidencia inequívoca de flujo múltiple. No elimina opciones, attachments, votos históricos ni eventos.

Cadena:

```text
0000 → 0001 → 0002 → 0003
```

## Frontend canónico

`frontend/src/expense-form.jsx` es ahora la implementación mantenible del formulario de solicitudes.

La función:

```text
resolveRequestType(draft)
```

retorna `MULTI_QUOTE` si el draft tiene `request_type=MULTI_QUOTE`, estado `QUOTATION_VOTING` o dos/más `quotation_options`.

El componente calcula:

```text
effectiveRequestType = draft ? resolveRequestType(draft) : requestType
```

Ese valor gobierna todo el formulario durante una corrección:

- qué layout se renderiza;
- qué validaciones se ejecutan;
- qué `request_type` viaja al backend;
- si se usan campos SIMPLE o `quotation_options`;
- qué soportes se cargan después del resubmit.

Para un `draft` MULTI_QUOTE el componente no renderiza el formulario sencillo como estructura principal; restaura directamente el editor de opciones de cotización.

Los soportes existentes se representan con `existing_attachment`; el navegador no intenta prellenar `<input type=file>`.

Durante corrección se oculta el selector de tipo y se muestra un indicador de solo lectura. También se conserva la cantidad de opciones para evitar cambios destructivos de evidencia.

## Integración temporal con main.jsx

`main.jsx` todavía contiene la función legacy por deuda de modularización histórica. `vite.config.js` aplica una extracción estructural mínima:

1. importa `ExpenseForm` desde `./expense-form.jsx`;
2. elimina del bundle la definición legacy comprendida entre `function ExpenseForm` y `function ClosurePanel`;
3. no modifica el punto de montaje JSX ni depende de indentación, saltos de línea o cadenas exactas del `<ExpenseForm>`.

El componente modular ya rehidrata su estado cuando cambian `draft.request_id` o `draft.flow_id`, por lo que no requiere que Vite inyecte una `key` por reemplazo textual.

El build falla si no puede aislar la frontera completa de la definición legacy. CI inspecciona además el `dist/` generado para confirmar que contiene las marcas inequívocas del formulario modular.

## Motivo de conservar cantidad de opciones

Eliminar o reordenar opciones con evidencia asociada requiere semántica explícita de versionado/eliminación de documentos. Esta feature evita borrado destructivo o pérdida de trazabilidad. Por ahora se permiten correcciones de contenido, no de estructura de la ronda.

## Testing

`tests/test_multi_quote_revision.py` usa `FastAPI TestClient` para verificar invariantes backend.

`tests/test_frontend_revision_contract.py` exige que:

- exista `frontend/src/expense-form.jsx`;
- `effectiveRequestType` gobierne render y payload;
- `QUOTATION_VOTING` y dos/más opciones infieran MULTI_QUOTE;
- se restauren opciones y soportes existentes;
- `vite.config.js` retire el ExpenseForm legacy del bundle e importe el modular;
- no exista nuevamente un parche textual del punto de montaje.

El job frontend ejecuta `npm run build` e inspecciona el bundle resultante; una extracción inválida, JSX inválido o ausencia del formulario modular falla CI.

La prueba manual de regresión debe comenzar explícitamente con **Solicitud sencilla** seleccionada, pulsar **Corregir / reenviar** sobre una MULTI_QUOTE y verificar que el formulario visible contiene **Opciones para votación** y no los campos de solicitud sencilla.

## Retiro futuro

Cuando `main.jsx` sea modularizado completamente:

1. importar `ExpenseForm` directamente desde el source normal;
2. retirar `modularExpenseFormPlugin` de `vite.config.js`;
3. mantener tests frontend del componente;
4. mantener el invariant backend de `request_type` independientemente de la UI.
