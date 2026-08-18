# Plan técnico — Entrega de correo por ambiente

## Arquitectura

El servicio canónico continúa en `app/services/email_service.py` y selecciona transporte mediante `Settings.email_mode`:

```text
EMAIL_MODE=console → log solamente
EMAIL_MODE=smtp    → smtplib / Google SMTP local
EMAIL_MODE=brevo   → Brevo HTTPS API productiva
```

No se duplica lógica de plantillas por proveedor.

## Construcción de enlaces

`app/services/email_service.py` construye enlaces de aprobación/votación desde `Settings.public_url`.

El valor debe corresponder al frontend realmente accesible:

```text
Docker Compose → http://localhost:3000
Vite directo   → http://localhost:5173
Producción     → URL HTTPS del frontend en Vercel
```

Para evitar que un `backend/.env` con `PUBLIC_URL=http://localhost:5173` genere enlaces inválidos mientras el desarrollador usa Docker Compose, `docker-compose.yml` sobreescribe de forma intencional:

```env
PUBLIC_URL=${LOCAL_PUBLIC_URL:-http://localhost:3000}
CORS_ALLOWED_ORIGINS=${LOCAL_CORS_ALLOWED_ORIGINS:-http://localhost:3000,http://localhost:5173}
```

El `.env` de la raíz documenta `LOCAL_PUBLIC_URL` y `LOCAL_CORS_ALLOWED_ORIGINS`. `backend/.env` continúa siendo la fuente de las credenciales SMTP y demás Settings de FastAPI.

## Local

`backend/.env` no se versiona. Se recomienda:

```env
EMAIL_MODE=smtp
EMAIL_FROM=<CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
```

`docker-compose.yml` carga `backend/.env` mediante `env_file`, mantiene la base de datos local aislada y reemplaza únicamente los Settings dependientes de cómo se publica el frontend local.

## Producción

Render conserva las variables del backend:

```env
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
PUBLIC_URL=<URL_HTTPS_FRONTEND_VERCEL>
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

Un correo aceptado por SMTP no valida por sí solo que el link sea alcanzable. La prueba de flujo debe comprobar también que, bajo Compose, el link comience por `http://localhost:3000/email-action/`.

## Seguridad

- no versionar `backend/.env`;
- no imprimir `SMTP_PASSWORD` ni `BREVO_API_KEY`;
- para Gmail/Workspace usar App Password cuando aplique;
- `EMAIL_FROM` local debe coincidir con `SMTP_USER` salvo que la cuenta tenga un alias autorizado;
- producción no reutiliza credenciales personales de Google;
- no exponer secretos en `LOCAL_PUBLIC_URL` ni variables frontend.

## Testing

Agregar/regresar pruebas de configuración que garanticen:

- `EMAIL_MODE=smtp` exige usuario + password;
- el modo `console` no intenta red;
- el modo `brevo` exige API key;
- el script diagnóstico es importable desde la imagen backend;
- Docker Compose publica frontend en 3000 y proporciona al backend `PUBLIC_URL` consistente con ese puerto;
- la documentación distingue Compose 3000 de Vite 5173.

## Deuda futura

La entrega actualmente es best-effort: un error de proveedor se registra y el workflow permanece guardado. Una feature futura puede introducir outbox persistente, estados de entrega, reintentos y webhooks sin cambiar el contrato funcional de aprobación.
