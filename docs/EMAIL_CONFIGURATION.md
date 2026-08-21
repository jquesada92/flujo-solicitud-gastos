# Correo y notificaciones

## Modos

Producción:

```text
EMAIL_MODE=brevo
```

usa Brevo HTTPS API desde el backend.

Local/desarrollo puede usar SMTP de forma explícita:

```text
EMAIL_MODE=smtp
SMTP_HOST
SMTP_PORT
SMTP_SECURITY
SMTP_USER
SMTP_PASSWORD
```

Docker Compose local usa `EMAIL_MODE=console` por defecto para impedir entregas accidentales durante pruebas. Solo debe cambiarse con `LOCAL_EMAIL_MODE` cuando la entrega real sea el objetivo explícito.

## Seguridad

Credenciales solo en variables de entorno/plataforma. Nunca exponerlas en Vite, repositorio o logs.

## Invitación de usuario

Para usuario activo recién creado, el correo incluye:

```text
correo
contraseña temporal
Cargo, si existe
permisos efectivos
PUBLIC_URL
```

El Cargo se obtiene de `UserPosition → Position`; los permisos se calculan con `effective_permission_codes()`. Cargo no modifica permisos.

## Actualización de Cargo

Si cambia realmente `position_ids` de un usuario activo:

1. se aplica el nuevo Cargo (0..1);
2. se calculan los permisos actuales desde Grupos/Roles;
3. se envía “Actualización de cargo y permisos”.

Guardar el mismo Cargo no debe duplicar el correo.

## Semántica transaccional

La creación de usuario/invitación y la actualización de Cargo siguen las garantías implementadas por `iam_users.py`; los tests de notificación son parte del contrato.

## Diagnóstico local

```bash
docker compose exec backend python -m scripts.test_email --to recipient@example.com
```
