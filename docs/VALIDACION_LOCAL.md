# Validación local con Docker

## Alcance

La validación local tiene dos capas aisladas:

- la suite unitaria del backend usa principalmente SQLite temporal o en memoria;
- la validación funcional con Docker usa PostgreSQL 16 y volúmenes locales del proyecto.

Ninguna de las dos debe usar credenciales, base de datos, archivos ni correo de producción. Antes de ejecutar comandos, confirma que estás en la raíz de este repositorio y que no hay variables de producción exportadas en la terminal. No ejecutes `app.demo_monitoring` directamente en el host: el único comando autorizado en este runbook lo ejecuta dentro del backend de Compose, cuya conexión se fuerza al PostgreSQL local.

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

La configuración usa `backend/.env` solo para ajustes de aplicación. `docker-compose.yml` reemplaza expresamente `DATABASE_URL`, `ENVIRONMENT`, `PUBLIC_URL`, CORS y el modo de correo con valores locales. No cambies `BACKEND_ENV_FILE` a un archivo de producción.

Servicios:

```text
Frontend  http://127.0.0.1:3000
API       http://127.0.0.1:3000/api
Postgres  red interna de Compose
```

## Preview temporal con túnel

El túnel Cloudflare expone la aplicación a Internet y no forma parte de una validación local ordinaria. Úsalo solo cuando el usuario lo solicite expresamente y con datos ficticios.

```powershell
.\scripts\start-preview.ps1
```

En el primer intento se crean `.env.preview` y `backend/.env.preview`. El script se detiene hasta que reemplaces `ADMIN_EMAIL` y `ADMIN_PASSWORD` por credenciales aleatorias propias del preview; no las compartas ni reutilices. El script fuerza `EMAIL_MODE=console` y aplica la URL temporal tanto a `PUBLIC_URL` como a CORS antes de publicar el backend.

Los enlaces y contraseñas temporales generados durante el preview pueden aparecer en logs locales. No publiques esos logs. Al terminar:

```powershell
.\scripts\stop-preview.ps1
```

Este comando conserva volúmenes. La eliminación de datos o volúmenes requiere otra autorización explícita.

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
.\.venv\Scripts\python.exe -m scripts.run_tests

cd ..\frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=moderate
```

El entorno Python de referencia es 3.12, igual que CI y la imagen del backend. Si `.venv` no existe o usa otra versión, vuelve a crearlo e instala `backend/requirements.txt` antes de considerar el resultado equivalente a CI. `npm ci` es obligatorio para respetar `package-lock.json`; no se sustituye por una actualización de dependencias durante una validación.

`scripts.run_tests` deshabilita la carga de `backend/.env` antes de importar la aplicación y fija SQLite, entorno development y correo console. No lo reemplaces por discovery directo: un `.env` local podría apuntar la suite al schema o servicio equivocado.

## Persistencia PostgreSQL

```powershell
docker compose exec -T backend alembic current
docker compose exec -T backend alembic heads
```

Ambos deben indicar `20260825_0011 (head)`.

Las tablas, tipos ENUM, contadores e `alembic_version` deben resolverse dentro de `administracion`. Toda consulta SQL cruda debe usar el nombre calificado derivado del modelo; no debe depender de `search_path`.

## Pruebas adversas mínimas

- token inválido y acceso anónimo → 401;
- payload inválido → 422;
- método no soportado → 405;
- cinco logins fallidos y un sexto intento → 429;
- cinco consumos públicos fallidos de restablecimiento en 15 minutos y el siguiente intento → 429;
- token de restablecimiento expirado, reemplazado o reutilizado → rechazo sin cambio de contraseña;
- Rol con cupo lleno → asignación y reactivación rechazadas; Usuario inactivo asignado no consume cupo;
- reducción del máximo de Rol por debajo de su ocupación activa → 409 sin cambio persistido;
- `SIMPLE` sin `ApprovalPolicy`, con aprobadores por Rol propio, herencia de Grupo
  o Rol global → ronda `MAJORITY` con esos Usuarios;
- `SIMPLE` sin otro Usuario con `requests:approve` → 422 sin `Expense` persistido;
- fallo al iniciar la primera ronda después de cargar soporte → 422 sin
  `Expense`, `ExpenseAttachment` ni archivo físico huérfano;
- origen CORS no autorizado sin `Access-Control-Allow-Origin`;
- exceso del límite autenticado → 429 con `Retry-After`;
- archivo cuyo contenido no coincide con MIME → 415;
- doble decisión o transición cerrada → 409;
- logs sin 500, traceback o secretos.

## Limitaciones conocidas

La suite frontend actual valida contratos y compilación, pero no reemplaza pruebas de navegador. Los clics, modales, responsive y accesibilidad requieren Playwright o una revisión manual explícita.

La aplicación todavía no aplica un límite global temprano al tamaño de todos los cuerpos HTTP; existen límites específicos de schemas y uploads. Debe añadirse middleware 413 antes de considerar completa la defensa contra cuerpos sobredimensionados.

## Diagnóstico de Docker y BuildKit

Para un fallo de estado o salud, recopila primero evidencia sin modificar datos:

```powershell
docker compose ps
docker compose logs --no-color --tail=200 backend
docker compose logs --no-color --tail=200 frontend
```

Si la construcción falla con `parent snapshot ... does not exist` o `failed to prepare extraction snapshot`, el problema pertenece normalmente al estado local de BuildKit, no al código de la aplicación. La secuencia segura es:

1. reintentar solo la imagen afectada con `docker compose build --no-cache backend` o `frontend`;
2. reiniciar Docker Desktop o el daemon de Docker y repetir la construcción;
3. si persiste, detenerse y pedir autorización antes de limpiar cachés.

Una IA no debe ejecutar como solución automática `docker system prune`, `docker volume prune` ni `docker compose down -v`. Los dos últimos pueden eliminar PostgreSQL y adjuntos locales; limpiar caché de build también requiere confirmación porque afecta otras construcciones del equipo.

`docker compose down` sin `-v` detiene el entorno y conserva sus volúmenes. Antes de cualquier operación de borrado se debe identificar el proyecto Compose y los volúmenes exactos.
