# Criterios de aceptación — Dashboard y seguimiento universal

**Feature:** 005  
**Constitución:** 2.4.0

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
- [ ] Validar manualmente con un usuario sin roles que Inicio carga sin error.
- [ ] Validar manualmente que ese usuario vea una solicitud creada por otro usuario.
- [ ] Validar manualmente que ese usuario no pueda crear, aprobar o cerrar si no recibe esos permisos.

## Pruebas automáticas

- [x] Existe `test_universal_tracking.py`.
- [x] Existe `test_request_cancellation.py`.
- [x] Prueba baseline de lectura sin asignaciones.
- [x] Prueba lectura de solicitud de otro usuario.
- [x] Prueba dashboard universal.
- [x] Prueba población universal de `requests:read`.
- [x] Prueba negativa de cierre sin `requests:close`.
- [x] Prueba negativa de cancelación ajena aun con `requests:create`.
- [x] Prueba cancelación propia en `QUOTATION_VOTING`.
- [x] Prueba cancelación por cuenta técnica.
- [x] Prueba negativa de cancelación de solicitud cerrada.
- [ ] CI del head final completamente verde.

## Documentación

- [x] Constitución 2.4.0 revisada; no requiere bump adicional porque la regla de cancelación concreta el principio existente de backend authoritative sin alterar el baseline universal.
- [x] Spec funcional actualizada.
- [x] Plan técnico actualizado.
- [x] Criterios de aceptación actualizados.
- [ ] README actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] IAM_MODEL actualizado.
- [ ] Documentación de seguimiento creada/actualizada.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] docs/README actualizado.
- [ ] PR actualizado con contrato final y evidencia CI.
