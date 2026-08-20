# Checklist de aceptación — Feature 012

## Topología Neon

- [ ] El proyecto Neon usado es `ph_torre_delta`.
- [ ] `main` está reservado para PROD.
- [ ] `dev` está reservado para DEV.
- [ ] Ambos ambientes usan la base `ph_torre_delta`.
- [ ] Ambos ambientes usan el schema `ph_torre_delta`.

## Creación limpia

- [ ] No se movieron tablas desde `flujos_de_aprobacion`.
- [ ] No se copiaron datos desde schemas legacy.
- [ ] No se renombró un schema legacy para simular la nueva estructura.
- [ ] No se utilizó `alembic stamp` para saltar la creación real del schema.
- [ ] La cadena Alembic completa puede ejecutarse sobre `ph_torre_delta` vacío.

## Configuración

- [ ] Existe una configuración central `DATABASE_SCHEMA`.
- [ ] Su valor esperado es `ph_torre_delta`.
- [ ] El literal del schema no está disperso por routers o servicios.
- [ ] DEV utiliza la `DATABASE_URL` del branch `dev`.
- [ ] PROD utiliza la `DATABASE_URL` del branch `main`.
- [ ] No hay credenciales reales versionadas.

## SQLAlchemy

- [ ] El ORM resuelve tablas del schema `ph_torre_delta`.
- [ ] La aplicación funciona aunque `public` exista simultáneamente.
- [ ] La aplicación no cae silenciosamente en `flujos_de_aprobacion`.
- [ ] Relaciones y foreign keys funcionan con el schema configurado.

## Alembic

- [ ] `ph_torre_delta.alembic_version` existe.
- [ ] `alembic current` reporta la revisión esperada.
- [ ] `alembic heads` reporta una única cabeza.
- [ ] `alembic upgrade head` funciona desde un schema objetivo vacío.
- [ ] Alembic no reutiliza el `alembic_version` de un schema legacy.
- [ ] Autogenerate compara el schema de aplicación correcto.

## Objetos físicos

- [ ] Todas las tablas de aplicación están bajo `ph_torre_delta`.
- [ ] Los índices de aplicación pertenecen a tablas del schema correcto.
- [ ] Las secuencias de aplicación pertenecen al schema correcto.
- [ ] Las constraints/FKs apuntan a objetos del schema correcto.
- [ ] No se creó ninguna tabla de aplicación nueva bajo `public`.

## DEV

- [ ] DEV fue inicializado desde cero con Alembic.
- [ ] `bootstrap_admin` funciona después de `alembic upgrade head`.
- [ ] Las pruebas backend pasan contra DEV/configuración equivalente.

## PROD

- [ ] La misma revisión de código validada en DEV se usa para PROD.
- [ ] PROD fue inicializado desde cero en `ph_torre_delta`.
- [ ] La estructura física de PROD equivale a DEV.
- [ ] No se reutilizaron datos legacy durante la inicialización.

## Gates

- [ ] `alembic heads` pasa.
- [ ] `alembic current` pasa.
- [ ] `python -m unittest discover -s tests -v` pasa.
- [ ] `npm run build` pasa.
- [ ] Consulta de `information_schema` confirma aislamiento de schema.

## Documentación

- [ ] Constitución actualizada a 2.10.0.
- [ ] `README.md` refleja Neon DEV/PROD y schema canónico.
- [ ] `PROMPT_RECONSTRUCCION.md` prohíbe crear en `public` o migrar desde schemas legacy.
- [ ] Feature 012 tiene spec, plan y checklist sincronizados.
