# Arquitectura FastAPI

## Referencia

La arquitectura sigue los patrones recomendados por la documentación oficial de FastAPI para aplicaciones grandes, dependencias, lifespan, seguridad y testing.

## Application factory

`app/application.py` crea la aplicación y registra:

- middleware;
- routers;
- dependencias globales de routers;
- health endpoint;
- lifespan mínimo.

`app/main.py` existe únicamente como alias de compatibilidad.

## Separación de responsabilidades

```text
api/       HTTP, parámetros, dependencias, códigos de respuesta
schemas/   contratos Pydantic
services/  reglas reutilizables y lógica de negocio
models/    persistencia SQLAlchemy
core/      configuración, DB, seguridad, rate limiting
```

Los modelos de clasificación que antes vivían en `api/areas.py` están en `models/classification.py`.

## Dependencia de DB

`get_db()` usa un context manager/yield para entregar una sesión por request y cerrarla siempre.

El backend actual usa SQLAlchemy síncrono. No se mezcla con AsyncSession.

## Sync vs async

FastAPI ejecuta path operations declaradas con `def` en un threadpool. Por eso las rutas canónicas que realizan SQLAlchemy síncrono o escritura síncrona de archivos usan `def`.

No debe añadirse un `async def` que ejecute directamente:

- `Session.scalar/execute/commit` síncronos;
- `Path.write_bytes`;
- otras operaciones bloqueantes;

sin migrar la dependencia a una API async o hacer offload explícito.

## Settings

`core/config.py` utiliza `pydantic-settings` y centraliza la lectura/validación de variables de entorno.

No introducir nuevos `os.getenv()` dispersos salvo una razón técnica documentada.

Producción valida:

- secretos fuertes;
- CORS HTTPS explícito;
- credenciales necesarias según modo de correo.

## Lifespan

El lifespan solo valida/carga configuración de ciclo de vida.

No ejecuta:

- `Base.metadata.create_all()`;
- `ALTER TABLE`;
- backfills;
- seeds organizacionales;
- migraciones destructivas.

## Alembic

Alembic es la autoridad para cambios de esquema. La topología actual es deliberadamente lineal:

```text
20260817_0000 application baseline
        ↓
20260817_0001 configurable IAM
        ↓
20260817_0002 protected system accounts
```

`0000` permite que una base PostgreSQL limpia reciba el esquema base property-free y, al mismo tiempo, conserva tablas que ya existen al aplicarse sobre la base productiva actual. Su downgrade es deliberadamente no destructivo porque no puede asumir que Alembic creó las tablas preexistentes.

`tests/test_migrations.py` exige un único head y la cadena anterior. Esto detecta errores de topología, pero no reemplaza un smoke test real de `alembic upgrade head` contra PostgreSQL/Neon de preview.

El entrypoint Docker ejecuta `alembic upgrade head` y el bootstrap técnico antes de Uvicorn.

Esto permite usar el patrón incluso en planes de Render que no incluyen una etapa pre-deploy separada. En despliegues con múltiples réplicas, la migración debe moverse a una etapa única para evitar carreras.

## Portabilidad Docker Windows → Linux

Los scripts shell ejecutados por la imagen backend son artefactos Linux aunque el checkout se realice en Windows.

El repositorio aplica dos defensas:

1. `.gitattributes` fuerza `*.sh text eol=lf`.
2. `backend/Dockerfile` elimina `\r` de los scripts `.sh` durante el build antes de ejecutar `chmod +x`.

Esto evita el caso en que Docker muestra:

```text
exec /app/scripts/start.sh: no such file or directory
```

cuando el archivo existe pero el shebang quedó materializado como `/bin/sh\r` por CRLF.

En Docker Compose local, Nginx no debe iniciar únicamente porque el contenedor backend fue creado. Debe esperar a que `/api/health` pase. Así, si Alembic, bootstrap o Uvicorn fallan, el error principal queda visible en `backend` en lugar de producir primero el secundario:

```text
host not found in upstream "backend"
```

`tests/test_container_portability.py` protege estas reglas de regresión.

## Seguridad

`require_permission()` es una dependencia FastAPI que consulta permisos efectivos IAM en PostgreSQL.

No existe bypass por ADMIN.

Se pueden aplicar dependencias a routers completos, por ejemplo configuración/auditoría, evitando repetir checks en cada handler.

## Password hashing

`pwdlib.PasswordHash.recommended()` genera Argon2.

`verify_password_and_upgrade()` permite autenticar PBKDF2 legacy y reemplazarlo por Argon2 después de un login exitoso.

## Response models

Autenticación usa `LoginResponse` y `TokenResponse`. Nuevas APIs IAM usan schemas Pydantic explícitos.

Al crear endpoints nuevos se debe declarar `response_model` salvo que la respuesta sea streaming/file o exista una razón documentada.

## Testing

`tests/test_iam_api.py` usa `FastAPI TestClient` con override de `get_db()` y SQLite aislada.

Los tests de autorización deben comprobar tanto ALLOW como DENY. Un test directo de una función auxiliar no sustituye un test HTTP para rutas críticas.

`tests/test_migrations.py` verifica la topología de las revisiones Alembic sin conectarse a producción.

`tests/test_container_portability.py` verifica que las defensas de LF y healthcheck local permanezcan en el repositorio.

## Router legacy

`api/expenses.py` y `api/users.py` contienen partes del MVP anterior. Las rutas canónicas extraídas se registran antes que las equivalentes legacy.

Esta estrategia permite migración incremental sin un big-bang rewrite. La meta es retirar gradualmente las ramas basadas en `UserRole`/`can_*` y modularizar el frontend.
