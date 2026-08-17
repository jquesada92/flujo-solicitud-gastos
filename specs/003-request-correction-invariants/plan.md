# Plan técnico — Correcciones de solicitudes

## Arquitectura

La corrección se implementa mediante una ruta canónica registrada antes del router legacy:

```text
frontend ExpenseForm
        ↓ PUT /api/expenses/{request_id}/resubmit
revision_actions.py
        ↓
Expense + QuotationOption + votes/invitations
```

## Backend canónico

`app/api/revision_actions.py` es responsable de:

1. requerir `requests:create`;
2. validar Área + Categoría;
3. localizar y bloquear la solicitud;
4. impedir corrección de una solicitud cerrada;
5. exigir `payload.request_type == expense.request_type`;
6. invalidar aprobaciones abiertas del flujo anterior;
7. generar un `flow_id` nuevo;
8. actualizar los campos comunes;
9. reiniciar el flujo según el tipo original.

### SIMPLE

- permanece `SIMPLE`;
- actualiza monto/proveedor/URL;
- conserva soportes existentes;
- reinicia aprobación cuando existe soporte suficiente.

### MULTI_QUOTE

- permanece `MULTI_QUOTE`;
- conserva la cantidad actual de `QuotationOption`;
- actualiza cada opción por `option_number`/orden existente;
- conserva attachments vinculados a los IDs de opciones existentes;
- limpia `QuotationVote` vigente;
- reemplaza `QuotationVotingInvitation`;
- conserva eventos históricos de voto;
- limpia ganador/proveedor/monto seleccionado;
- vuelve a `QUOTATION_VOTING`;
- crea nuevas invitaciones desde `users_with_permission('requests:approve')`.

## Frontend legacy

`main.jsx` sigue siendo monolítico. Para evitar una modificación masiva y frágil mientras se completa su modularización, `vite.config.js` contiene un plugin de compatibilidad de build/dev que transforma únicamente fragmentos conocidos de `ExpenseForm`.

La transformación:

- hace `setRequestType(draft.request_type)`;
- reconstruye `quoteOptions` desde `draft.quotation_options`;
- marca `existing_attachment` usando `draft.attachments`;
- considera ese soporte en validación/Pydantic payload;
- restablece SIMPLE al salir del modo corrección;
- oculta agregar/eliminar opciones durante la corrección.

`replaceRequired()` hace fallar el build si cambia el fragmento legacy y ya no puede aplicarse el parche. No se permite una degradación silenciosa.

## Motivo de conservar cantidad de opciones

Eliminar o reordenar opciones con evidencia asociada requiere semántica explícita de versionado/eliminación de documentos. Esta feature evita hacer borrado destructivo o perder trazabilidad. Por ahora se permiten correcciones de contenido, no de estructura de la ronda.

## Testing

`tests/test_multi_quote_revision.py` usa `FastAPI TestClient` y SQLite aislado para verificar:

- MULTI_QUOTE permanece MULTI_QUOTE;
- flow_id cambia;
- opciones se actualizan;
- attachment existente se conserva;
- votos vigentes se eliminan;
- invitación anterior se sustituye;
- intento MULTI_QUOTE → SIMPLE retorna 409.

El job frontend ejecuta `npm run build`; el plugin Vite falla si los marcadores legacy esperados no coinciden.

## Retiro futuro

Cuando `ExpenseForm` sea extraído de `main.jsx`:

1. mover la lógica de hidratación a funciones/componentes normales;
2. crear tests frontend unitarios para draft SIMPLE/MULTI_QUOTE;
3. retirar `legacyRevisionSafetyPlugin` de `vite.config.js`;
4. mantener el invariant backend de `request_type` independientemente de la UI.
