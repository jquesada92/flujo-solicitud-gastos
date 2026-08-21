# Neon / PostgreSQL

## Contrato

```text
Database: ph_torre_delta
Schema:   administracion
```

Variables:

```text
DATABASE_URL=<connection string Neon o PostgreSQL local>
DATABASE_SCHEMA=administracion
```

## Endpoint pooled

El backend es compatible con el endpoint pooled de Neon. No añadir a SQLAlchemy/Alembic:

```text
options=-csearch_path=...
```

El pooler puede rechazar ese startup parameter. El aislamiento se consigue con schema explícito:

- `MetaData(schema=APPLICATION_SCHEMA)` en runtime;
- `version_table_schema=database_schema` en Alembic;
- objetos/migraciones schema-qualified;
- tipos ENUM ORM con `inherit_schema=True`;
- SQL crudo con tabla calificada derivada de `Table.fullname`;
- creación de `administracion` antes de migrar.

## Alembic

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
→ 20260821_0004_allow_global_roles
```

`alembic heads` debe devolver `20260821_0004`.

`0004` permite asignaciones de Roles globales (sin Grupo) y conserva el guard de máximo un Rol del mismo Grupo por Usuario.

La baseline exige el schema de aplicación vacío en una instalación nueva. Una vez desplegada, no se reescribe; se agregan revisiones.

## Render

`render.yaml` declara `DATABASE_SCHEMA=administracion`. `DATABASE_URL` es secreto/configuración del servicio.

Inicio:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

El bootstrap asigna el Rol global técnico `system-administrator` a la cuenta protegida y registra `SystemAccount`; la política técnica sigue siendo la autoridad de privilegios.

## Verificación SQL

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'administracion'
ORDER BY table_name;
```

`alembic_version` y las tablas de aplicación deben estar en `administracion`.

También deben existir allí `userrole`, `expensestatus` y `approvalstatus`. Una prueba real debe insertar una solicitud, incrementar `category_counters` y crear una aprobación; `alembic heads` por sí solo no valida estas operaciones runtime.
