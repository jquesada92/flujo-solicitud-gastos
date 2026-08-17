# Criterios de aceptación — Correcciones de solicitudes

**Constitución:** 2.3.2

## Tipo de solicitud

- [x] Corregir una solicitud SIMPLE conserva `request_type=SIMPLE`.
- [x] Corregir una solicitud MULTI_QUOTE conserva `request_type=MULTI_QUOTE`.
- [x] El backend rechaza con 409 un intento real de cambiar el tipo durante `resubmit`.
- [x] El frontend deriva el tipo desde la solicitud al entrar en modo corrección.
- [x] En una corrección MULTI_QUOTE la UI vuelve a mostrar el editor de múltiples cotizaciones.
- [x] La pestaña SIMPLE/MULTI_QUOTE seleccionada antes de pulsar Corregir no determina el tipo del editor.
- [x] Entrar en corrección fuerza un remount del formulario y descarta el estado de creación previo.
- [x] Cambiar a otra solicitud en corrección vuelve a derivar el tipo desde esa solicitud.

## Compatibilidad de datos históricos

- [x] Un registro con `request_type=SIMPLE` y estado `QUOTATION_VOTING` se reconoce como MULTI_QUOTE.
- [x] Un registro con `request_type=SIMPLE` y dos o más `quotation_options` se reconoce como MULTI_QUOTE.
- [x] El endpoint canónico repara defensivamente `request_type` al corregir un registro legacy inconsistente.
- [x] Existe Alembic `20260817_0003_backfill_multi_quote_request_type.py` para reparar filas históricas.
- [x] La cadena Alembic queda `0000 → 0001 → 0002 → 0003` con un único head.

## Cotizaciones y evidencia

- [x] Se restauran proveedor, monto, URL y observaciones de cada opción existente.
- [x] Un attachment existente satisface la validación de soporte sin exigir volver a seleccionar el archivo local.
- [x] Los attachments existentes permanecen asociados a los IDs de opciones conservados.
- [x] Durante esta feature no se permite cambiar la cantidad de opciones en modo corrección.
- [x] La UI oculta Agregar/Eliminar opción durante una corrección MULTI_QUOTE.

## Nueva ronda

- [x] Una corrección genera un `flow_id` nuevo.
- [x] Los votos vigentes de la ronda anterior dejan de formar parte del estado actual.
- [x] Las invitaciones anteriores se eliminan/reemplazan.
- [x] La nueva población se resuelve desde `requests:approve`.
- [x] La solicitud corregida vuelve a `QUOTATION_VOTING`.
- [x] `selected_quotation_id`, `supplier` y `amount` seleccionados se limpian antes de la nueva votación.
- [x] Los eventos históricos append-only no se reescriben.

## Backend

- [x] Existe una ruta canónica `revision_actions.py` registrada antes de `expenses.py` legacy.
- [x] `resubmit` requiere `requests:create`.
- [x] Área + Categoría se validan antes de aplicar la corrección.
- [x] Una solicitud CLOSED no puede corregirse.
- [x] El backend mantiene el invariant aunque el frontend envíe un tipo incorrecto.
- [x] El backend no depende de la pestaña visual para decidir SIMPLE/MULTI_QUOTE.

## Frontend legacy

- [x] `vite.config.js` deriva el tipo inicial desde el draft/evidencia durable durante dev/build.
- [x] `ExpenseForm` recibe una `key` de corrección para evitar heredar estado de la pestaña anterior.
- [x] El transform considera evidencia existente.
- [x] El transform falla explícitamente si los fragmentos legacy esperados desaparecen.
- [ ] **Deuda:** retirar el transform al modularizar `ExpenseForm` fuera de `main.jsx`.

## Pruebas

- [x] Existe test HTTP que corrige una MULTI_QUOTE y verifica que sigue siendo MULTI_QUOTE.
- [x] Existe test HTTP que simula `request_type=SIMPLE` legacy con evidencia MULTI_QUOTE y verifica reparación.
- [x] El test verifica preservación de attachment.
- [x] El test verifica limpieza de votos.
- [x] El test verifica reemplazo de invitación.
- [x] El test verifica 409 al intentar MULTI_QUOTE → SIMPLE cuando el tipo canónico es múltiple.
- [ ] Verificar manualmente: con pestaña **Solicitud sencilla** activa, corregir una MULTI_QUOTE debe abrir directamente el editor múltiple.
- [ ] Todos los jobs del commit final de esta corrección deben quedar verdes antes de considerarla terminada.

## Documentación

- [x] Constitución actualizada a 2.3.2.
- [x] Spec funcional actualizada con aislamiento de estado y datos legacy.
- [x] Plan técnico actualizado.
- [x] Criterios de aceptación actualizados.
- [x] README actualizado a Constitución 2.3.2 y migración 0003.
- [x] Prompt maestro actualizado.
- [x] `docs/REQUEST_CORRECTIONS.md` actualizado.
- [x] Arquitectura FastAPI actualizada con migración 0003 y aislamiento de estado.
- [x] Política documental clasifica fugas de estado UI con impacto de negocio como cambios funcionales.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] Índice documental actualizado.
- [x] Terminología distingue selector de nueva solicitud y corrección.
- [x] Feature 002 spec/plan/checklist sincronizados con Constitución 2.3.2 y Alembic 0003.
- [ ] PR actualizado con la causa exacta del bug.
