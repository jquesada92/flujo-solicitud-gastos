# Plan — Notificaciones de Cargo y permisos efectivos

**Feature:** 010  
**Constitución vigente:** 2.9.0

## Backend

- ampliar `send_user_invitation()` para Cargo(s) y permisos efectivos;
- mantener `send_user_access_updated()` sin contraseña temporal;
- calcular resumen desde `UserPosition/Position` + `effective_permission_codes()`;
- en creación, enviar después de aplicar asignaciones y antes de commit;
- en actualización, comparar conjunto anterior/nuevo de `position_ids`;
- enviar solo si cambia realmente y el usuario queda activo;
- fallo de cambio de Cargo → rollback + 502.

## Frontend / superficie

La creación y configuración de Usuarios vive en:

```text
Configuración → Accesos → Usuarios
```

Feature 011 retiró Usuarios/Personas y Organigrama como pantallas independientes. No duplicar formularios de creación/cambio de Cargo fuera de Accesos.

## Pruebas

- invitación contiene Cargo y permisos efectivos;
- cambio real de Cargo recalcula/notifica;
- mismo Cargo no duplica correo;
- fallo revierte cambio;
- HTML/texto contienen Cargo y códigos;
- validar manualmente desde Accesos en Docker/SMTP.

## Documentación

Mantener sincronizados:

- Feature 010;
- Feature 011 cuando cambie la superficie de administración;
- EMAIL_CONFIGURATION;
- IAM_MODEL;
- README;
- prompt maestro;
- docs/README;
- HISTORY;
- CHANGELOG.

## Gates locales

```text
cd backend
python -m unittest tests.test_user_access_notifications -v
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```

No requiere migración nueva por la notificación. La cadena global del proyecto continúa hasta `0008` por features posteriores.
