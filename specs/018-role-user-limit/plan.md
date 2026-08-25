# Plan — Spec 018

1. Agregar `Role.max_users`, schemas y migración forward-only `0011`.
2. Exponer `max_users` y `assigned_user_count` en `RoleOut`.
3. Bloquear Roles y validar cupo en asignación canónica, ruta compatible y
   reactivación; impedir máximos menores que la ocupación.
4. Incorporar controles staged, resumen de capacidad y opciones llenas en UI.
5. Cubrir API, migración, frontend, PostgreSQL local y anchos responsive.
6. Sincronizar Constitución, README, prompt, contrato, IAM y guías operativas.
