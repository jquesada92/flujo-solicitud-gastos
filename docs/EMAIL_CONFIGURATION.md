# Configuración de correo por ambiente

## Matriz oficial del proyecto

| Ambiente | Frontend | Backend | Transporte de correo |
| --- | --- | --- | --- |
| Producción | Vercel | Render | Brevo HTTPS API |
| Local / development con Docker Compose | `http://localhost:3000` | Docker/FastAPI local | Google SMTP |
| Local con Vite directo | `http://localhost:5173` | FastAPI local | Google SMTP |
| Test automatizado | n/a | test runner | console/mocks según la prueba |

## URL pública usada en los enlaces de correo

Los enlaces de aprobación/votación se construyen desde `PUBLIC_URL`.

Cuando se usa Docker Compose, el frontend no vive en el puerto de desarrollo de Vite. Nginx se publica en:

```text
http://localhost:3000
```

Por eso `docker-compose.yml` sobreescribe el valor recibido desde `backend/.env` y fija por defecto:

```env
PUBLIC_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

Los valores pueden personalizarse desde el `.env` de la raíz mediante:

```env
LOCAL_PUBLIC_URL=http://localhost:3000
LOCAL_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

Si se ejecuta Vite directamente con `npm run dev`, sin el frontend de Docker Compose, entonces el backend puede usar:

```env
PUBLIC_URL=http://localhost:5173
```

Regla: el host/puerto que aparece en un correo debe corresponder al frontend que realmente está escuchando en ese modo de ejecución. Un enlace `localhost:5173` no funciona si solo está levantado Docker Compose en `localhost:3000`.

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
PUBLIC_URL=<URL_HTTPS_DEL_FRONTEND_EN_VERCEL>
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

Al abrir el correo en Docker Compose, el enlace esperado debe comenzar por:

```text
http://localhost:3000/email-action/...
```

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

Si el correo llega pero el enlace responde `ERR_CONNECTION_REFUSED`, comparar el puerto del enlace con el modo de frontend activo:

```text
Docker Compose → localhost:3000
Vite directo   → localhost:5173
```

Si `EMAIL_MODE=console`, no habrá correo real: el mensaje aparecerá únicamente en los logs.

La aplicación conserva actualmente el estado del workflow aunque falle el proveedor de correo. Por eso un correo ausente no implica necesariamente que no se haya creado la aprobación o invitación. Esta separación debe mantenerse hasta implementar una outbox/reintentos persistidos.
