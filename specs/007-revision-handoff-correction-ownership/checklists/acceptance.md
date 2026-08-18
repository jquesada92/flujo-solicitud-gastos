# Criterios de aceptación — Propiedad de corrección y envío a revisión

**Feature:** 007  
**Constitución:** 2.6.0

## Corrección

- [x] `ExpenseOut` expone `can_correct`.
- [x] `can_correct=true` para el solicitante original en estados corregibles.
- [x] `can_correct=true` para el Administrador del sistema protegido.
- [x] `can_correct=false` para un tercero aunque tenga `requests:create`.
- [x] `can_correct=false` para un tercero aunque tenga `requests:approve`.
- [x] `can_correct=false` para `CLOSED` y `CANCELLED`.
- [x] `PUT /resubmit` vuelve a validar solicitante/Admin del sistema en backend.
- [x] El endpoint no depende de `requests:create` para autorizar una solicitud existente.
- [x] Un tercero recibe 403 con instrucción de usar **Enviar a revisión**.
- [x] `request_type` sigue siendo inmutable durante corrección.
- [x] MULTI_QUOTE corregida excluye al solicitante original de la nueva población de votación.

## Enviar a revisión

- [x] `REVISION_REQUESTED` exige comentario de al menos 3 caracteres.
- [x] Una sola revisión válida lleva inmediatamente la solicitud a `NEEDS_REVISION`.
- [x] La revisión no requiere mayoría.
- [x] El paso del revisor queda `REVISION_REQUESTED`.
- [x] Las demás aprobaciones PENDING/WAITING quedan `EXPIRED`.
- [x] Se persiste comentario, actor y timestamp.
- [x] El solicitante recibe notificación con el comentario.
- [x] El solicitante recibe `CORRECT_REQUEST` en su dashboard.
- [x] Los otros aprobadores dejan de tener acción pendiente para esa ronda.
- [x] El Administrador del sistema no recibe automáticamente la tarea personal de corrección de solicitudes ajenas.

## Frontend / correo

- [x] La tabla de Solicitudes usa `x.can_correct` para mostrar **Corregir / reenviar**.
- [x] El formulario puede montarse en modo corrección para el Admin del sistema aunque no tenga `requests:create` productivo.
- [x] El modal usa la etiqueta **Enviar a revisión**.
- [x] El botón de revisión del modal exige comentario mínimo antes de habilitarse.
- [x] El correo de aprobación usa **ENVIAR A REVISIÓN** / **Enviar a revisión**.
- [x] **Enviar a revisión** y **Corregir / reenviar** son acciones visualmente distintas.
- [ ] Validar manualmente que un aprobador no vea **Corregir / reenviar** en una solicitud ajena.
- [ ] Validar manualmente que el solicitante sí vea **Corregir / reenviar**.
- [ ] Validar manualmente que el Administrador del sistema sí pueda corregir una solicitud ajena.
- [ ] Validar manualmente desde correo **Enviar a revisión** con comentario.
- [ ] Validar manualmente que la solicitud pase inmediatamente a `NEEDS_REVISION`.
- [ ] Validar manualmente que el solicitante vea la tarea y el comentario recibido.

## Pruebas automáticas

- [x] `test_multi_quote_revision.py` cubre tercero denegado.
- [x] `test_multi_quote_revision.py` cubre solicitante por propiedad sin permiso global de creación.
- [x] `test_pending_actions.py` cubre interrupción inmediata de una ronda MAJORITY.
- [x] `test_pending_actions.py` cubre comentario obligatorio y expiración de pares.
- [x] `test_frontend_dashboard_contract.py` protege `x.can_correct` y montaje de corrección.
- [ ] Suite backend completa ejecutada localmente en el head final.
- [ ] `npm run build` ejecutado localmente en el head final.
- [ ] Docker build/smoke ejecutado localmente en el head final.
- [ ] CI remoto verde cuando vuelva a existir cuota de GitHub Actions.

## Documentación

- [x] Constitución actualizada a 2.6.0.
- [x] Feature 007 spec creada.
- [x] Feature 007 plan creado.
- [x] Feature 007 criterios creados.
- [x] Feature 003 revisada/actualizada.
- [x] Feature 005 revisada/actualizada.
- [x] README actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] `docs/REQUEST_CORRECTIONS.md` actualizado.
- [x] `docs/REQUEST_TRACKING.md` actualizado.
- [x] `docs/FASTAPI_ARCHITECTURE.md` revisado/actualizado.
- [x] `docs/README.md` actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [ ] PR #9 actualizado con Feature 007 / Constitución 2.6.0.
