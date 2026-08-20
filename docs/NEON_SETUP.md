# Neon PostgreSQL setup — PH Torre Delta

Configuración objetivo para producción:

- Proyecto Neon: `ph_torre_delta`
- Base de datos PostgreSQL: `ph_torre_delta`
- Schema de aplicación: `flujos_de_aprobacion`
- Variable de aplicación: `DATABASE_SCHEMA=flujos_de_aprobacion`

## Creación manual con psql

Conéctate primero a la base administrativa/default del proyecto Neon con un rol propietario:

```bash
psql "$NEON_ADMIN_DATABASE_URL"
```

Crea la base:

```sql
CREATE DATABASE ph_torre_delta;
```

Luego conéctate a la nueva base:

```bash
psql "$NEON_PH_TORRE_DELTA_DATABASE_URL"
```

Crea el schema y configura el `search_path`:

```sql
CREATE SCHEMA IF NOT EXISTS flujos_de_aprobacion;
ALTER DATABASE ph_torre_delta SET search_path TO flujos_de_aprobacion, public;
```

Si se desea fijar también el `search_path` para el rol de la aplicación:

```sql
ALTER ROLE neondb_owner IN DATABASE ph_torre_delta
SET search_path TO flujos_de_aprobacion, public;
```

## Variables de producción

No guardar la cadena real de Neon en Git. Configurarla como secreto/variable del runtime:

```dotenv
DATABASE_URL=postgresql://<usuario>:<password>@<host>/ph_torre_delta?sslmode=require
DATABASE_SCHEMA=flujos_de_aprobacion
```

La aplicación añade el schema configurado al `search_path` de SQLAlchemy y Alembic. En desarrollo local, `DATABASE_SCHEMA` mantiene `public` como valor por defecto.

## Migraciones

Desde `backend/`, con las variables de producción cargadas:

```bash
alembic upgrade head
```

Para verificar dónde quedaron las tablas:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'flujos_de_aprobacion'
ORDER BY table_name;
```
