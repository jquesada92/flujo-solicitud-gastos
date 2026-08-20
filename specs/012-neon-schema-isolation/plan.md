# Plan de implementación — Feature 012

**Feature:** Aislamiento de schema Neon por ambiente  
**Branch:** `feature/neon-ph-torre-delta-schema`  
**Constitución:** 2.10.0

## Resultado objetivo

DEV y PROD usan:

```text
Neon project: ph_torre_delta
Database: ph_torre_delta
Schema: ph_torre_delta
```

con:

```text
main → PROD
dev  → DEV
```

Las tablas se crean desde cero con Alembic. No se migran datos ni tablas desde schemas anteriores.

## Fase 1 — Configuración central

### Backend Settings

Agregar una configuración única:

```text
DATABASE_SCHEMA=ph_torre_delta
```

Ubicación esperada:

```text
backend/app/core/config.py
backend/.env.example
backend/.env.preview.example
.env.example
.env.preview.example
```

Requisitos:

- valor por defecto seguro/documentado cuando corresponda;
- no duplicar el literal en módulos de negocio;
- `DATABASE_URL` continúa siendo secreto por ambiente;
- `DATABASE_SCHEMA` no es secreto.

## Fase 2 — SQLAlchemy

Actualizar `backend/app/core/database.py` para que el schema de aplicación sea parte del contrato de persistencia.

La implementación debe garantizar:

- metadata ORM asociada al schema configurado;
- sesiones runtime resolviendo `ph_torre_delta`;
- relaciones y FKs compatibles;
- ninguna dependencia de `public` como fallback;
- conexión Neon compatible con `postgresql+psycopg`.

Se debe evitar prefijar manualmente el schema en cada query.

## Fase 3 — Alembic

Actualizar `backend/alembic/env.py` para:

1. leer `DATABASE_SCHEMA` desde Settings;
2. garantizar que el schema exista antes de ejecutar DDL;
3. establecer el schema efectivo de la conexión de migración;
4. configurar `version_table_schema` para que `alembic_version` viva en `ph_torre_delta`;
5. habilitar comparación de schema cuando corresponda;
6. mantener `compare_type=True`;
7. soportar modo online y offline de forma coherente.

### Cadena existente

La cadena actual permanece:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

No se crea una migración de traslado desde `flujos_de_aprobacion`.

La instalación limpia debe ejecutar la cadena completa sobre el nuevo schema.

Si alguna revisión contiene SQL o nombres de objetos que dependan explícitamente de `public`, debe corregirse para ser compatible con el schema configurado sin alterar la semántica funcional de la revisión.

## Fase 4 — Protección contra schemas legacy

Auditar código y migraciones buscando:

```text
public.
flujos_de_aprobacion
search_path
schema=
version_table_schema
```

Objetivo:

- no usar `flujos_de_aprobacion` como fallback;
- no crear tablas de negocio bajo `public`;
- no leer `alembic_version` legacy por accidente.

Los objetos legacy existentes no se borran dentro de esta feature.

## Fase 5 — Inicialización DEV

Target:

```text
Neon branch: dev
Database: ph_torre_delta
Schema: ph_torre_delta
```

Procedimiento:

1. confirmar conexión al branch `dev`;
2. confirmar que `ph_torre_delta` existe;
3. confirmar que el schema objetivo no contiene tablas de aplicación que deban preservarse;
4. ejecutar `alembic upgrade head`;
5. ejecutar `python -m scripts.bootstrap_admin`;
6. validar estructura y revisión Alembic;
7. ejecutar pruebas backend.

No copiar datos desde `flujos_de_aprobacion`.

## Fase 6 — Validación PROD

Target:

```text
Neon branch: main
Database: ph_torre_delta
Schema: ph_torre_delta
```

Antes de inicializar:

- validar la misma revisión de código probada en DEV;
- confirmar que el schema objetivo puede tratarse como instalación limpia;
- confirmar que no existe información que el usuario haya solicitado preservar dentro del schema objetivo.

Luego ejecutar la misma cadena de inicialización.

## Fase 7 — Gates técnicos

### Alembic

```text
cd backend
alembic heads
alembic current
alembic upgrade head
```

Debe existir una sola cabeza y `current == head` en el schema objetivo.

### SQL de validación

Validar conceptualmente:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('ph_torre_delta', 'public', 'flujos_de_aprobacion')
ORDER BY table_schema, table_name;
```

Esperado:

- tablas de aplicación vigentes bajo `ph_torre_delta`;
- `alembic_version` bajo `ph_torre_delta`;
- ninguna tabla de aplicación nueva creada por Feature 012 bajo `public`;
- objetos legacy, si existen, permanecen aislados.

### Backend

```text
python -m unittest discover -s tests -v
```

Agregar pruebas específicas para configuración de schema si son necesarias.

### Frontend

```text
cd frontend
npm ci
npm run build
```

Aunque la feature sea de persistencia, el build sigue siendo gate de integración.

## Fase 8 — Documentación

Actualizar:

```text
.specify/memory/constitution.md
README.md
PROMPT_RECONSTRUCCION.md
specs/012-neon-schema-isolation/*
```

Los documentos deben declarar explícitamente:

```text
main = PROD
dev = DEV
database = ph_torre_delta
schema = ph_torre_delta
fresh create; no data migration
```

## Riesgos y mitigaciones

### Riesgo: Alembic detecta una revisión legacy

Mitigación: `alembic_version` debe estar aislada dentro de `ph_torre_delta`; no usar `stamp` para reutilizar estado ajeno.

### Riesgo: ORM cae en `public`

Mitigación: metadata/configuración central + schema efectivo de conexión + prueba con schemas coexistentes.

### Riesgo: migraciones con SQL hardcodeado

Mitigación: auditoría de todas las revisiones y eliminación de dependencias explícitas de schemas legacy.

### Riesgo: DEV y PROD divergen

Mitigación: ambos parten de la misma cadena Alembic y la misma revisión de código; solo cambia `DATABASE_URL`/branch.

## No hacer

- no copiar tablas;
- no mover tablas;
- no renombrar schemas legacy;
- no hacer `alembic stamp` para saltar revisiones;
- no usar `public` como schema de aplicación;
- no ejecutar DDL manual distinto entre DEV y PROD para obtener la estructura final.
