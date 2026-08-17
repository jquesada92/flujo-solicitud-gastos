# Plan técnico — Entrega de correo por ambiente

## Arquitectura

El servicio canónico continúa en `app/services/email_service.py` y selecciona transporte mediante `Settings.email_mode`:

```text
EMAIL_MODE=console → log solamente
EMAIL_MODE=smtp    → smtplib / Google SMTP local
EMAIL_MODE=brevo   → Brevo HTTPS API productiva
```

No se duplica lógica de plantillas por proveedor.

## Local

`backend/.env` es la fuente local y no se versiona. Se recomienda:

```env
EMAIL_MODE=smtp
EMAIL_FROM=<CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
```

`docker-compose.yml` ya carga `backend/.env` mediante `env_file` y mantiene la base de datos local aislada.

## Producción

Render conserva las variables del backend:

```env
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
```

Vercel conserva únicamente variables del frontend. Las credenciales de Brevo/SMTP nunca deben existir en Vite/Vercel.

## Diagnóstico

`scripts/test_email.py` ejecuta el mismo `_send()` del servicio de correo y permite validar el transporte sin crear una solicitud:

```bash
python -m scripts.test_email --to usuario@example.com
```

Dentro de Docker Compose:

```bash
docker compose exec backend python -m scripts.test_email --to usuario@example.com
```

El script muestra modo, host, puerto, seguridad, remitente y destinatario, pero nunca imprime secretos.

## Seguridad

- no versionar `backend/.env`;
- no imprimir `SMTP_PASSWORD` ni `BREVO_API_KEY`;
- para Gmail/Workspace usar App Password cuando aplique;
- `EMAIL_FROM` local debe coincidir con `SMTP_USER` salvo que la cuenta tenga un alias autorizado;
- producción no reutiliza credenciales personales de Google.

## Testing

Agregar/regresar pruebas de configuración que garanticen:

- `EMAIL_MODE=smtp` exige usuario + password;
- el modo `console` no intenta red;
- el modo `brevo` exige API key;
- el script diagnóstico es importable desde la imagen backend.

## Deuda futura

La entrega actualmente es best-effort: un error de proveedor se registra y el workflow permanece guardado. Una feature futura puede introducir outbox persistente, estados de entrega, reintentos y webhooks sin cambiar el contrato funcional de aprobación.
