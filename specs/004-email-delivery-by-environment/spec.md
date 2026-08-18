# Especificación funcional — Entrega de correo por ambiente

**Feature:** 004-email-delivery-by-environment  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17

## Objetivo

Definir de forma explícita qué proveedor de correo utiliza cada ambiente, cómo se valida la entrega y cómo se garantiza que los enlaces enviados apunten al frontend realmente accesible en ese modo de ejecución.

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
PUBLIC_URL=<URL_HTTPS_DEL_FRONTEND_EN_VERCEL>
```

### Local / desarrollo con Docker Compose

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

El frontend de Docker Compose se publica en `http://localhost:3000`. Por tanto los enlaces de aprobación/votación generados por el backend deben usar ese origen mientras Compose sea el modo de ejecución activo.

`docker-compose.yml` debe sobreescribir la URL pública del backend con:

```env
PUBLIC_URL=http://localhost:3000
```

salvo que el desarrollador defina explícitamente otro `LOCAL_PUBLIC_URL` accesible.

### Local con Vite directo

Cuando el frontend se ejecuta directamente con `npm run dev`, el puerto esperado es `5173` y `PUBLIC_URL=http://localhost:5173` es válido.

El puerto de una URL enviada por correo debe corresponder siempre al frontend que realmente está escuchando.

También se admite `SMTP_PORT=587` con `SMTP_SECURITY=starttls`.

La contraseña SMTP local debe ser una App Password cuando la cuenta Google la requiera. No se debe guardar una contraseña real ni una App Password en Git.

## Historias de usuario

### US-001 — Probar correo local real

Como desarrollador quiero usar Google SMTP en local para confirmar que las invitaciones de aprobación/votación llegan realmente antes de desplegar.

### US-002 — Mantener Brevo en producción

Como operador quiero que producción continúe usando Brevo aunque desarrollo use Google SMTP, evitando acoplar el entorno productivo a credenciales personales de Google.

### US-003 — Diagnosticar el transporte independientemente del workflow

Como desarrollador quiero ejecutar una prueba de correo directa usando exactamente la misma configuración del backend para distinguir un problema de SMTP de un problema en el flujo de aprobación.

### US-004 — Abrir acciones desde el correo local

Como desarrollador que usa Docker Compose quiero que los enlaces del correo apunten al frontend local publicado en `localhost:3000`, para poder abrir la pantalla de aprobación/votación sin modificar manualmente la URL.

## Reglas

1. `EMAIL_MODE=console` no entrega correo real; solo registra el contenido en logs.
2. `EMAIL_MODE=smtp` utiliza la configuración `SMTP_*`.
3. `EMAIL_MODE=brevo` utiliza `BREVO_API_KEY` y un `EMAIL_FROM` válido/verificado.
4. Ninguna credencial real se almacena en `.env.example`, README, specs, logs o repositorio.
5. El comando `python -m scripts.test_email --to <correo>` debe usar el mismo `Settings` y servicio de correo que la aplicación.
6. Un fallo de entrega no debe hacer creer que el workflow nunca creó la aprobación: la entrega de correo y el estado transaccional del workflow deben poder diagnosticarse por separado.
7. `PUBLIC_URL` es la fuente de verdad para construir links enviados por correo.
8. Docker Compose debe apuntar por defecto a `http://localhost:3000`; Vite directo puede usar `http://localhost:5173`.
9. Un cambio de modo de ejecución requiere regenerar nuevos correos; los correos ya enviados conservan la URL existente en su contenido.

## Fuera de alcance

- OAuth2 SMTP de Google;
- proveedor de correo configurable desde la UI;
- colas/reintentos persistidos de correo;
- webhook de entrega/bounce de Brevo;
- plantillas editables por organización.
