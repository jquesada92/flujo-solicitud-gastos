# Spec 004 — Entrega de correo por ambiente

**Estado:** Implementada con guard productivo pendiente
**Constitución:** 2.18.0

## Objetivo

Enviar notificaciones desde backend sin exponer secretos y con transporte configurable.

## Producción

```text
EMAIL_MODE=brevo
Backend Render → Brevo HTTPS API
```

`render.yaml` fija `EMAIL_MODE=brevo`, pero Settings aún acepta `console` con `ENVIRONMENT=production`. Falta un guard runtime que rechace ese modo y valide `PUBLIC_URL` HTTPS/remitente antes de considerar cerrado el hardening fuera de Render.

## Desarrollo/local

```text
EMAIL_MODE=console  # default seguro de Docker Compose
```

SMTP solo se habilita explícitamente mediante `LOCAL_EMAIL_MODE=smtp` y host/puerto/seguridad/credenciales en variables de entorno. `console` es el transporte normal de pruebas sin entrega real.

## Seguridad

- credenciales solo backend/plataforma;
- `PUBLIC_URL` genera enlaces externos;
- no registrar credenciales de infraestructura;
- `console` muestra el cuerpo completo y puede incluir contraseñas temporales o tokens de restablecimiento/aprobación/votación: solo se usa localmente con datos ficticios y sus logs se tratan como sensibles;
- fallos de entrega siguen la semántica transaccional del caso de uso que originó el correo.

## Notificaciones IAM

Invitación de usuario: contraseña temporal + Cargo opcional + permisos efectivos + URL. Cambio real de Cargo: actualización de Cargo y permisos actuales. Cargo no modifica permisos.

El restablecimiento de contraseña usa un template distinto de la invitación. El
correo contiene únicamente un enlace de propósito exclusivo con vigencia de 30
minutos por defecto, nunca una contraseña. Si el transporte falla, la emisión se
revierte para conservar la vigencia del enlace anterior.
