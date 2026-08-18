# Criterios de aceptación — Correcciones de solicitudes

**Constitución:** 2.6.0

## Autoridad de corrección

- [x] Solo el solicitante original o el Administrador del sistema pueden ejecutar `resubmit`.
- [x] `requests:create` no autoriza a corregir una solicitud ajena.
- [x] `requests:approve` no autoriza a corregir una solicitud ajena.
- [x] `config:manage` no autoriza a corregir una solicitud ajena.
- [x] `ExpenseOut` expone `can_correct` calculado por recurso.
- [x] La tabla usa `can_correct` como señal UX en vez de `canEdit` global.
- [x] El backend vuelve a autorizar aunque la UI sea manipulada.
- [x] El Administrador del sistema puede entrar en modo corrección aunque en producción no tenga `requests:create`.
- [x] Un aprobador ajeno recibe 403 con instrucción de usar **Enviar a revisión**.
- [ ] Validar manualmente que un aprobador ajeno no vea **Corregir / reenviar**.
- [ ] Validar manualmente que solicitante y Administrador del sistema sí puedan corregir.

## Tipo de solicitud

- [x] Corregir SIMPLE conserva `request_type=SIMPLE`.
- [x] Corregir MULTI_QUOTE conserva `request_type=MULTI_QUOTE`.
- [x] El backend rechaza con 409 un cambio real del tipo.
- [x] El frontend deriva el tipo desde la solicitud al entrar en corrección.
- [x] La pestaña SIMPLE/MULTI_QUOTE previa no determina el editor.
- [x] Cambiar a otra solicitud vuelve a derivar su tipo.
- [x] El tipo se muestra como dato de solo lectura.

## Layout MULTI_QUOTE

- [x] Existe `frontend/src/expense-form.jsx` como formulario canónico.
- [x] `effectiveRequestType` gobierna layout, validación, payload y uploads.
- [x] `QUOTATION_VOTING` o dos/más opciones infieren MULTI_QUOTE.
- [x] Una corrección MULTI_QUOTE no renderiza el layout SIMPLE como estructura principal.
- [x] Vite importa el formulario modular y elimina la función legacy completa.
- [x] El build no parchea el punto de montaje por whitespace.
- [x] `expense-form.jsx` rehidrata por `draft.request_id`/`flow_id`.

## Compatibilidad histórica

- [x] Flag SIMPLE + evidencia MULTI_QUOTE se reconoce/repara como MULTI_QUOTE.
- [x] Existe Alembic `0003` para reparar `request_type` histórico.
- [x] La cadena global vigente incluye `0000 → 0001 → 0002 → 0003 → 0004`.

## Cotizaciones y evidencia

- [x] Se restauran proveedor, monto, URL y observaciones.
- [x] Un attachment existente satisface la validación sin volver a seleccionarlo.
- [x] Attachments conservan asociación con sus opciones.
- [x] No se cambia la cantidad de opciones durante esta feature.

## Nueva ronda

- [x] Una corrección genera `flow_id` nuevo.
- [x] Votos vigentes anteriores se limpian.
- [x] Invitaciones anteriores se reemplazan.
- [x] La nueva población se resuelve desde `requests:approve`.
- [x] La población siempre excluye al **solicitante original**, incluso si Admin del sistema ejecuta la corrección.
- [x] La solicitud vuelve a `QUOTATION_VOTING`.
- [x] Se limpia selección previa de ganador/proveedor/monto.
- [x] Historial append-only no se reescribe.

## Handoff de revisión

- [x] Feature 007 separa **Enviar a revisión** de **Corregir / reenviar**.
- [x] `CORRECT_REQUEST` pertenece al solicitante original en `NEEDS_REVISION`.
- [x] El Administrador del sistema conserva capacidad administrativa sin convertirse en responsable normal de la tarea.

## Pruebas

- [x] Test HTTP MULTI_QUOTE preserva tipo y ronda.
- [x] Test HTTP cubre fila legacy SIMPLE con evidencia MULTI_QUOTE.
- [x] Test cubre 409 por cambio de tipo.
- [x] Test cubre 403 para aprobador no propietario.
- [x] Test cubre corrección del solicitante por propiedad sin depender de `requests:create` global.
- [x] Test frontend protege formulario modular.
- [x] Test frontend protege `x.can_correct` mientras la tabla siga legacy.
- [x] Regresión manual histórica del editor MULTI_QUOTE fue completada previamente.
- [ ] Suite actual completa ejecutada localmente después de Feature 007.

## Documentación

- [x] Constitución actualizada a 2.6.0 por Feature 007.
- [x] Spec actualizada con propiedad de corrección.
- [x] Plan actualizado.
- [x] Feature 007 documenta el handoff de revisión.
- [ ] README/prompt/docs derivados sincronizados con 2.6.0.
- [ ] HISTORY/CHANGELOG registran el cambio.
- [ ] PR #9 registra la regla final.
