# PH Expense Approval MVP

Incluye autenticación con token, registro administrado de usuarios y control de acceso por rol.

## Usuarios y roles

- `REQUESTER`: crea solicitudes y consulta únicamente las propias.
- `APPROVER`: consulta solicitudes y decide aprobaciones asignadas a su correo.
- `VIEWER`: acceso de lectura a las solicitudes.
- `ADMIN`: acceso total y administración de usuarios.

Antes del primer arranque configure `SECRET_KEY`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`
en `.env`. El backend crea ese administrador inicial cuando aún no existen usuarios.
Los usuarios posteriores se registran desde la sección **Usuarios**. El correo de un
aprobador debe coincidir con el configurado en la regla de aprobación.

Al registrar un usuario, el backend genera una contraseña temporal segura y envía
una invitación a su correo. En el primer inicio de sesión, la API bloquea todas las
operaciones hasta que el usuario reemplace esa contraseña. Con `EMAIL_MODE=console`,
la invitación se imprime en los logs del backend; para entrega real usa `smtp`.

El alta permite definir los cuatro permisos iniciales. Las modificaciones posteriores
se preparan en la interfaz y se aplican juntas con un único botón **Guardar cambios**.
El guardado masivo es transaccional: si una modificación falla, ninguna se aplica. Cada creación o
cambio genera un registro append-only en `user_change_events` con fecha/hora, actor,
usuario afectado, campos modificados y estados anterior/nuevo.

Los cargos se administran como perfiles persistentes en `access_profiles`: se pueden
crear, renombrar, activar/desactivar y configurar granularmente. Al asignar un cargo,
sus permisos se convierten en los permisos efectivos del usuario y no pueden editarse
individualmente. Al modificar los permisos de un perfil, el cambio se propaga a todos
sus usuarios relacionados. Los cambios de perfiles se auditan en
`access_profile_change_events`.

Cada cargo puede activar el flag **Tiene límite** y definir un máximo de personas
activas relacionadas. Sin el flag, no existe límite. Presidente, Vicepresidente y
Tesorero se precargan con límite 1, pero la regla es configurable para cualquier
cargo. La API y un trigger transaccional de PostgreSQL validan el cupo; no se permite
reducirlo por debajo de las asignaciones activas existentes.

MVP dockerizado para registrar solicitudes de gastos y ejecutar un flujo secuencial de aprobación configurable por tipo de gasto y monto.

## Stack

- React + Vite
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker Compose
- Gmail SMTP opcional

## Flujo incluido

1. El usuario crea una solicitud desde React.
2. FastAPI guarda la solicitud en PostgreSQL.
3. El Approval Engine busca reglas aplicables por `expense_type` y rango de monto.
4. Se crean los pasos de aprobación.
5. El primer aprobador recibe un enlace único.
6. Al aprobar, se activa y notifica el siguiente paso.
7. Al terminar todos los pasos, la solicitud queda `APPROVED`.
8. Si cualquier paso rechaza, queda `REJECTED`.

## Historial de eventos de aprobación

Cada transición se registra de forma append-only en `approval_step_events`, dentro
de la misma transacción que modifica el estado. Esto conserva el historial completo
y permite incorporar CDC en el futuro sin perder eventos ni reconstruir snapshots.

La tabla incluye un cursor monotónico (`event_sequence`), un UUID idempotente
(`event_id`), fecha de base de datos con zona horaria, identificadores del flujo y
la solicitud, estados anterior y nuevo, actor, comentario y un `payload` JSON
versionado. PostgreSQL impide actualizar o borrar sus registros mediante un trigger.

Los eventos registrados son `STEP_CREATED`, `STEP_ACTIVATED`, `STEP_APPROVED`,
`STEP_REJECTED`, `STEP_REVISION_REQUESTED` y `STEP_EXPIRED`.

## Ambientes

### Desarrollo local

Todo el ambiente de desarrollo corre localmente: PostgreSQL, FastAPI, React/Nginx
y el volumen de adjuntos. No utiliza Neon ni servicios de producción.

```bash
cp .env.example .env
docker compose up --build
```

Abrir:

- Aplicación: http://localhost:3000
- OpenAPI/FastAPI: http://localhost:3000/api/docs (nota: Nginx solo enruta `/api/`; FastAPI docs se puede exponer agregando una ruta proxy o publicando el backend localmente)

Para ver los correos durante desarrollo:

```bash
docker compose logs -f backend
```

Con `EMAIL_MODE=console`, los enlaces de aprobación aparecen en esos logs.

Los datos y archivos locales permanecen en los volúmenes Docker `postgres_data`
y `expense_uploads`. Para detener el ambiente sin borrar datos:

```bash
docker compose down
```

### Producción

- Frontend en Vercel, con Root Directory `frontend` y `VITE_API_URL` apuntando a Render.
- Backend en Render, definido por `render.yaml`.
- PostgreSQL en Neon mediante `DATABASE_URL` configurada en Render.
- Archivos en el disco persistente `/app/uploads` de Render.

Las variables de referencia están en `.env.production.example`. Los valores reales
se configuran en los paneles de Render y Vercel y nunca se guardan en Git.

### CI/CD con GitHub Actions

Los Pull Requests y las ramas de trabajo ejecutan `.github/workflows/ci.yml`, que
valida Python, construye Vite y construye ambas imágenes Docker. Un push a `main`
ejecuta nuevamente las validaciones y, si pasan, activa Render y luego Vercel con
`.github/workflows/deploy-production.yml`.

Configura en GitHub `Settings > Environments` un ambiente llamado `production` y
agrega estos Environment secrets:

- `RENDER_DEPLOY_HOOK`: deploy hook del servicio backend en Render.
- `VERCEL_DEPLOY_HOOK`: deploy hook del proyecto frontend en Vercel.

Si deseas aprobación manual antes de publicar, agrega Required reviewers al ambiente
`production`. Desactiva los deploys automáticos por Git en Render y Vercel para no
generar un segundo despliegue paralelo; GitHub Actions será el orquestador.

## Publicar el MVP gratuitamente

La configuración opcional `docker-compose.preview.yml` abre un Cloudflare Quick
Tunnel HTTPS hacia el frontend. No expone PostgreSQL ni FastAPI directamente, no
requiere abrir puertos del router y no necesita dominio ni cuenta de Cloudflare.

```powershell
docker compose -f docker-compose.yml -f docker-compose.preview.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.preview.yml logs tunnel
```

En los logs aparecerá una dirección parecida a:

```text
https://palabras-aleatorias.trycloudflare.com
```

Antes de probar correos de aprobación o invitaciones, copia esa dirección en
`.env` y recrea el backend:

```env
PUBLIC_URL=https://palabras-aleatorias.trycloudflare.com
```

```powershell
docker compose up -d --force-recreate backend
```

La URL cambia si se recrea el contenedor `tunnel`; en ese caso actualiza
`PUBLIC_URL` nuevamente. La computadora, Docker y el túnel deben permanecer
encendidos. Esta modalidad sirve para demostraciones y validación de un MVP, pero
Cloudflare no ofrece SLA para Quick Tunnels. La autenticación de la aplicación
sigue siendo obligatoria y el puerto local 3000 solo escucha en `127.0.0.1`.

Para detener la publicación:

```powershell
docker compose -f docker-compose.yml -f docker-compose.preview.yml down
```

## Gmail real

Para hacer una primera prueba simple con Gmail SMTP:

1. Activa la verificación en dos pasos de la cuenta Google si corresponde.
2. Crea una contraseña de aplicación para la integración.
3. Configura `.env`:

```env
EMAIL_MODE=smtp
SMTP_USER=correo-del-ph@gmail.com
SMTP_PASSWORD=contraseña-de-aplicacion
EMAIL_FROM=correo-del-ph@gmail.com
```

No pongas la contraseña normal de Gmail en el repositorio.

Para producción, conviene evolucionar el envío a OAuth/Google API o a un proveedor transaccional de correo y administrar los secretos en un secret manager.

## Reglas iniciales de demostración

Al iniciar por primera vez, el backend crea estas reglas:

- `ADMINISTRATION` hasta $500 → Tesorero.
- `ADMINISTRATION` desde $500.01 → Tesorero → Presidente.
- `MAINTENANCE` → Tesorero → Presidente.
- `EXTRAORDINARY` → Presidente.

Los correos de Tesorero y Presidente se toman de `.env`.

Las reglas se guardan en PostgreSQL y pueden consultarse/crearse mediante `/api/rules`.

## Endpoints principales

```text
GET  /api/health
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/change-password
GET  /api/users
GET  /api/users/changes
POST /api/users
PATCH /api/users/{id}
GET  /api/expenses
GET  /api/expenses/invoices?q={texto}&category={codigo}
POST /api/expenses
GET  /api/approvals/{token}
POST /api/approvals/{token}
GET  /api/rules
POST /api/rules
```

## Resumen de archivos de ambientes y CI/CD

| Archivo | Ambiente | Propósito | Cuándo se utiliza |
|---|---|---|---|
| `docker-compose.yml` | Desarrollo | Levanta PostgreSQL, backend, frontend y volúmenes locales. | Al desarrollar y probar localmente. |
| `.env.example` | Desarrollo | Plantilla de variables locales sin secretos reales. | Se copia como `.env` al preparar el entorno local. |
| `.env` | Desarrollo | Contiene credenciales y configuración local de cada desarrollador. | Al ejecutar Docker Compose; nunca se sube a Git. |
| `.env.production.example` | Producción | Documenta las variables requeridas por Render y Neon. | Como referencia al configurar producción. |
| `frontend/.env.example` | Desarrollo/producción | Documenta `VITE_API_URL`; vacía en local y con la URL de Render en Vercel. | Al configurar el frontend en cada ambiente. |
| `backend/Dockerfile` | Desarrollo/producción | Construye y ejecuta FastAPI con Python y Uvicorn. | En CI, Docker local y Render. |
| `frontend/Dockerfile` | Desarrollo/CI | Compila React/Vite y lo sirve mediante Nginx. | En Docker local y validaciones de CI. |
| `frontend/package-lock.json` | Todos | Fija las versiones exactas de las dependencias npm. | En `npm ci`, Docker, Vercel y GitHub Actions. |
| `frontend/vercel.json` | Producción | Configura Vite, rutas SPA y caché de `index.html` en Vercel. | En cada despliegue del frontend. |
| `render.yaml` | Producción | Define el backend, health check, variables y disco persistente en Render. | Al crear o actualizar el servicio backend. |
| `.github/workflows/ci.yml` | CI | Valida backend, frontend e imágenes Docker sin desplegar. | En Pull Requests y pushes fuera de `main`. |
| `.github/workflows/reusable-ci.yml` | CI/CD | Proporciona las validaciones reutilizables previas al despliegue. | Cuando lo invoca el workflow de producción. |
| `.github/workflows/deploy-production.yml` | CD | Valida `main` y activa los deploy hooks de Render y Vercel. | En pushes a `main` o ejecuciones manuales. |
| `.gitignore` | Todos | Excluye secretos, dependencias, cachés y artefactos generados. | En cada operación de Git. |

Ejemplo para crear una solicitud:

```json
{
  "title": "Reparación bomba de agua",
  "description": "Reemplazo de bomba principal",
  "expense_type": "MAINTENANCE",
  "amount": 3850,
  "supplier": "Bombas Panamá S.A."
}
```

## Próximas mejoras recomendadas

- Autenticación con Google OAuth.
- Recuperación y cambio autónomo de contraseña.
- Adjuntar cotizaciones y facturas.
- Reglas `PARALLEL`, `MAJORITY` y `MINIMUM_APPROVALS`.
- Audit log inmutable.
- Presupuesto y centros de costo.
- Alembic para migraciones de esquema.
- Tests de integración.
- HTTPS y tokens de aprobación con expiración.
