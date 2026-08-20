# Plan — Feature 012: base limpia en Neon + schema `administracion`

## Resultado esperado

```text
DEV
DATABASE_URL  → Neon / database ph_torre_delta
DATABASE_SCHEMA=administracion

PROD / Render
DATABASE_URL  → Neon / database ph_torre_delta
DATABASE_SCHEMA=administracion
```

No se conserva ninguna tabla, dato o revisión física previa.

## 1. Configuración

### `backend/app/core/config.py`

Agregar:

```text
database_schema
```

con default `administracion` y validación de identificador PostgreSQL simple.

Rechazar:

```text
public
pg_catalog
information_schema
pg_*
```

### ENV

Alinear:

```text
backend/.env.example
backend/.env.preview.example
.env.example
.env.preview.example
```

El nombre de la base local también se normaliza a `ph_torre_delta` / `ph_torre_delta_preview`.

## 2. SQLAlchemy

### `backend/app/core/database.py`

Para PostgreSQL:

- `MetaData(schema=DATABASE_SCHEMA)`;
- `search_path` de la conexión limitado al schema configurado.

Para SQLite de tests:

- metadata sin schema;
- no enviar opciones PostgreSQL.

Objetivo: las consultas ORM en PostgreSQL quedan físicamente dirigidas a `administracion` y un SQL no cualificado tampoco cae en `public`.

## 3. Alembic

### `backend/alembic/env.py`

- crear el schema si todavía no existe;
- establecer `search_path`;
- configurar `version_table_schema`;
- limitar autogenerate/discovery al schema de aplicación;
- mantener SQLite sin schema para tests.

## 4. Reinicio de historia

Eliminar:

```text
20260817_0000_application_baseline.py
20260817_0001_iam_foundation.py
20260817_0002_system_accounts.py
20260817_0003_backfill_multi_quote_request_type.py
20260818_0004_position_role_inheritance.py
20260818_0005_closure_delegation.py
20260818_0006_area_management_permission.py
20260819_0007_configuration_read_access.py
20260819_0008_expense_area_category_columns.py
backend/migrations/20260817_remove_property_domain.sql
```

Crear:

```text
backend/alembic/versions/20260820_0001_initial_schema.py
```

## 5. Baseline inicial

La revisión debe contener un snapshot congelado del modelo físico actual y crear desde cero:

```text
users / auditoría
expenses / quotations / approvals
clasificación Área + Categoría
IAM configurable
system_accounts
closure delegation
```

La baseline debe crear directamente:

```text
expenses.expense_area
expenses.expense_category
```

No crear primero nombres viejos para renombrarlos después.

## 6. IAM mínimo

Semillas de instalación:

### Permisos activos

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

### Registro inactivo

```text
requests:close
```

### Roles

```text
system-administrator
area-manager
configuration-viewer
```

No importar configuración organizacional de una base previa.

## 7. Auditoría

Mantener dentro del schema `administracion` la función PostgreSQL que rechaza UPDATE/DELETE y sus triggers para las tablas append-only.

## 8. Protección contra reutilización accidental

Antes de crear el snapshot, la baseline inspecciona el schema objetivo.

Si existen tablas distintas de `alembic_version`, aborta con error explícito.

Esto convierte “base limpia” en una condición técnica verificable y no solo en una instrucción documental.

## 9. Bootstrap

Después de `alembic upgrade head`:

```text
python -m scripts.bootstrap_admin
```

crea/reconcilia la cuenta técnica en la instalación nueva.

No se importan usuarios antiguos.

## 10. Tests

Actualizar pruebas que dependían de `0008`.

Agregar contrato que valide:

- default `administracion`;
- rechazo de schemas del sistema;
- única revisión `20260820_0001`;
- `version_table_schema` configurado;
- ENV examples sincronizados;
- baseline canónica sin renombres históricos.

## 11. Validación DEV

Con la base/schema vacíos:

```text
cd backend
alembic heads
# esperado: 20260820_0001

alembic upgrade head
alembic current
```

Verificar en PostgreSQL:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'administracion'
ORDER BY table_name;
```

Y ausencia de tablas de app en `public`:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

## 12. Validación PROD

Solo después de validar DEV, ejecutar el mismo `alembic upgrade head` contra la nueva `DATABASE_URL` de Render/PROD.

No ejecutar este baseline contra una base que se quiera conservar.

## 13. Evolución posterior

Una vez desplegado `20260820_0001`, queda congelado. Cualquier cambio de estructura posterior se hace mediante nuevas revisiones Alembic incrementales.
