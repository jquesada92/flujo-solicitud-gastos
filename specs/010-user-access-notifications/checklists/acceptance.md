# Criterios de aceptación — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución vigente:** 2.9.0

## Creación

- [x] invitación incluye Cargo(s).
- [x] invitación incluye permisos efectivos legibles + código.
- [x] permisos provienen del IAM canónico.
- [x] contraseña temporal aparece solo en invitación inicial.
- [x] superficie canónica de creación es **Accesos → Usuarios**.

## Cambio de Cargo

- [x] cambiar realmente `position_ids` dispara correo.
- [x] correo muestra Cargo(s) resultante(s).
- [x] correo muestra permisos efectivos recalculados.
- [x] guardar el mismo Cargo no duplica correo.
- [x] fallo de entrega revierte cambio y devuelve 502.
- [x] cambio se realiza desde la experiencia consolidada de Accesos, no desde una pantalla Organigrama independiente.
- [ ] validar manualmente correo real en Docker/SMTP desde Accesos.

## Pruebas

- [x] existe `test_user_access_notifications.py`.
- [ ] test específico ejecutado localmente en head final.
- [ ] suite backend completa ejecutada localmente.
- [ ] frontend build ejecutado localmente después del pull final.

## Documentación

- [x] Constitución vigente actualizada a 2.9.0.
- [x] spec/plan/checklist Feature 010 alineados con Accesos.
- [x] EMAIL_CONFIGURATION actualizado.
- [x] IAM_MODEL actualizado.
- [x] docs/README actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] README principal actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] Feature 011 documenta la consolidación de Usuarios/Organigrama.
