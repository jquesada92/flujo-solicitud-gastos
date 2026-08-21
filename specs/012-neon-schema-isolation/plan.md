# Plan 012 — Persistencia Neon

1. Mantener `DATABASE_URL` y `DATABASE_SCHEMA` en Settings/entorno.
2. No añadir startup `search_path` al endpoint pooled.
3. Mantener tablas/constraints/version table schema-qualified.
4. Mantener `render.yaml` con `DATABASE_SCHEMA=administracion`.
5. Validar `alembic heads` y topología de revisiones.
6. En despliegue, verificar `information_schema.tables` bajo `administracion`.
7. Crear toda evolución física como nueva migración.
