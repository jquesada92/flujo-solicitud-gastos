# Aceptación 002

- [x] Permisos efectivos se resuelven desde IAM persistido como baseline + Permisos propios de Rol + herencia de Grupo.
- [x] un Rol agrupado aplica la unión aditiva `RolePermission ∪ GroupPermission`, sin `DENY`.
- [x] `GroupMember` aislado no concede Permisos.
- [x] editar o desvincular un Grupo conserva los `RolePermission` del Rol.
- [x] `requests:read` es baseline de usuario activo.
- [x] `config:manage` no es efectivo para usuario ordinario.
- [x] `config:read` permite GET/HEAD sin permitir mutaciones.
- [x] contraseña nueva usa Argon2.
- [x] sesión valida versión, expiración/inactividad y usuario activo.
- [x] 10 minutos sin actividad eliminan el token, limpian la ruta privada y muestran Login; FastAPI rechaza la sesión con 401.
- [x] volver a una pestaña suspendida después del límite no reactiva la sesión.
- [x] API tiene CORS, rate limiting y headers sensibles.
- [x] migraciones/bootstrap se ejecutan antes del servidor ASGI.
- [x] rutas que contradicen el IAM actual están bloqueadas.
