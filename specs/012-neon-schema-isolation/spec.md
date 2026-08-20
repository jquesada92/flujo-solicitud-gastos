# Especificación técnica — Aislamiento de schema Neon por ambiente

**Feature:** 012  
**Constitución:** 2.10.0

## Objetivo

Establecer una persistencia limpia y reproducible en Neon para DEV y PROD usando una única base de datos lógica y un único schema de aplicación:

```text
Proyecto Neon: ph_torre_delta
Base de datos: ph_torre_delta
Schema aplicación: ph_torre_delta
```

La aplicación debe crear sus tablas desde cero dentro de `ph_torre_delta`. Esta feature **no migra, mueve, copia ni renombra** tablas existentes desde `public`, `flujos_de_aprobacion` u otro schema previo.

## Topología de ambientes

```text
Neon project: ph_torre_delta
├─ main  → PROD
│  └─ database: ph_torre_delta
│     └─ schema: ph_torre_delta
└─ dev   → DEV
   └─ database: ph_torre_delta
      └─ schema: ph_torre_delta
```

DEV y PROD deben compartir definición de esquema y migraciones, pero nunca depender de datos entre sí.

## F-012-01 — Schema canónico de aplicación

Toda tabla, secuencia, índice, constraint y objeto Alembic creado por la aplicación debe pertenecer al schema:

```text
ph_torre_delta
```

Esto incluye explícitamente `alembic_version`.

No se crearán tablas de negocio nuevas en:

```text
public
flujos_de_aprobacion
```

Los schemas legacy pueden existir temporalmente en Neon, pero no son fuente de verdad ni objetivo de creación.

## F-012-02 — Creación limpia, no migración de datos

La instalación de DEV y PROD se considera una instalación limpia del modelo vigente.

Está prohibido para esta feature:

- mover tablas existentes entre schemas;
- copiar registros legacy al nuevo schema;
- renombrar `flujos_de_aprobacion` a `ph_torre_delta`;
- usar `CREATE TABLE ... AS` para clonar estructuras o datos existentes;
- usar `alembic stamp` para fingir que el nuevo schema ya contiene las revisiones.

El mecanismo esperado es ejecutar la cadena Alembic completa contra `ph_torre_delta` vacío.

## F-012-03 — Configuración centralizada

El nombre del schema debe resolverse desde Settings mediante una única configuración de infraestructura:

```text
DATABASE_SCHEMA=ph_torre_delta
```

No debe repetirse el literal del schema de forma dispersa en routers, servicios o modelos.

DEV y PROD usan el mismo valor de `DATABASE_SCHEMA`; cambia la conexión/branch de Neon, no el contrato lógico del schema.

## F-012-04 — SQLAlchemy debe resolver el schema correcto

La configuración de SQLAlchemy debe garantizar que las operaciones ORM de runtime apunten a `ph_torre_delta` aunque exista `public` u otro schema en la misma base.

La solución debe estar centralizada en `app/core/database.py` y ser compatible con las relaciones/FKs actuales.

No se permite depender de que cada query recuerde prefijar manualmente el schema.

## F-012-05 — Alembic debe aislar su versionado

Alembic debe:

1. crear/verificar `ph_torre_delta` antes de crear objetos de aplicación;
2. ejecutar las revisiones con `ph_torre_delta` como schema efectivo;
3. guardar `alembic_version` dentro de `ph_torre_delta`;
4. autogenerar cambios comparando el schema de aplicación y no `public`;
5. mantener una única cabeza válida.

El estado Alembic de un schema legacy no debe hacer que el nuevo schema se considere migrado.

## F-012-06 — DEV y PROD reproducibles

Una base `ph_torre_delta` con el schema objetivo vacío debe poder llegar al estado vigente mediante:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
```

El resultado estructural debe ser equivalente en las branches Neon `dev` y `main`.

Los datos de bootstrap pueden diferir por política de ambiente, pero no la estructura física de tablas.

## F-012-07 — Protección contra creación accidental en `public`

La validación de despliegue debe fallar si se detecta una tabla de aplicación nueva fuera de `ph_torre_delta`.

Como mínimo se validará con `information_schema` que:

- todas las tablas esperadas están bajo `ph_torre_delta`;
- `ph_torre_delta.alembic_version` existe;
- no aparecieron tablas de aplicación bajo `public`;
- la revisión Alembic es `head`.

## F-012-08 — Schemas legacy

`flujos_de_aprobacion` y cualquier tabla histórica fuera del schema canónico pueden permanecer temporalmente mientras se confirma la instalación limpia.

No deben ser consultados por la aplicación nueva ni usados como fallback silencioso.

Su eliminación futura será una operación separada, explícita y destructiva; no forma parte de Feature 012.

## F-012-09 — Variables y secretos por ambiente

Cada deployment debe usar su propia `DATABASE_URL` correspondiente a la branch Neon correcta:

```text
DEV  → Neon branch dev
PROD → Neon branch main
```

No se guardan connection strings ni credenciales reales en Git.

`DATABASE_SCHEMA=ph_torre_delta` sí puede documentarse porque no es secreto.

## F-012-10 — Documentación como contrato

La feature no está completa hasta sincronizar como mínimo:

```text
.specify/memory/constitution.md
specs/012-neon-schema-isolation/spec.md
specs/012-neon-schema-isolation/plan.md
specs/012-neon-schema-isolation/checklists/acceptance.md
README.md
PROMPT_RECONSTRUCCION.md
```

## Escenarios de aceptación

### Escenario A — DEV limpio

```text
Dado Neon branch dev
Y database ph_torre_delta
Y schema ph_torre_delta vacío
Cuando se ejecuta alembic upgrade head
Entonces todas las tablas de aplicación se crean bajo ph_torre_delta
Y ph_torre_delta.alembic_version apunta a head
Y no se copian datos desde schemas legacy
```

### Escenario B — PROD limpio

```text
Dado Neon branch main
Y database ph_torre_delta
Y schema ph_torre_delta vacío
Cuando se ejecuta la misma cadena Alembic
Entonces la estructura resultante equivale a DEV
Y ninguna tabla de aplicación se crea en public
```

### Escenario C — Existe schema legacy

```text
Dado que flujos_de_aprobacion contiene objetos previos
Cuando se inicializa ph_torre_delta
Entonces Alembic no reutiliza ni mueve esos objetos
Y la aplicación opera exclusivamente sobre ph_torre_delta
```

### Escenario D — Runtime ORM

```text
Dado que public y ph_torre_delta existen simultáneamente
Cuando FastAPI consulta o muta entidades persistidas
Entonces SQLAlchemy resuelve las tablas de ph_torre_delta
Y nunca cae silenciosamente en public o flujos_de_aprobacion
```

## Fuera de alcance

- migración de datos legacy;
- eliminación del schema `flujos_de_aprobacion`;
- eliminación de `public`;
- cambio del modelo funcional de gastos/IAM;
- cambio de proveedor de base de datos.
