# Criterios de aceptación — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.5.0

## Acceso base

- [x] Todo usuario activo obtiene `requests:read` aunque no tenga grupo, rol o permiso directo.
- [x] `permission_sources()` identifica `requests:read` como acceso base del producto.
- [x] `users_with_permission('requests:read')` devuelve todos los usuarios activos.
- [x] Un usuario inactivo no puede autenticarse ni ejercer el baseline.
- [x] Quitar `requests:read` de roles/asignaciones no elimina la capacidad base del usuario activo.

## Inicio / Dashboard

- [x] `GET /api/expenses/dashboard` requiere autenticación y `requests:read` efectivo.
- [x] Un usuario sin permisos organizacionales puede cargar el dashboard.
- [x] Las métricas generales son visibles para cualquier usuario activo.
- [x] `pending_my_action` no presenta cierres a usuarios sin `requests:close`.
- [x] `pending_my_action` no presenta aprobaciones/votaciones a usuarios sin `requests:approve`.
- [x] Las votaciones personales se determinan mediante invitaciones activas de la ronda.
- [x] Solicitudes propias en `NEEDS_REVISION` aparecen como `CORRECT_REQUEST` solo si el usuario mantiene `requests:create`.
- [x] `pending_my_action` cuenta acciones concretas vigentes, no permisos abstractos.
- [x] Cada `pending_item` devuelve los códigos de acción correspondientes al usuario actual.
- [x] **Acciones que requieren mi atención** es un KPI informativo y no un botón.
- [x] **Solicitudes en proceso** es un KPI informativo y no un botón.
- [x] Los KPIs superiores no tienen `onClick` ni ejecutan navegación/acciones.
- [ ] Validar manualmente en Docker que los KPIs superiores no respondan a clic ni teclado como controles.

## Modal de acciones pendientes

- [x] Seleccionar una fila de **Acciones pendientes** ejecuta `openAction(item)` y no el handler genérico de **Ver todas**.
- [x] **Ver todas** conserva navegación a Solicitudes.
- [x] El modal consulta `GET /api/expenses/{request_id}/my-actions` al abrirse.
- [x] El backend revalida las acciones contra permisos + asignación/estado vigente.
- [x] El modal soporta `APPROVAL_DECISION`.
- [x] El modal soporta `QUOTATION_VOTE`.
- [x] El modal soporta `CLOSE_REQUEST`.
- [x] El modal soporta `CORRECT_REQUEST` con acceso explícito al editor de Solicitudes.
- [x] Aprobación contextual no expone el token bearer usado por links de correo.
- [x] Aprobación contextual permite Aprobar / Rechazar / Solicitar corrección.
- [x] Votación contextual muestra opciones y soportes antes de votar.
- [x] Cierre contextual permite cargar factura y notas.
- [x] Después de una mutación se recargan dashboard y detalle contextual.
- [x] Si otra sesión/canal ya atendió la tarea, el modal puede quedar sin acciones y lo informa explícitamente.
- [x] El modal usa `role=dialog`, `aria-modal=true` y soporta cierre con Escape.
- [ ] Validar manualmente en Docker que hacer clic en una aprobación pendiente abra el modal sin navegar a Solicitudes.
- [ ] Validar manualmente Aprobar desde el modal y confirmar que la acción desaparezca/cambie.
- [ ] Validar manualmente Rechazar desde el modal.
- [ ] Validar manualmente Solicitar corrección desde el modal con comentario requerido por el motor.
- [ ] Validar manualmente una votación MULTI_QUOTE desde el modal.
- [ ] Validar manualmente carga de factura/cierre desde el modal con usuario `requests:close`.

## Seguimiento de solicitudes

- [x] `GET /api/expenses` está servido por una ruta canónica registrada antes del router legacy.
- [x] La lista no filtra por `UserRole.REQUESTER`.
- [x] La lista no filtra por `requested_by == current_user.email`.
- [x] Un usuario puede ver una solicitud creada por otro usuario.
- [x] Se conserva el comportamiento operativo de solicitudes abiertas y cerradas recientes.
- [x] Se mantienen eager loads para evitar N+1 de relaciones usadas por la tabla/detalle.

## Cancelación de solicitudes abiertas

- [x] `POST /api/expenses/{request_id}/cancel` está servido por una ruta canónica antes del router legacy.
- [x] El solicitante original puede cancelar su propia solicitud abierta.
- [x] El Administrador del sistema identificado mediante `system_accounts` puede cancelar cualquier solicitud abierta.
- [x] Un usuario ajeno con `requests:create` no puede cancelar una solicitud de otro usuario.
- [x] `requests:approve` o `config:manage` no conceden por sí mismos cancelación de solicitudes ajenas.
- [x] `QUOTATION_VOTING` es cancelable por solicitante/admin del sistema.
- [x] `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION` y `APPROVED` son cancelables mientras sigan abiertos.
- [x] `CLOSED`, `CANCELLED` y `REJECTED` no son cancelables.
- [x] Cancelar exige motivo y persiste actor, timestamp y razón.
- [x] La lista devuelve `can_cancel` por solicitud.
- [x] El frontend usa `can_cancel` en vez de inferir la acción desde `can_request` o cargos.
- [ ] Validar manualmente en producción que el solicitante vea **Cancelar solicitud** durante `QUOTATION_VOTING`.
- [ ] Validar manualmente que otro usuario que solo da seguimiento no vea **Cancelar solicitud** para esa solicitud.
- [ ] Validar manualmente que el Administrador del sistema sí vea la acción para una solicitud abierta ajena.

## Separación de permisos

- [x] Tener solo `requests:read` no concede `requests:create`.
- [x] Tener solo `requests:read` no concede `requests:approve`.
- [x] Tener solo `requests:read` no concede `requests:close`.
- [x] Tener solo `requests:read` no concede `config:manage`.
- [x] Backend sigue siendo autoridad aunque el frontend muestre/oculte botones.

## Frontend

- [x] Inicio está disponible para usuarios autenticados.
- [x] Solicitudes está disponible para usuarios autenticados.
- [x] `can_view` se deriva temporalmente desde `requests:read` y resulta `true` para usuarios activos.
- [x] `HomeDashboard` dispone de implementación modular en `frontend/src/home-dashboard.jsx`.
- [x] Vite elimina la implementación legacy completa de `HomeDashboard` durante build en vez de parchear handlers internos.
- [x] Los KPIs superiores se renderizan como `article` informativos.
- [x] Las únicas interacciones de seguimiento son filas de acciones concretas y controles explícitos como **Ver todas**.
- [ ] Validar manualmente con un usuario sin roles que Inicio carga sin error.
- [ ] Validar manualmente que ese usuario vea una solicitud creada por otro usuario.
- [ ] Validar manualmente que ese usuario no pueda crear, aprobar o cerrar si no recibe esos permisos.

## Pruebas automáticas

- [x] Existe `test_universal_tracking.py`.
- [x] Existe `test_request_cancellation.py`.
- [x] Existe `test_pending_actions.py`.
- [x] Existe `test_frontend_dashboard_contract.py`.
- [x] Prueba baseline de lectura sin asignaciones.
- [x] Prueba lectura de solicitud de otro usuario.
- [x] Prueba dashboard universal.
- [x] Prueba población universal de `requests:read`.
- [x] Prueba negativa de cierre sin `requests:close`.
- [x] Prueba negativa de cancelación ajena aun con `requests:create`.
- [x] Prueba cancelación propia en `QUOTATION_VOTING`.
- [x] Prueba cancelación por cuenta técnica.
- [x] Prueba negativa de cancelación de solicitud cerrada.
- [x] Prueba de acción de aprobación contextual y mutación autenticada.
- [x] Prueba de acción de votación contextual.
- [x] Prueba de corrección/cierre personalizados por usuario.
- [x] Contrato frontend exige modal y revalidación posterior a mutación.
- [x] Contrato frontend impide reintroducir KPIs superiores como botones interactivos.
- [ ] Suite backend completa ejecutada localmente en el head final.
- [ ] `npm run build` ejecutado localmente en el head final.
- [ ] Docker build/smoke ejecutado localmente en el head final.
- [ ] CI remoto verde cuando vuelva a existir cuota de GitHub Actions.

## Documentación

- [x] Constitución 2.5.0 revisada; no requiere bump porque la separación KPI informativo/acción explícita es una concreción UX de Feature 005, no un cambio de principio constitucional.
- [x] Spec funcional actualizada.
- [x] Plan técnico actualizado.
- [x] Criterios de aceptación actualizados.
- [x] README revisado para mantener el Dashboard como resumen y las filas como interacción.
- [x] PROMPT_RECONSTRUCCION revisado con la misma regla UX.
- [x] IAM_MODEL no requiere cambio semántico por este ajuste visual.
- [x] FASTAPI_ARCHITECTURE no requiere cambio backend por este ajuste visual.
- [x] `docs/REQUEST_TRACKING.md` actualizado.
- [x] HISTORY actualizado preservando las entradas anteriores.
- [x] CHANGELOG actualizado.
- [x] docs/README revisado.
- [ ] PR #9 actualizado con contrato final y nota de cuota agotada de Actions.
