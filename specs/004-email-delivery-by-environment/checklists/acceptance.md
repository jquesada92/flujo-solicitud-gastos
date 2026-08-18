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
- [x] Docker Compose publica el frontend en `localhost:3000`.
- [x] Docker Compose sobreescribe `PUBLIC_URL` del backend a `http://localhost:3000` por defecto.
- [x] El `.env` raíz permite personalizar `LOCAL_PUBLIC_URL` sin tocar código.
- [x] La documentación distingue Docker Compose `3000` de Vite directo `5173`.

## Producción

- [x] Producción continúa usando `EMAIL_MODE=brevo`.
- [x] Las variables Brevo viven en el backend/Render, no en Vercel/frontend.
- [x] `BREVO_API_KEY` es obligatoria cuando `EMAIL_MODE=brevo`.
- [x] `EMAIL_FROM` productivo se documenta como remitente verificado.
- [x] `PUBLIC_URL` productiva corresponde al frontend Vercel.

## Seguridad

- [x] Ninguna contraseña SMTP/App Password/API key se versiona.
- [x] El script diagnóstico no imprime secretos.
- [x] La contraseña normal de Google no se documenta como credencial recomendada para SMTP local.
- [x] `LOCAL_PUBLIC_URL` no contiene secretos ni sustituye variables privadas del backend.

## Diagnóstico

- [x] `python -m scripts.test_email --to <correo>` permite probar entrega sin crear una solicitud.
- [x] El comando equivalente dentro de Docker Compose está documentado.
- [x] CI importa `scripts.test_email` dentro de la imagen backend construida.
- [x] `ERR_CONNECTION_REFUSED` en un link local se documenta como posible desalineación `PUBLIC_URL`/puerto frontend.
- [ ] Validar manualmente con las credenciales locales reales que Google acepta el correo de prueba.
- [ ] Validar una solicitud SIMPLE que llegue a un usuario con `requests:approve` y abra `http://localhost:3000/email-action/...` bajo Compose.
- [ ] Validar una MULTI_QUOTE que entregue la invitación de votación y abra `http://localhost:3000/email-action/...` bajo Compose.

## Documentación

- [x] Constitución vigente revisada; este fix operativo no cambia reglas de gobierno y permanece en 2.3.3.
- [x] Feature spec actualizada.
- [x] Plan técnico actualizado.
- [x] Criterios de aceptación actualizados.
- [x] README revisado para la configuración local de correo.
- [x] Prompt maestro mantiene el contrato por ambiente.
- [x] `docs/EMAIL_CONFIGURATION.md` actualizado e indexado.
- [x] HISTORY/CHANGELOG registran el incidente/configuración cuando aplica.
- [x] `backend/.env.example` refleja SMTP Google local y Brevo producción.
- [x] `.env.example` raíz documenta el URL público de Docker Compose.
- [x] Configuración productiva/local no mezcla secretos del frontend con el backend.
- [x] Descripción del PR sincronizada con Feature 004.
