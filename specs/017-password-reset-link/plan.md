# Plan 017 — Enlace de restablecimiento de contraseña

## Backend

- Mantener la emisión administrativa compatible en
  `POST /api/users/{user_id}/regenerate-password`, protegida por
  `config:manage` y `system_accounts`.
- Rechazar destinatarios inactivos o técnicos.
- Persistir `users.password_reset_version` mediante una nueva migración sobre el
  head vigente.
- Generar tokens de propósito exclusivo con expiración configurable, uso único
  e invalidación de emisiones anteriores sin modificar contraseña ni sesiones.
- Invalidar enlaces al cambiar correo o estado `active` del Usuario.
- Implementar el consumo público en `POST /api/auth/reset-password`.
- Aplicar Argon2, limpiar `must_change_password`, incrementar
  `session_version` y `password_reset_version` al consumir.
- Hacer rollback si el proveedor reporta fallo antes del commit y documentar el
  caso no atómico de correo aceptado cuyo commit posterior falla; evaluar outbox.
- Intentar después del commit una notificación best-effort de contraseña
  cambiada, sin token/contraseña y sin revertir el cambio ante fallo.
- Auditar sin token, contraseña o hash.
- Aplicar la política sensible autenticada a la emisión y una cuota pública
  local de 5 intentos por 15 minutos por IP/proceso al consumo, con limpieza TTL.

## Correo

- Crear un template específico de restablecimiento, separado de la invitación.
- Construir el enlace con `PUBLIC_URL` y fragmento `#token=...`, y explicar su vigencia.
- No incluir contraseñas en texto ni HTML.
- Probar fallo reportado antes del commit, commit fallido después de aceptación y
  notificación post-commit fallida con mocks o modo `console` local.
- Tratar como sensible el log local de `console`; ningún log ordinario registra el token.

## Frontend

- Agregar la acción confirmada a la ficha de Usuario activo no técnico.
- Mantenerla separada del estado staged y de **Guardar cambios**.
- Evitar doble envío mientras la operación está pendiente y mostrar resultado
  sin revelar el token.
- Renderizar `/reset-password#token=...` antes del Login, capturar el fragmento
  en memoria y retirarlo de la URL al cargar, sin tratarla como ruta privada ni
  iniciar sesión al completar.
- Conservar foco, mensajes y layout utilizable de 320 a 1180 px.

## Configuración y pruebas

- Definir `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30` en Settings y ejemplos.
- Cubrir autorización, destino protegido, expiración, reemplazo, reutilización,
  invalidación por correo/estado, rollback previo al commit, fallo de commit tras
  aceptación, auditoría, Argon2, revocación de sesiones, notificación
  best-effort, ausencia de auto-login y contenido seguro del correo.
