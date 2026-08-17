# Criterios de aceptación — Entrega de correo por ambiente

## Local / desarrollo

- [x] El backend soporta `EMAIL_MODE=smtp`.
- [x] Google SMTP usa `smtp.gmail.com`.
- [x] La configuración recomendada usa puerto 465 + SSL.
- [x] Se documenta 587 + STARTTLS como alternativa.
- [x] `SMTP_USER` y `SMTP_PASSWORD` son obligatorios cuando `EMAIL_MODE=smtp`.
- [x] `.env.example` no contiene credenciales reales.
- [x] `.env.example` deja claro que `SMTP_PASSWORD` es una App Password de Google.
- [x] Existe un comando diagnóstico que usa el mismo servicio de correo de la aplicación.

## Producción

- [x] Producción continúa usando `EMAIL_MODE=brevo`.
- [x] Las variables Brevo viven en el backend/Render, no en Vercel/frontend.
- [x] `BREVO_API_KEY` es obligatoria cuando `EMAIL_MODE=brevo`.
- [x] `EMAIL_FROM` productivo se documenta como remitente verificado.

## Seguridad

- [x] Ninguna contraseña SMTP/App Password/API key se versiona.
- [x] El script diagnóstico no imprime secretos.
- [x] La contraseña normal de Google no se documenta como credencial recomendada para SMTP local.

## Diagnóstico

- [x] `python -m scripts.test_email --to <correo>` permite probar entrega sin crear una solicitud.
- [x] El comando equivalente dentro de Docker Compose está documentado.
- [ ] Validar manualmente con las credenciales locales reales que Google acepta el correo de prueba.
- [ ] Validar después una solicitud SIMPLE que llegue a un usuario con `requests:approve`.
- [ ] Validar después una MULTI_QUOTE que entregue la invitación de votación.

## Documentación

- [x] Feature spec creada.
- [x] Plan técnico creado.
- [x] Criterios de aceptación creados.
- [x] `backend/.env.example` refleja SMTP Google local y Brevo producción.
- [x] Configuración productiva/local no mezcla secretos del frontend con el backend.
