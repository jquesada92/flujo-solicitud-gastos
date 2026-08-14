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

| Ambiente | Frontend | Backend | Base de datos | Archivos | Uso |
|---|---|---|---|---|---|
| Local | Docker/Nginx en `localhost:3000` | Docker/FastAPI | PostgreSQL Docker local | Volumen Docker local | Desarrollo diario. |
| Preview Cloudflare | Cloudflare Quick Tunnel hacia el frontend Docker | Docker/FastAPI local | PostgreSQL Docker aislado de producción | Volumen Docker local | Demostraciones y pruebas remotas temporales. |
| Producción | Vercel | Render | Neon | Disco persistente de Render | Aplicación estable para usuarios finales. |

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

### Preview con Cloudflare Tunnel

Este ambiente publica temporalmente el stack Docker local. No utiliza Neon,
Vercel ni Render y nunca debe recibir `DATABASE_URL` de producción.

Prepara sus variables separadas:

```powershell
.\scripts\start-preview.ps1
```

El script crea `.env.preview` cuando no existe, levanta los contenedores, captura
automáticamente la URL `https://...trycloudflare.com`, actualiza `PUBLIC_URL`,
recrea el backend y muestra la URL lista para compartir.

Para detenerlo sin eliminar datos locales:

```powershell
.\scripts\stop-preview.ps1
```

El nombre de proyecto `flujo-gastos-preview` crea volúmenes diferentes de los del
ambiente local. Local y preview escuchan en el mismo puerto 3000, por lo que se usa
uno a la vez.

### Producción

- Frontend en Vercel, con Root Directory `frontend` y `VITE_API_URL` apuntando a Render.
- Backend en Render, definido por `render.yaml`.
- PostgreSQL en Neon mediante `DATABASE_URL` configurada en Render.
- Archivos en el disco persistente `/app/uploads` de Render.

Para mantener el almacenamiento de documentos por debajo de 0.5 GB, el backend
usa `MAX_UPLOAD_STORAGE_MB=450`. Antes de guardar cotizaciones o facturas calcula
el espacio utilizado y rechaza la carga con HTTP `507` si excedería ese límite.
Los 50 MB restantes funcionan como margen operativo. Este límite corresponde al
disco de archivos de Render; el almacenamiento relacional de Neon se monitorea por
separado desde su panel.

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
| `docker-compose.preview.yml` | Preview | Agrega Cloudflare Quick Tunnel al stack Docker. | Para demostraciones remotas temporales. |
| `.env.preview.example` | Preview | Plantilla aislada de variables para el ambiente Cloudflare. | Se copia como `.env.preview`; nunca apunta a Neon. |
| `.env.preview` | Preview | Contiene la URL temporal de Cloudflare y credenciales de preview. | Al ejecutar el proyecto Compose `flujo-gastos-preview`; no se sube a Git. |
| `scripts/start-preview.ps1` | Preview | Inicia el ambiente, captura la URL de Cloudflare y actualiza `PUBLIC_URL`. | Al publicar una nueva sesión temporal de preview. |
| `scripts/stop-preview.ps1` | Preview | Detiene los contenedores de preview sin borrar sus volúmenes. | Al finalizar una demostración remota. |
| `.env.production.example` | Producción | Documenta las variables requeridas por Render y Neon. | Como referencia al configurar producción. |
| `frontend/.env.example` | Local/producción | Documenta `VITE_API_URL`; vacía en Docker y con la URL de Render en Vercel. | Al configurar el frontend en cada ambiente. |
| `backend/Dockerfile` | Todos | Construye y ejecuta FastAPI con Python y Uvicorn. | En local, preview, CI y Render. |
| `frontend/Dockerfile` | Local/preview/CI | Compila React/Vite y lo sirve mediante Nginx. | En Docker local, Cloudflare y validaciones de CI. |
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
