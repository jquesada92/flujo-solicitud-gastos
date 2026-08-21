# Spec 012 — Neon y aislamiento de schema

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Ejecutar toda la aplicación en PostgreSQL/Neon dentro de un schema explícito y compatible con el endpoint pooled.

## Contrato

```text
Database: ph_torre_delta
Schema:   administracion
```

## Reglas

1. `DATABASE_SCHEMA=administracion` es explícito en despliegue.
2. SQLAlchemy usa `MetaData(schema=APPLICATION_SCHEMA)`.
3. Alembic usa schema explícito y `version_table_schema`.
4. Alembic crea el schema si falta.
5. No se envía `options=-csearch_path=...` al iniciar conexiones pooled.
6. SQLite de unit tests opera sin schema.
7. La baseline 0001 requiere un schema de aplicación limpio en instalación nueva.
8. Una revisión desplegada no se reescribe; se añade otra revisión.
9. Los tipos ENUM del ORM heredan el schema de metadata.
10. SQL crudo usa nombres de tabla calificados y no depende de `search_path`.
11. La aceptación incluye una escritura PostgreSQL real de contador, solicitud y aprobación.

## Cadena vigente

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
→ 20260821_0004_allow_global_roles
→ 20260821_0005_activity_periods
→ 20260821_0006_period_snapshot_values
→ 20260821_0007_period_audit_metadata
→ 20260821_0008_normalize_period_timestamps
```

## Render

El proceso de arranque ejecuta `alembic upgrade head`, luego `bootstrap_admin` y finalmente Uvicorn.
