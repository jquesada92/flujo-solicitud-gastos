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
- [x] EMAIL_CONFIGURATION actualizado.
- [x] IAM_MODEL actualizado.
- [x] docs/README actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] README principal actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [ ] PR #9 actualizado.
