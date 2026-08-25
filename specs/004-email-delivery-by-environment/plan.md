# Plan 004 — Correo

- Centralizar envío en `app/services/email_service.py`.
- Seleccionar transporte desde Settings.
- Mantener Brevo para producción y SMTP para local cuando se configure.
- Probar templates y errores sin enviar secretos.
- Mantener `scripts/test_email.py` como diagnóstico manual.
- Actualizar ejemplos de `.env` cuando cambie una variable requerida.
- Rechazar `EMAIL_MODE=console` y URLs públicas no HTTPS cuando `ENVIRONMENT=production`.
- Mantener un template de restablecimiento separado de la invitación, con enlace
  tokenizado, vigencia visible y sin contraseñas.
- Probar que un fallo de entrega revierte la nueva emisión sin invalidar el
  enlace anterior.
