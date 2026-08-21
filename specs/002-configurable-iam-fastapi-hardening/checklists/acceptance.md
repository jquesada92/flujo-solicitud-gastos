# Aceptación 002

- [x] Permisos efectivos se resuelven desde IAM persistido.
- [x] `requests:read` es baseline de usuario activo.
- [x] `config:manage` no es efectivo para usuario ordinario.
- [x] `config:read` permite GET/HEAD sin permitir mutaciones.
- [x] contraseña nueva usa Argon2.
- [x] sesión valida versión, expiración/inactividad y usuario activo.
- [x] API tiene CORS, rate limiting y headers sensibles.
- [x] migraciones/bootstrap se ejecutan antes del servidor ASGI.
- [x] rutas que contradicen el IAM actual están bloqueadas.
