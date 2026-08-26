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

## Runtime pooled y operaciones directas

El runtime del backend es compatible con el endpoint pooled de Neon porque sus consultas califican el schema explícitamente. El hostname pooled contiene `-pooler` y la cadena debe copiarse desde Neon con sus parámetros TLS; nunca se reconstruye a mano ni se registra en logs.

No añadir a SQLAlchemy/Alembic:

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

Neon recomienda una conexión directa, no pooled, para migraciones ORM y `pg_dump`. Las operaciones administrativas pueden depender de estado de sesión que PgBouncer en modo transacción no conserva. Ver [Connection pooling · Neon Docs](https://neon.com/docs/connect/connection-pooling).

### Limitación vigente

El código actual solo admite una `DATABASE_URL`: `backend/alembic/env.py` y el runtime leen la misma variable, y `backend/scripts/start.sh` migra antes de iniciar la aplicación. Todavía no existe una `MIGRATION_DATABASE_URL` separada.

Por tanto:

- usar una URL directa para el servicio cumple la ruta segura de migración, aunque renuncia al pooler en runtime;
- usar una URL pooled beneficia el runtime, pero también hace que el arranque ejecute Alembic sobre el pooler y debe considerarse una limitación conocida;
- no inventar ni documentar una segunda variable hasta que el código la implemente y pruebe.

Antes de producción se debe ensayar el head completo sobre una rama Neon o un PostgreSQL aislado. `pg_dump`, una inspección administrativa y cualquier restauración usan la URL directa. Ninguna de estas operaciones se ejecuta contra producción por iniciativa de una IA.

## Alembic

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
→ 20260825_0012_keep_quotation_voting_open
```

`alembic heads` debe devolver `20260825_0012`.

`0004` permite asignaciones de Roles globales (sin Grupo) y conserva el guard de máximo un Rol del mismo Grupo por Usuario.

`0009` agrega `group_permissions` para herencia aditiva y deja la tabla vacía al migrar, sin modificar `role_permissions`.

`0010` agrega `users.password_reset_version` con default cero para invalidar
enlaces de restablecimiento anteriores sin almacenar tokens.
`0011` agrega `roles.max_users` nullable con check positivo y actualiza las
instantáneas temporales de Rol; los Roles existentes quedan ilimitados.

`0012` normaliza a `QUOTATION_VOTING` las solicitudes `MULTI_QUOTE` que estaban
en `APPROVED` sin factura, para conservar abierta la ronda hasta el cierre real.

La baseline exige el schema de aplicación vacío en una instalación nueva. Una vez desplegada, no se reescribe; se agregan revisiones.

## Render

`render.yaml` declara `DATABASE_SCHEMA=administracion`. `DATABASE_URL` es secreto/configuración del servicio.

El inicio canónico es el `CMD` de la imagen, `backend/scripts/start.sh`:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app --host 0.0.0.0 --port ${PORT:-8000}
```

No reemplazarlo en Render por el comando Uvicorn abreviado: debe escuchar en todas las interfaces y respetar `PORT`.

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

Esa prueba real se ejecuta exclusivamente en local, staging o una rama Neon desechable. En producción la verificación posterior al despliegue es no mutante. `alembic heads` comprueba el grafo disponible; `alembic current` comprueba la revisión aplicada, pero ninguno demuestra por sí solo que todos los flujos runtime funcionen.

## Restauración

Antes de una migración productiva confirma la ventana de restauración de Neon y conserva el identificador del deployment. Una restauración o un cambio de rama puede alterar el estado al que apunta la conexión y requiere autorización humana. No se ejecuta automáticamente `alembic downgrade`; se prefiere una corrección forward-compatible o un plan de restauración coordinado y probado.
