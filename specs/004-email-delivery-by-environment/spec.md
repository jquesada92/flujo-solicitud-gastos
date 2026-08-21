# Spec 004 — Entrega de correo por ambiente

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Enviar notificaciones desde backend sin exponer secretos y con transporte configurable.

## Producción

```text
EMAIL_MODE=brevo
Backend Render → Brevo HTTPS API
```

## Desarrollo/local

```text
EMAIL_MODE=console  # default seguro de Docker Compose
```

SMTP solo se habilita explícitamente mediante `LOCAL_EMAIL_MODE=smtp` y host/puerto/seguridad/credenciales en variables de entorno. `console` es el transporte normal de pruebas sin entrega real.

## Seguridad

- credenciales solo backend/plataforma;
- `PUBLIC_URL` genera enlaces externos;
- no registrar contraseñas, tokens o secretos;
- fallos de entrega siguen la semántica transaccional del caso de uso que originó el correo.

## Notificaciones IAM

Invitación de usuario: contraseña temporal + Cargo opcional + permisos efectivos + URL. Cambio real de Cargo: actualización de Cargo y permisos actuales. Cargo no modifica permisos.
