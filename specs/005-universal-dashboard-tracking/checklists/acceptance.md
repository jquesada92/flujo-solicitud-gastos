# Criterios de aceptación — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.6.0

## Acceso base

- [x] Todo usuario activo obtiene `requests:read` aunque no tenga grupo, rol o permiso directo.
- [x] `permission_sources()` identifica `requests:read` como acceso base.
- [x] `users_with_permission('requests:read')` devuelve usuarios activos.
- [x] Usuario inactivo no puede autenticarse.

## Inicio / Dashboard

- [x] `GET /api/expenses/dashboard` requiere `requests:read` efectivo.
- [x] Métricas generales son visibles para usuario activo.
- [x] Aprobaciones/votaciones personales requieren `requests:approve` + asignación concreta.
- [x] Cierres personales requieren `requests:close`.
- [x] Solicitud propia `NEEDS_REVISION` aparece como `CORRECT_REQUEST` por propiedad, sin depender de `requests:create`.
- [x] `pending_my_action` cuenta tareas concretas.
- [x] Cada `pending_item` devuelve códigos de acción.
- [x] KPIs superiores son `article` informativos, sin `onClick`.
- [ ] Validar manualmente que KPIs no respondan como controles.

## Modal de acciones pendientes

- [x] Fila pendiente ejecuta `openAction(item)`.
- [x] **Ver todas** navega a Solicitudes.
- [x] Modal consulta `GET /api/expenses/{request_id}/my-actions`.
- [x] Backend revalida permiso + asignación + estado.
- [x] Soporta `APPROVAL_DECISION`, `QUOTATION_VOTE`, `CLOSE_REQUEST`, `CORRECT_REQUEST`.
- [x] Aprobación contextual no expone token bearer de correo.
- [x] Aprobación contextual permite Aprobar / Rechazar / **Enviar a revisión**.
- [x] **Enviar a revisión** exige comentario mínimo antes de habilitar el botón.
- [x] Backend también rechaza revisión sin comentario válido.
- [x] Una revisión válida pasa inmediatamente a `NEEDS_REVISION` y expira aprobaciones restantes.
- [x] El solicitante recibe `CORRECT_REQUEST`; otros aprobadores dejan de tener acción vigente.
- [x] Votación contextual muestra opciones/soportes.
- [x] Cierre contextual permite factura/notas.
- [x] Después de mutación se recargan dashboard + detalle.
- [x] Modal soporta Escape y `role=dialog`/`aria-modal`.
- [ ] Validar manualmente aprobación, rechazo y **Enviar a revisión**.
- [ ] Validar manualmente votación MULTI_QUOTE.
- [ ] Validar manualmente cierre con `requests:close`.

## Seguimiento y capacidades por recurso

- [x] `GET /api/expenses` no filtra por requester.
- [x] Usuario puede ver solicitudes ajenas.
- [x] Lista devuelve `can_cancel`.
- [x] Lista devuelve `can_correct`.
- [x] `can_correct` solo es true para solicitante/Admin del sistema en estados corregibles.
- [x] `requests:create` no habilita corrección de solicitudes ajenas.
- [x] Frontend usa `x.can_correct` para **Corregir / reenviar** mientras la tabla siga legacy.
- [ ] Validar manualmente que aprobador ajeno no vea **Corregir / reenviar**.
- [ ] Validar manualmente que solicitante/Admin sí lo vean.

## Cancelación

- [x] Solicitante original puede cancelar solicitud abierta.
- [x] Administrador del sistema puede cancelar solicitud abierta.
- [x] Otro usuario no puede hacerlo por permisos mutables.
- [x] `CLOSED`, `CANCELLED`, `REJECTED` no son cancelables.
- [x] Motivo/actor/timestamp se persisten.

## Separación de permisos

- [x] `requests:read` no concede create/approve/close/config.
- [x] `requests:create` crea nuevas solicitudes pero no concede edición de solicitudes ajenas.
- [x] Backend sigue siendo autoridad aunque frontend muestre/oculte controles.

## Frontend

- [x] `HomeDashboard` modular existe.
- [x] Wording **Enviar a revisión** y validación de comentario viven directamente en `home-dashboard.jsx`.
- [x] Vite no parchea wording/handlers internos del Dashboard.
- [x] Vite solo mantiene bridges temporales del monolito para `can_cancel`, `can_correct` y montaje modular.

## Pruebas automáticas

- [x] `test_universal_tracking.py`.
- [x] `test_request_cancellation.py`.
- [x] `test_pending_actions.py`.
- [x] `test_frontend_dashboard_contract.py`.
- [x] Revisión inmediata MAJORITY + comentario obligatorio + expiración de pares.
- [x] Contrato frontend protege KPIs, modal, wording y `can_correct`.
- [ ] Suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente en head final.
- [ ] Docker build/smoke ejecutado localmente en head final.
- [ ] CI remoto verde cuando vuelva la cuota de GitHub Actions.

## Documentación

- [x] Constitución actualizada a 2.6.0 por Feature 007.
- [x] Feature 005 spec/plan/acceptance alineados.
- [x] Feature 007 define ownership/handoff.
- [ ] README/PROMPT/docs derivados sincronizados con 2.6.0.
- [ ] HISTORY/CHANGELOG actualizados.
- [ ] PR #9 actualizado con regla final.
