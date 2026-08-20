# Feature 012 — Base limpia en Neon y aislamiento por schema

**Constitución:** 2.10.0  
**Estado:** Implementado en rama

## Objetivo

Reiniciar el ciclo de vida físico de la base de datos sin conservar tablas, datos ni revisiones Alembic anteriores.

Contrato objetivo:

```text
Neon / Render
Database: ph_torre_delta
Schema de aplicación: administracion
Variable: DATABASE_SCHEMA=administracion
```

La aplicación crea el modelo vigente directamente dentro de `administracion`. `public` no es schema de aplicación y no existe fallback hacia schemas anteriores.

## F-012-01 — Base nueva

DEV y PROD usan conexiones que apuntan a la base PostgreSQL `ph_torre_delta` correspondiente al ambiente.

No se copian datos ni tablas desde bases anteriores.

## F-012-02 — Schema dedicado

Todas las tablas de la aplicación deben residir en el schema configurado por `DATABASE_SCHEMA`.

Para este despliegue:

```text
DATABASE_SCHEMA=administracion
```

También deben residir ahí:

- índices;
- constraints;
- secuencias asociadas;
- tipos ENUM propios;
- funciones/triggers propios de auditoría;
- `alembic_version`.

`public`, `pg_catalog`, `information_schema` y schemas `pg_*` no son valores válidos para `DATABASE_SCHEMA`.

## F-012-03 — SQLAlchemy schema-aware

En PostgreSQL, SQLAlchemy debe:

1. asociar el metadata ORM al schema configurado;
2. establecer `search_path` exclusivamente al schema de aplicación como defensa adicional.

SQLite permanece sin schema para las pruebas unitarias.

## F-012-04 — Alembic como baseline futura, no como migración histórica

Alembic se conserva para versionar cambios futuros, pero se elimina la historia anterior `0000 → 0008`.

La nueva historia comienza en:

```text
20260820_0001_initial_schema.py
```

con:

```text
down_revision = None
```

Esta revisión crea directamente el modelo vigente. No contiene:

- `ALTER ... SET SCHEMA`;
- renombres para adaptar estructuras viejas;
- `COPY`;
- backfills históricos;
- importación de permisos por nombres legacy;
- `alembic stamp`;
- preservación de datos anteriores.

## F-012-05 — Baseline exige schema vacío

La revisión inicial debe abortar si encuentra tablas de aplicación existentes en el schema destino.

Se permite únicamente la tabla `alembic_version` que Alembic puede crear antes de ejecutar la revisión.

Esto evita que una instalación nueva reutilice accidentalmente una estructura vieja.

## F-012-06 — IAM mínimo de instalación

La baseline crea los permisos vigentes:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

`requests:close` se conserva únicamente como registro legacy **inactivo**, porque la autoridad de cierre/factura es por recurso.

También crea los roles mínimos:

```text
system-administrator
area-manager
configuration-viewer
```

El bootstrap posterior crea la cuenta técnica usando `system-administrator`.

No se migran usuarios, cargos, grupos, roles organizacionales ni asignaciones anteriores.

## F-012-07 — Auditoría append-only

La baseline conserva la protección PostgreSQL contra UPDATE/DELETE de las tablas de eventos de auditoría mediante función y triggers dentro del mismo schema de aplicación.

## F-012-08 — Separación DEV / PROD

Cada ambiente tiene su propio `DATABASE_URL`.

Ambos usan:

```text
DATABASE_SCHEMA=administracion
```

La estructura física debe provenir de la misma revisión `20260820_0001` y posteriores.

## F-012-09 — Arranque

El contrato de despliegue continúa siendo:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

`alembic upgrade head` ahora significa construir una instalación limpia o aplicar exclusivamente revisiones futuras sobre la nueva baseline.

## F-012-10 — Evolución futura

Después de desplegar `20260820_0001`:

```text
20260820_0001_initial_schema
        ↓
0002_nuevo_cambio
        ↓
0003_otro_cambio
```

No se reescribe `0001` una vez que se haya desplegado en un ambiente que deba conservarse.

## Criterios de aceptación

1. `backend/alembic/versions/` contiene una sola revisión inicial.
2. No existe el SQL legacy `backend/migrations/20260817_remove_property_domain.sql`.
3. Settings reconoce `DATABASE_SCHEMA` y rechaza schemas de sistema.
4. SQLAlchemy usa el schema configurado en PostgreSQL.
5. Alembic coloca `alembic_version` en `administracion`.
6. La baseline crea `expense_area` / `expense_category` directamente, sin renombrar columnas viejas.
7. La baseline falla si encuentra tablas previas en el schema destino.
8. DEV y PROD usan `ph_torre_delta` con `DATABASE_SCHEMA=administracion`.
9. Las pruebas de contrato protegen esta arquitectura.
