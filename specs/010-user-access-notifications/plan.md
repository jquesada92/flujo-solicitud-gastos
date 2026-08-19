# Plan — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución:** 2.8.0

## Backend

- ampliar `send_user_invitation()` para recibir Cargos y permisos efectivos;
- crear `send_user_access_updated()` sin contraseña temporal;
- calcular resumen desde `UserPosition/Position` + `effective_permission_codes()`;
- en creación, enviar después de aplicar asignaciones y antes de commit;
- en actualización, comparar conjunto anterior/nuevo de `position_ids`;
- solo enviar si el conjunto cambió realmente y el usuario queda activo;
- si falla la entrega del cambio de Cargo, rollback + 502.

## Pruebas

- invitación contiene Cargo y `requests:read`/permisos heredados;
- cambio Vocal → Tesorero recalcula permisos y notifica;
- guardar Tesorero → Tesorero no duplica correo;
- fallo de correo revierte cambio de Cargo;
- HTML/texto contienen Cargo y códigos de permisos.

## Documentación

Actualizar EMAIL_CONFIGURATION, IAM_MODEL, README, prompt maestro, índice docs, HISTORY, CHANGELOG y PR #9.

## Gates locales

```text
cd backend
python -m unittest tests.test_user_access_notifications -v
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```

No requiere nueva migración Alembic.
