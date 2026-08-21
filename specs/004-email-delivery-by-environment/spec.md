# Spec 004 — Entrega de correo por ambiente

**Estado:** Implementada  
**Constitución:** 2.11.0

## Objetivo

Enviar notificaciones desde backend sin exponer secretos y con transporte configurable.

## Producción

```text
EMAIL_MODE=brevo
Backend Render → Brevo HTTPS API
```

## Desarrollo/local

```text
EMAIL_MODE=smtp
```

con host/puerto/seguridad/credenciales en variables de entorno. `console` puede usarse en tests sin entrega real.

## Seguridad

- credenciales solo backend/plataforma;
- `PUBLIC_URL` genera enlaces externos;
- no registrar contraseñas, tokens o secretos;
- fallos de entrega siguen la semántica transaccional del caso de uso que originó el correo.

## Notificaciones IAM

Invitación de usuario: contraseña temporal + Cargo opcional + permisos efectivos + URL. Cambio real de Cargo: actualización de Cargo y permisos actuales. Cargo no modifica permisos.
