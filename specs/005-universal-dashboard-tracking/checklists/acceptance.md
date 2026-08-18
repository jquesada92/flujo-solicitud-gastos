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
- [x] Prueba baseline de lectura sin asignaciones.
- [x] Prueba lectura de solicitud de otro usuario.
- [x] Prueba dashboard universal.
- [x] Prueba población universal de `requests:read`.
- [x] Prueba negativa de cierre sin `requests:close`.
- [ ] CI del head final completamente verde.

## Documentación

- [x] Constitución actualizada a 2.4.0.
- [x] Spec funcional creada.
- [x] Plan técnico creado.
- [x] Criterios de aceptación creados.
- [ ] README actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] IAM_MODEL actualizado.
- [ ] Documentación de seguimiento creada/actualizada.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] docs/README actualizado.
- [ ] PR actualizado con contrato final y evidencia CI.
