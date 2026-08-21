# Plan 010 — Notificaciones IAM

- reutilizar `email_service.py`;
- generar el resumen después de aplicar asignaciones vigentes;
- mostrar Cargo opcional y permisos por nombre/código;
- no incluir contraseña en actualizaciones posteriores;
- mantener semántica de rollback definida en `iam_users.py` ante fallos de entrega obligatoria;
- probar creación, cambio real, mismo Cargo y fallo de proveedor.
