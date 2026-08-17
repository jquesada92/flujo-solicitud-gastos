# Plan técnico — Correcciones de solicitudes

**Constitución:** 2.3.2

## Arquitectura

La corrección se implementa mediante una ruta canónica registrada antes del router legacy:

```text
frontend ExpenseForm
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
- actualiza cada opción por `option_number`/orden existente;
- conserva attachments vinculados a los IDs de opciones existentes;
- limpia `QuotationVote` vigente;
- reemplaza `QuotationVotingInvitation`;
- conserva eventos históricos de voto;
- limpia ganador/proveedor/monto seleccionado;
- vuelve a `QUOTATION_VOTING`;
- crea nuevas invitaciones desde `users_with_permission('requests:approve')`.

## Reparación de datos

Se agrega Alembic `20260817_0003_backfill_multi_quote_request_type.py` después de `0002`.

La migración cambia a `MULTI_QUOTE` filas históricas que todavía tienen el default `SIMPLE` pero presentan evidencia inequívoca de flujo múltiple. No elimina opciones, attachments, votos históricos ni eventos.

Cadena:

```text
0000 → 0001 → 0002 → 0003
```

## Frontend legacy

`main.jsx` sigue siendo monolítico. Para evitar una modificación masiva y frágil mientras se completa su modularización, `vite.config.js` contiene un plugin de compatibilidad de build/dev que transforma únicamente fragmentos conocidos de `ExpenseForm`.

La transformación ahora tiene dos defensas de estado:

1. el `requestType` inicial se deriva del `draft`/evidencia durable, no se inicializa ciegamente en SIMPLE al corregir;
2. `ExpenseForm` recibe una `key` dependiente de `request_id + flow_id/status`, por lo que entrar en corrección o cambiar de solicitud fuerza un remount y descarta el estado previo de las pestañas de creación.

Además:

- ejecuta `setRequestType()` desde el tipo inferido del draft;
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
- un registro legacy con `request_type=SIMPLE` + evidencia múltiple se infiere y repara como MULTI_QUOTE;
- flow_id cambia;
- opciones se actualizan;
- attachment existente se conserva;
- votos vigentes se eliminan;
- invitación anterior se sustituye;
- intento MULTI_QUOTE → SIMPLE retorna 409.

`tests/test_migrations.py` exige que `0003` sea el único Alembic head.

El job frontend ejecuta `npm run build`; el plugin Vite falla si los marcadores legacy esperados no coinciden.

La prueba manual de regresión debe comenzar explícitamente con **Solicitud sencilla** seleccionada, pulsar **Corregir / reenviar** sobre una MULTI_QUOTE y verificar que el editor abre como múltiple sin interacción previa con la pestaña.

## Retiro futuro

Cuando `ExpenseForm` sea extraído de `main.jsx`:

1. mover la lógica de hidratación a funciones/componentes normales;
2. crear tests frontend unitarios para draft SIMPLE/MULTI_QUOTE y aislamiento de estado;
3. retirar `legacyRevisionSafetyPlugin` de `vite.config.js`;
4. mantener el invariant backend de `request_type` independientemente de la UI.
