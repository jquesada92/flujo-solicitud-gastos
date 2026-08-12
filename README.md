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

## Historial de eventos para streaming

Además del estado vigente en `approvals`, cada transición se registra de forma
append-only en `approval_step_events`. La escritura del evento ocurre en la misma
transacción que el cambio de estado, por lo que la tabla puede ingerirse mediante
CDC hacia un stream o datalake sin reconstruir el historial desde snapshots.

- `event_sequence`: cursor incremental de PostgreSQL para lectura ordenada.
- `event_id`: UUID estable para deduplicación/idempotencia en consumidores.
- `occurred_at`: fecha y hora asignadas por PostgreSQL con zona horaria.
- `flow_id` y `step`: partición y orden lógico dentro de cada flujo.
- Estados anterior/nuevo, actor, comentario y estado de la solicitud.
- `payload`: sobre JSON versionado con el evento completo y snapshot de negocio.

Los eventos actuales son `STEP_CREATED`, `STEP_ACTIVATED`, `STEP_APPROVED`,
`STEP_REJECTED`, `STEP_REVISION_REQUESTED` y `STEP_EXPIRED`. Esta tabla es
inmutable por diseño: no debe exponerse a operaciones de actualización o borrado.

### Ejecutar CDC con Debezium

El archivo adicional `docker-compose.cdc.yml` agrega un broker Kafka en modo
KRaft, Kafka Connect con Debezium y un inicializador idempotente del conector.
Es completamente opcional y no forma parte del funcionamiento de los flujos.
La aplicación siempre captura los eventos en PostgreSQL; solo al combinar ambos
archivos PostgreSQL arranca con `wal_level=logical`, slots y WAL senders habilitados.

Para trabajar únicamente en la funcionalidad y capturar eventos en la base de
datos, usa el arranque normal:

```bash
docker compose up --build
```

Cuando se quiera transmitir esos eventos, agrega la infraestructura CDC:

```bash
docker compose -f docker-compose.yml -f docker-compose.cdc.yml up --build -d
```

El conector usa `pgoutput`, crea la publicación filtrada
`ph_expense_approval_events_pub` y el slot persistente
`ph_expense_approval_events_slot`. Solo captura:

```text
public.approval_step_events
```

Los registros llegan a:

```text
ph_expenses.public.approval_step_events
```

Comprobar el conector:

```bash
curl http://localhost:8083/connectors/ph-expense-approval-events/status
```

Consumir eventos desde el inicio (PowerShell):

```powershell
docker compose -f docker-compose.yml -f docker-compose.cdc.yml exec kafka `
  /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server kafka:9092 `
  --topic ph_expenses.public.approval_step_events `
  --from-beginning
```

Revisar el slot y su retención de WAL:

```sql
SELECT slot_name, active, restart_lsn, confirmed_flush_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
WHERE slot_name = 'ph_expense_approval_events_slot';
```

La imagen local reutiliza el usuario configurado en `POSTGRES_USER`, creado como
administrador por la imagen oficial de PostgreSQL. En producción se debe usar un
usuario dedicado con `LOGIN REPLICATION`, permisos de conexión y `SELECT` sobre
la tabla, y crear la publicación explícitamente. Hay que monitorear el slot: si
Debezium permanece detenido, PostgreSQL conserva WAL hasta el límite configurado.

## Ejecutar

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
