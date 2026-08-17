# Especificación funcional — Entrega de correo por ambiente

**Feature:** 004-email-delivery-by-environment  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17

## Objetivo

Definir de forma explícita qué proveedor de correo utiliza cada ambiente y cómo se valida la entrega antes de probar flujos de aprobación.

## Regla funcional

### Producción

La arquitectura productiva separa frontend y backend:

- frontend: Vercel;
- backend: Render;
- correo transaccional: Brevo HTTPS API.

Configuración esperada del backend productivo:

```env
ENVIRONMENT=production
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
```

### Local / desarrollo

El backend local debe usar Gmail o Google Workspace mediante SMTP autenticado para realizar pruebas reales de correo.

Configuración canónica local:

```env
ENVIRONMENT=development
EMAIL_MODE=smtp
EMAIL_FROM=<CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
```

También se admite `SMTP_PORT=587` con `SMTP_SECURITY=starttls`.

La contraseña SMTP local debe ser una App Password cuando la cuenta Google la requiera. No se debe guardar una contraseña real ni una App Password en Git.

## Historias de usuario

### US-001 — Probar correo local real

Como desarrollador quiero usar Google SMTP en local para confirmar que las invitaciones de aprobación/votación llegan realmente antes de desplegar.

### US-002 — Mantener Brevo en producción

Como operador quiero que producción continúe usando Brevo aunque desarrollo use Google SMTP, evitando acoplar el entorno productivo a credenciales personales de Google.

### US-003 — Diagnosticar el transporte independientemente del workflow

Como desarrollador quiero ejecutar una prueba de correo directa usando exactamente la misma configuración del backend para distinguir un problema de SMTP de un problema en el flujo de aprobación.

## Reglas

1. `EMAIL_MODE=console` no entrega correo real; solo registra el contenido en logs.
2. `EMAIL_MODE=smtp` utiliza la configuración `SMTP_*`.
3. `EMAIL_MODE=brevo` utiliza `BREVO_API_KEY` y un `EMAIL_FROM` válido/verificado.
4. Ninguna credencial real se almacena en `.env.example`, README, specs, logs o repositorio.
5. El comando `python -m scripts.test_email --to <correo>` debe usar el mismo `Settings` y servicio de correo que la aplicación.
6. Un fallo de entrega no debe hacer creer que el workflow nunca creó la aprobación: la entrega de correo y el estado transaccional del workflow deben poder diagnosticarse por separado.

## Fuera de alcance

- OAuth2 SMTP de Google;
- proveedor de correo configurable desde la UI;
- colas/reintentos persistidos de correo;
- webhook de entrega/bounce de Brevo;
- plantillas editables por organización.
