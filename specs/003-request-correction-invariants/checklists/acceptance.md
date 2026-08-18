# Criterios de aceptación — Correcciones de solicitudes

**Constitución:** 2.3.3

## Tipo de solicitud

- [x] Corregir una solicitud SIMPLE conserva `request_type=SIMPLE`.
- [x] Corregir una solicitud MULTI_QUOTE conserva `request_type=MULTI_QUOTE`.
- [x] El backend rechaza con 409 un intento real de cambiar el tipo durante `resubmit`.
- [x] El frontend deriva el tipo desde la solicitud al entrar en modo corrección.
- [x] La pestaña SIMPLE/MULTI_QUOTE seleccionada antes de pulsar Corregir no determina el tipo del editor.
- [x] Cambiar a otra solicitud en corrección vuelve a derivar el tipo desde esa solicitud.
- [x] Durante corrección el tipo se muestra como dato de solo lectura, no como selector editable.

## Layout MULTI_QUOTE

- [x] Existe `frontend/src/expense-form.jsx` como formulario canónico.
- [x] `effectiveRequestType` gobierna layout, validación, payload y uploads.
- [x] Un draft `QUOTATION_VOTING` renderiza **Opciones para votación**.
- [x] Un draft con dos o más `quotation_options` renderiza **Opciones para votación** aunque el flag persistido sea legacy.
- [x] Una corrección MULTI_QUOTE no renderiza los campos SIMPLE de monto/proveedor/soporte único como estructura principal.
- [x] `vite.config.js` importa el formulario modular y elimina del bundle la función `ExpenseForm` legacy completa.
- [x] El formulario recibe `key` por solicitud/flujo para evitar herencia de estado entre correcciones.

## Compatibilidad de datos históricos

- [x] Un registro con `request_type=SIMPLE` y estado `QUOTATION_VOTING` se reconoce como MULTI_QUOTE.
- [x] Un registro con `request_type=SIMPLE` y dos o más `quotation_options` se reconoce como MULTI_QUOTE.
- [x] El endpoint canónico repara defensivamente `request_type` al corregir un registro legacy inconsistente.
- [x] Existe Alembic `20260817_0003_backfill_multi_quote_request_type.py` para reparar filas históricas.
- [x] La cadena Alembic queda `0000 → 0001 → 0002 → 0003` con un único head.

## Cotizaciones y evidencia

- [x] Se restauran proveedor, monto, URL y observaciones de cada opción existente.
- [x] Un attachment existente satisface la validación de soporte sin exigir volver a seleccionar el archivo local.
- [x] La UI indica cuando una opción conserva un soporte existente.
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

## Pruebas

- [x] Existe test HTTP que corrige una MULTI_QUOTE y verifica que sigue siendo MULTI_QUOTE.
- [x] Existe test HTTP que simula `request_type=SIMPLE` legacy con evidencia MULTI_QUOTE y verifica reparación.
- [x] El test verifica preservación de attachment.
- [x] El test verifica limpieza de votos.
- [x] El test verifica reemplazo de invitación.
- [x] El test verifica 409 al intentar MULTI_QUOTE → SIMPLE cuando el tipo canónico es múltiple.
- [x] Existe `test_frontend_revision_contract.py` para verificar el formulario modular y su integración de build.
- [ ] Verificar manualmente: con pestaña **Solicitud sencilla** activa, corregir una MULTI_QUOTE debe mostrar **Tipo de solicitud: Múltiples cotizaciones** y **Opciones para votación**.
- [ ] Verificar manualmente que no aparezcan los campos SIMPLE `Monto (USD)`, `Proveedor`, `URL del producto o servicio` y soporte único fuera de las tarjetas de cotización.
- [ ] Confirmar CI verde del head final de esta corrección.

## Documentación

- [x] Constitución revisada: la regla ya existe en 2.3.3 y no requiere nueva versión.
- [x] Spec funcional actualizada con formulario modular.
- [x] Plan técnico actualizado.
- [x] Criterios de aceptación actualizados.
- [ ] README actualizado para retirar la descripción del parche granular anterior.
- [ ] Prompt maestro actualizado con la implementación modular.
- [ ] `docs/REQUEST_CORRECTIONS.md` actualizado.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] PR actualizado con la causa y solución final.
