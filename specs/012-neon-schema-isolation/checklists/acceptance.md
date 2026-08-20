# Checklist de aceptación — Feature 012

## Topología

- [x] Base objetivo documentada como `ph_torre_delta`.
- [x] Schema objetivo documentado como `administracion`.
- [x] `DATABASE_SCHEMA=administracion` agregado a los ENV de ejemplo del backend.
- [x] DEV y PROD conservan `DATABASE_URL` separadas.

## Settings / SQLAlchemy

- [x] `Settings` expone `database_schema`.
- [x] Default: `administracion`.
- [x] Identificador inválido produce error.
- [x] `public`, `information_schema` y `pg_*` se rechazan.
- [x] SQLAlchemy usa metadata con schema en PostgreSQL.
- [x] SQLAlchemy fuerza `search_path` al schema configurado.
- [x] SQLite permanece schema-less para unit tests.

## Alembic

- [x] `version_table_schema` usa `DATABASE_SCHEMA`.
- [x] `env.py` crea el schema si no existe.
- [x] Autogenerate/discovery queda restringido al schema de aplicación.
- [x] Revisiones `0000→0008` eliminadas.
- [x] SQL legacy de migración eliminado.
- [x] Existe una sola revisión: `20260820_0001_initial_schema.py`.
- [x] `down_revision = None`.

## Baseline limpia

- [x] Crea el modelo actual desde cero.
- [x] `expense_area` se crea directamente.
- [x] `expense_category` se crea directamente.
- [x] No contiene renombre desde `expense_type` / `expense_subcategory`.
- [x] No contiene backfills de datos históricos.
- [x] No importa usuarios/asignaciones de bases anteriores.
- [x] No usa `alembic stamp`.
- [x] Aborta si encuentra tablas previas en el schema destino.

## IAM inicial

- [x] Siembra `requests:read`.
- [x] Siembra `requests:create`.
- [x] Siembra `requests:approve`.
- [x] Siembra `areas:manage`.
- [x] Siembra `config:read`.
- [x] Siembra `config:manage`.
- [x] Conserva `requests:close` solo como registro inactivo.
- [x] Siembra `system-administrator`.
- [x] Siembra `area-manager`.
- [x] Siembra `configuration-viewer`.

## Auditoría

- [x] La baseline conserva guards append-only de PostgreSQL.
- [x] Función y triggers se crean dentro del schema de aplicación.

## Pruebas

- [x] La prueba de Área/Categoría ya no exige la migración `0008`.
- [x] Existe `test_database_schema_contract.py`.
- [ ] Ejecutar `python -m unittest discover -s tests -v` en checkout local/CI.
- [ ] Ejecutar `alembic heads` y confirmar `20260820_0001`.
- [ ] Ejecutar baseline contra DEV vacío.
- [ ] Confirmar todas las tablas en `administracion`.
- [ ] Confirmar ausencia de tablas de aplicación en `public`.
- [ ] Ejecutar `python -m scripts.bootstrap_admin` en DEV.
- [ ] Validar login/flujo básico en DEV.
- [ ] Repetir baseline en PROD nuevo después de validar DEV.

## Regla de cierre

Una vez que `20260820_0001` se despliegue en un ambiente persistente, la baseline queda congelada. Todo cambio posterior debe crear una revisión Alembic nueva.
