# Aceptación — Spec 018

- [x] `NULL` conserva Roles ilimitados y cero/negativos se rechazan.
- [x] `RoleOut` informa límite y ocupación activa.
- [x] El primer Usuario activo ocupa cupo y el siguiente recibe 409 si está lleno.
- [x] Un Usuario inactivo conserva el Rol sin consumir cupo.
- [x] Reactivar contra un Rol lleno recibe 409 y hace rollback.
- [x] Reducir el máximo debajo de la ocupación recibe 409 y conserva el valor.
- [x] La ruta compatible de asignación respeta el mismo límite.
- [x] Las filas de Rol se bloquean en orden estable antes de contar.
- [x] La UI edita el límite solo con Guardar cambios y muestra ocupación/error.
- [x] El selector marca como sin cupo un Rol lleno no asignado al Usuario.
- [x] `20260825_0011` forma parte de la cadena Alembic lineal y conserva historial temporal.
- [x] Validación visual local completada en 320, 390, 440, 640, 1024 y 1180 px.
- [x] Suite completa, build, audit y Compose/PostgreSQL local verdes.
