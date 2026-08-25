# Plan 012 — Persistencia Neon

1. Mantener `DATABASE_URL` y `DATABASE_SCHEMA` en Settings/entorno; hasta separar migraciones, configurar una URL directa en servicios que ejecutan `start.sh`.
2. No añadir startup `search_path` al endpoint pooled.
3. Mantener tablas/constraints/version table schema-qualified.
4. Mantener `render.yaml` con `DATABASE_SCHEMA=administracion`.
5. Validar `alembic heads` y topología de revisiones.
6. Si se adopta pooling de runtime, implementar y probar primero una URL directa independiente para Alembic/operaciones administrativas.
7. En despliegue, verificar `information_schema.tables` bajo `administracion`.
8. Crear toda evolución física como nueva migración.
9. Validar `AreaCounter.__table__.fullname` en generación de identificadores.
10. Mantener `inherit_schema=True` en los Enum ORM.
11. Ejecutar un escenario persistente Docker que inserte solicitud y aprobación.
12. Verificar que `0010` agrega `password_reset_version` con default cero tanto
    al migrar datos existentes como en una instalación nueva.
