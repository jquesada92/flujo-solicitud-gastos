# Criterios de aceptación — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución:** 2.8.0

## Creación

- [x] invitación incluye Cargo(s).
- [x] invitación incluye permisos efectivos legibles + código.
- [x] permisos provienen del IAM canónico.
- [x] contraseña temporal sigue apareciendo solo en invitación inicial.

## Cambio de Cargo

- [x] cambiar realmente `position_ids` dispara correo.
- [x] correo muestra Cargo(s) resultante(s).
- [x] correo muestra permisos efectivos recalculados.
- [x] guardar el mismo Cargo no duplica correo.
- [x] fallo de entrega revierte el cambio y devuelve 502.
- [ ] validar manualmente correo real en Docker/SMTP.

## Pruebas

- [x] existe `test_user_access_notifications.py`.
- [ ] test específico ejecutado localmente en head final.
- [ ] suite backend completa ejecutada localmente.
- [ ] frontend build ejecutado localmente después de pull final.

## Documentación

- [x] Constitución revisada; permanece 2.8.0.
- [x] spec/plan/checklist Feature 010.
- [ ] EMAIL_CONFIGURATION actualizado.
- [ ] IAM_MODEL actualizado.
- [ ] README principal actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] docs/README actualizado.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] PR #9 actualizado.
