# Configuración de correo por ambiente

## Matriz oficial del proyecto

| Ambiente | Frontend | Backend | Transporte de correo |
| --- | --- | --- | --- |
| Producción | Vercel | Render | Brevo HTTPS API |
| Local / development con Docker Compose | `http://localhost:3000` | Docker/FastAPI local | Google SMTP |
| Local con Vite directo | `http://localhost:5173` | FastAPI local | Google SMTP |
| Test automatizado | n/a | test runner | console/mocks según la prueba |

## URL pública usada en enlaces

Los enlaces de aprobación/votación se construyen desde `PUBLIC_URL`.

Docker Compose publica el frontend en:

```text
http://localhost:3000
```

Configuración local recomendada:

```env
PUBLIC_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

Si se ejecuta Vite directamente con `npm run dev`, el backend puede usar:

```env
PUBLIC_URL=http://localhost:5173
```

El host/puerto de un correo debe corresponder al frontend realmente activo.

## Local — Google SMTP

Crear `backend/.env` a partir de `backend/.env.example`:

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

Para cuentas Google con 2-Step Verification, usar App Password cuando la política de la cuenta lo permita. Nunca guardar la contraseña real ni secretos en repositorio, README, issues, PRs o logs.

## Producción — Brevo

Variables del backend en Render:

```env
ENVIRONMENT=production
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO_EN_BREVO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
PUBLIC_URL=<URL_HTTPS_DEL_FRONTEND_EN_VERCEL>
```

No colocar `BREVO_API_KEY`, `SMTP_PASSWORD` ni secretos equivalentes en Vercel/Vite.

## Probar transporte

Docker Compose:

```bash
docker compose exec backend python -m scripts.test_email --to destino@example.com
```

Sin Docker, desde `backend/`:

```bash
python -m scripts.test_email --to destino@example.com
```

El diagnóstico no debe imprimir secretos.

## Correos de acceso de usuario

La administración de usuarios se realiza canónicamente desde:

```text
Configuración → Accesos → Usuarios
```

No existe una pantalla Usuarios/Personas independiente.

### Invitación inicial

Cuando se crea un usuario activo desde **Accesos**, el correo de contraseña temporal incluye:

```text
Cargo(s)
Permisos efectivos
Usuario
Contraseña temporal
Enlace de acceso
```

Los permisos se calculan con IAM canónico después de aplicar Grupo/Rol/Cargo/permisos directos; no provienen de `can_*` ni `UserRole`.

### Cambio de Cargo

Cuando cambia realmente `position_ids` de un usuario activo desde Accesos, se envía **Actualización de cargo y permisos** con Cargos resultantes y permisos efectivos recalculados.

Guardar exactamente el mismo conjunto de Cargos no genera correo duplicado.

El correo de cambio de Cargo no contiene contraseña temporal.

### Semántica de fallo

Invitación inicial y cambio de Cargo son notificaciones obligatorias de administración de acceso.

Si falla el transporte:

- creación: no se confirma la operación;
- cambio de Cargo: se revierte la transacción y el endpoint devuelve 502.

Una futura outbox persistente podrá desacoplar entrega y transacción sin perder la garantía de notificación.

## Solicitudes después del SMTP

### SIMPLE

El correo de aprobación se genera cuando el flujo entra en aprobación. El destinatario debe ser usuario activo con permiso efectivo `requests:approve`, distinto del solicitante.

### MULTI_QUOTE

Al crear/reiniciar la ronda se envía invitación a cada usuario elegible con `requests:approve`, excluyendo al solicitante según la regla vigente.

En Docker Compose el enlace esperado comienza por:

```text
http://localhost:3000/email-action/...
```

## Diagnóstico

Si no llega correo:

```bash
docker compose logs backend --tail=200
```

Si el enlace responde `ERR_CONNECTION_REFUSED`, comparar puerto del enlace con el frontend activo:

```text
Docker Compose → localhost:3000
Vite directo   → localhost:5173
```

Si `EMAIL_MODE=console`, no existe entrega real; el mensaje solo aparece en logs.

Los correos de workflow pueden conservar actualmente el estado aunque falle el proveedor. Invitación inicial y cambio de Cargo son obligatorios. La convergencia futura recomendada es outbox/reintentos persistidos.
