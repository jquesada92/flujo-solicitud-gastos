# Configuración de correo por ambiente

## Matriz oficial del proyecto

| Ambiente | Frontend | Backend | Transporte de correo |
| --- | --- | --- | --- |
| Producción | Vercel | Render | Brevo HTTPS API |
| Local / development | localhost | Docker/FastAPI local | Google SMTP |
| Test automatizado | n/a | test runner | console/mocks según la prueba |

## Local — Google SMTP

Crear `backend/.env` a partir de `backend/.env.example` y configurar:

```env
ENVIRONMENT=development
EMAIL_MODE=smtp
EMAIL_FROM=tu-cuenta@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=tu-cuenta@gmail.com
SMTP_PASSWORD=<APP_PASSWORD_DE_GOOGLE>
```

Alternativa:

```env
SMTP_PORT=587
SMTP_SECURITY=starttls
```

Google SMTP requiere autenticación. Para cuentas con 2-Step Verification, usar una App Password. No usar ni guardar la contraseña real de la cuenta en el repositorio.

### Crear App Password

1. Activar 2-Step Verification en la cuenta Google.
2. Crear una App Password para esta aplicación cuando la cuenta lo permita.
3. Copiarla únicamente a `backend/.env` como `SMTP_PASSWORD`.
4. No pegarla en README, issues, PRs, screenshots ni chats compartidos.

Algunas cuentas administradas, Advanced Protection o configuraciones basadas solo en security keys pueden no ofrecer App Passwords; en esos casos se debe usar la política permitida por el administrador de Google Workspace.

## Producción — Brevo

Las variables pertenecen al servicio backend en Render:

```env
ENVIRONMENT=production
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO_EN_BREVO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
```

No colocar `BREVO_API_KEY`, `SMTP_PASSWORD` ni secretos equivalentes en Vercel/Vite. El frontend solo necesita variables públicas como la URL del backend y timezone.

## Probar el transporte antes del workflow

Dentro de Docker Compose:

```bash
docker compose exec backend python -m scripts.test_email --to destino@example.com
```

Sin Docker, desde `backend/`:

```bash
python -m scripts.test_email --to destino@example.com
```

La salida muestra el transporte usado, host/puerto cuando aplica y remitente/destinatario, pero nunca imprime la contraseña ni la API key.

Si el comando termina con:

```text
Email accepted by the configured transport.
```

el servidor SMTP/API aceptó la entrega. Después se valida el workflow real.

## Probar solicitudes después del SMTP

### Solicitud SIMPLE

El correo de aprobación se genera cuando el flujo entra en aprobación. Si la solicitud exige un archivo, esto puede ocurrir después de cargar el soporte. El destinatario debe ser un usuario activo con permiso efectivo `requests:approve`, distinto del solicitante.

### MULTI_QUOTE

Al crear/reiniciar la ronda se envía una invitación de votación a cada usuario elegible con `requests:approve`, excluyendo al solicitante según la regla actual.

## Diagnóstico

Si no llega el correo:

```bash
docker compose logs backend --tail=200
```

Buscar mensajes como:

```text
Email delivery failed
Quotation voting email delivery failed
```

Si `EMAIL_MODE=console`, no habrá correo real: el mensaje aparecerá únicamente en los logs.

La aplicación conserva actualmente el estado del workflow aunque falle el proveedor de correo. Por eso un correo ausente no implica necesariamente que no se haya creado la aprobación o invitación. Esta separación debe mantenerse hasta implementar una outbox/reintentos persistidos.
