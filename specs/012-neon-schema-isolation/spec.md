# Spec 012 — Neon y aislamiento de schema

**Estado:** Implementada  
**Constitución:** 2.18.0

## Objetivo

Ejecutar la aplicación en PostgreSQL/Neon dentro de un schema explícito. El runtime es compatible con endpoint pooled; migraciones y `pg_dump` usan conexión directa.

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
6. Mientras `start.sh` ejecute Alembic con la misma `DATABASE_URL` del runtime, el servicio usa una URL directa; una URL pooled de runtime requiere una conexión de migración separada implementada y probada.
7. SQLite de unit tests opera sin schema.
8. La baseline 0001 requiere un schema de aplicación limpio en instalación nueva.
9. Una revisión desplegada no se reescribe; se añade otra revisión.
10. Los tipos ENUM del ORM heredan el schema de metadata.
11. SQL crudo usa nombres de tabla calificados y no depende de `search_path`.
12. La aceptación incluye una escritura PostgreSQL real de contador, solicitud y aprobación.

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
→ 20260824_0009_group_permission_inheritance
→ 20260824_0010_password_reset_links
→ 20260825_0011_role_user_limit
  ├→ 20260825_0012_keep_quotation_voting_open ───────────────┐
  └→ 20260827_0012_scoped_approval_policies                  │
     → 20260828_0013_direct_expenses ────────────────────────┤
                                                             └→ 20260828_0014_merge_main_layout_heads
                                                                → 20260831_0015_audit_change_feed
                                                                → 20260831_0016_retire_legacy_audit_tables
```

`0010` agrega `users.password_reset_version` con valor inicial cero y mantiene
la evolución física como una revisión nueva sobre `0009`.
`0011` agrega el cupo opcional de Rol; las ramas `0012/0013` convergen en `0014`.
`0015` crea y rellena el feed canónico dentro del schema configurado y `0016`
retira ocho tablas redundantes sin `CASCADE`. `20260831_0016` es el único head y
su downgrade es irreversible; recuperar exige respaldo e imagen anteriores.

## Render

El proceso de arranque ejecuta `alembic upgrade head`, luego `bootstrap_admin` y finalmente Uvicorn.
