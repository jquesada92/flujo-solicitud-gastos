# Correo y notificaciones

## Modos

Producción:

```text
EMAIL_MODE=brevo
```

usa Brevo HTTPS API desde el backend.

En producción `console` no es un modo aceptable. El código actualmente conserva `console` como valor por defecto y no lo rechaza solo por estar en producción; por eso `EMAIL_MODE=brevo` debe verificarse expresamente antes de desplegar, junto con `BREVO_API_KEY`, un `EMAIL_FROM` verificado y un `PUBLIC_URL` HTTPS correcto.

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

Compose prevalece sobre `EMAIL_MODE` definido en `backend/.env`. No cambies `LOCAL_EMAIL_MODE` durante pruebas funcionales normales y no reutilices archivos de variables de Render/Neon en el stack local.

## Seguridad

Credenciales solo en variables de entorno/plataforma. Nunca exponerlas en Vite, repositorio o logs.

El modo `console` escribe el cuerpo completo del mensaje en los logs. Eso puede incluir contraseñas temporales y enlaces tokenizados de restablecimiento/aprobación/votación. Los logs locales se tratan como sensibles y no se publican en issues, PR ni conversaciones. Si producción arranca accidentalmente en `console`, se detiene la operación y se corrige la configuración antes de crear usuarios o solicitudes.

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

## Restablecimiento de contraseña

El restablecimiento usa un template propio, distinto de la invitación. Para un
Usuario activo no técnico contiene:

```text
enlace {PUBLIC_URL}/reset-password#token=...
vigencia del enlace
indicación de ignorarlo si no fue solicitado
```

No incluye contraseña temporal, contraseña nueva ni hash. El token tiene
propósito exclusivo, un solo uso y expira después de
`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` (30 minutos por defecto). Un enlace nuevo
invalida los anteriores del Usuario.

Emitir no cambia la contraseña, `must_change_password` ni las sesiones. Si el
proveedor falla, se revierte `password_reset_version`, por lo que el enlace
anterior conserva su vigencia. El consumo válido revoca sesiones e invalida todos
los enlaces, pero no inicia sesión automáticamente.

## Actualización de Cargo

Si cambia realmente `position_ids` de un usuario activo:

1. se aplica el nuevo Cargo (0..1);
2. se calculan los permisos actuales desde Permisos propios de Roles y herencia aditiva de Grupos;
3. se envía “Actualización de cargo y permisos”.

Guardar el mismo Cargo no debe duplicar el correo.

## Semántica transaccional

La creación de usuario/invitación y la actualización de Cargo siguen las garantías implementadas por `iam_users.py`; los tests de notificación son parte del contrato.

La emisión del enlace y su entrega también forman una unidad lógica: el fallo de
correo no puede dejar vigente una emisión que el destinatario no recibió ni
invalidar el enlace anterior. Las pruebas usan mocks o `console`, nunca un envío
externo. En modo `console`, el enlace queda visible en el log local sensible por
diseño; fuera de ese modo los logs ordinarios no registran tokens.

## Diagnóstico local

```bash
docker compose exec -T backend python -m scripts.test_email --to recipient@example.com
```

Con la configuración local predeterminada este comando no entrega correo externo: valida el render y deja el mensaje en `docker compose logs backend`. Para una prueba SMTP/Brevo real se requiere autorización explícita, credenciales exclusivas del entorno no productivo y un destinatario de prueba controlado.

No ejecutar `scripts.test_email` en producción como smoke test automático. Enviar un correo es una mutación externa y requiere aprobación y destinatario acordado.
