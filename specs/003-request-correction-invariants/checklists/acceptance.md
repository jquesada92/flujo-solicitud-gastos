# Criterios de aceptación — Correcciones de solicitudes

## Tipo de solicitud

- [x] Corregir una solicitud SIMPLE conserva `request_type=SIMPLE`.
- [x] Corregir una solicitud MULTI_QUOTE conserva `request_type=MULTI_QUOTE`.
- [x] El backend rechaza con 409 un intento de cambiar el tipo durante `resubmit`.
- [x] El frontend restaura el tipo original al entrar en modo corrección.
- [x] En una corrección MULTI_QUOTE la UI vuelve a mostrar el editor de múltiples cotizaciones.

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

## Frontend legacy

- [x] `vite.config.js` restaura estado MULTI_QUOTE durante dev/build.
- [x] El transform considera evidencia existente.
- [x] El transform falla explícitamente si los fragmentos legacy esperados desaparecen.
- [ ] **Deuda:** retirar el transform al modularizar `ExpenseForm` fuera de `main.jsx`.

## Pruebas

- [x] Existe test HTTP que corrige una MULTI_QUOTE y verifica que sigue siendo MULTI_QUOTE.
- [x] El test verifica preservación de attachment.
- [x] El test verifica limpieza de votos.
- [x] El test verifica reemplazo de invitación.
- [x] El test verifica 409 al intentar MULTI_QUOTE → SIMPLE.
- [x] Backend tests y frontend build del commit funcional pasaron antes del cierre documental final.
- [ ] Todos los jobs del commit documental final deben quedar verdes antes de considerar esta corrección terminada.

## Documentación

- [x] Constitución actualizada a 2.3.1.
- [x] Spec funcional creada.
- [x] Plan técnico creado.
- [x] Criterios de aceptación actualizados.
- [x] README actualizado y declara Constitución 2.3.1.
- [x] Prompt maestro actualizado.
- [x] `docs/REQUEST_CORRECTIONS.md` agregado.
- [x] Arquitectura FastAPI actualizada con la ruta canónica y el transform temporal.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] Índice documental actualizado y referencia la Constitución 2.3.1.
- [x] Terminología actualizada para SIMPLE, MULTI_QUOTE y Corrección / Corregir y reenviar.
- [x] Feature 002 spec/plan/checklist revisados para la Constitución vigente 2.3.1 y la relación con Feature 003.
- [ ] Descripción final del PR debe incluir la corrección y la Constitución 2.3.1.
