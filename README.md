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
GET  /api/users
POST /api/users
PATCH /api/users/{id}
GET  /api/expenses
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
