# Validación local con Docker

## Alcance

La validación local usa exclusivamente PostgreSQL y volúmenes Docker del proyecto. No debe usar credenciales, base de datos ni correo de producción.

`docker-compose.yml` fuerza por defecto:

```text
ENVIRONMENT=development
EMAIL_MODE=console
DATABASE_SCHEMA=administracion
```

Para cambiar el transporte local se requiere una decisión explícita mediante `LOCAL_EMAIL_MODE`; no se debe habilitar SMTP durante pruebas funcionales automáticas.

## Levantar el entorno

```powershell
docker compose up -d --build
docker compose ps
```

Servicios:

```text
Frontend  http://127.0.0.1:3000
API       http://127.0.0.1:3000/api
Postgres  red interna de Compose
```

## Datos visibles

Las pruebas `unittest` usan bases temporales y eliminan sus fixtures. Sus solicitudes nunca aparecen en la aplicación Docker.

Para crear datos persistentes, idempotentes y marcados como prueba:

```powershell
docker compose exec -T backend python -m app.demo_monitoring
```

Solicitante:

```text
solicitante.prueba@example.com
Demo12345!
```

Votante:

```text
tesorero.prueba@example.com
Demo12345!
```

El sembrador crea catálogo, Roles IAM explícitos, usuarios y cinco solicitudes:

- SIMPLE pendiente;
- SIMPLE aprobada;
- SIMPLE cerrada con factura dummy;
- MULTI_QUOTE con votación abierta;
- MULTI_QUOTE con voto parcial.

Nunca imprime ni envía secretos de producción. Los correos de workflow se muestran únicamente en logs del backend.

## Validación automatizada

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd ..\frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=moderate
```

## Persistencia PostgreSQL

```powershell
docker compose exec -T backend alembic current
docker compose exec -T backend alembic heads
```

Ambos deben indicar `20260821_0004 (head)`.

Las tablas, tipos ENUM, contadores e `alembic_version` deben resolverse dentro de `administracion`. Toda consulta SQL cruda debe usar el nombre calificado derivado del modelo; no debe depender de `search_path`.

## Pruebas adversas mínimas

- token inválido y acceso anónimo → 401;
- payload inválido → 422;
- método no soportado → 405;
- cinco logins fallidos y un sexto intento → 429;
- origen CORS no autorizado sin `Access-Control-Allow-Origin`;
- exceso del límite autenticado → 429 con `Retry-After`;
- archivo cuyo contenido no coincide con MIME → 415;
- doble decisión o transición cerrada → 409;
- logs sin 500, traceback o secretos.

## Limitaciones conocidas

La suite frontend actual valida contratos y compilación, pero no reemplaza pruebas de navegador. Los clics, modales, responsive y accesibilidad requieren Playwright o una revisión manual explícita.

La aplicación todavía no aplica un límite global temprano al tamaño de todos los cuerpos HTTP; existen límites específicos de schemas y uploads. Debe añadirse middleware 413 antes de considerar completa la defensa contra cuerpos sobredimensionados.
