# Flujo de Solicitud de Gastos

Aplicación web para registrar, revisar y aprobar solicitudes de gastos de una propiedad horizontal. Incluye control de usuarios y perfiles, organigrama de junta directiva, trazabilidad, adjuntos, notificaciones por correo y controles de seguridad para producción.

## Arquitectura

- Frontend: React + Vite, desplegado en Vercel.
- Backend: FastAPI + SQLAlchemy, desplegado en Render.
- Base de datos: PostgreSQL en Neon.
- Correo en producción: API HTTPS de Brevo.
- Archivos adjuntos: disco persistente de Render mediante `UPLOAD_DIR`.

## Tipos de usuario

- **Administrador del sistema:** cuenta técnica inicial creada con las variables `ADMIN_*`. Administra el sistema, pero no representa al administrador operativo de la propiedad horizontal.
- **Administrador de la PH:** usuario operativo creado desde el portal y asignado al perfil correspondiente.
- **Miembros de junta directiva:** presidente, vicepresidente, tesorero, vocal u otros perfiles configurados. Todo miembro activo debe estar asociado al menos a un apartamento.
- **Solicitantes y demás usuarios:** sus permisos dependen de los perfiles asignados desde el portal.

La presidencia y tesorería no se configuran con correos fijos en variables de entorno. Los miembros, cargos, unidades y políticas de aprobación se administran desde el portal web.

## Reglas principales

- La cédula se normaliza y debe ser única entre los usuarios.
- Las personas se pueden buscar por cédula, nombre, apellido o correo electrónico.
- Los miembros activos de junta directiva deben estar vinculados al menos a un apartamento.
- Las aprobaciones se asignan por perfiles y políticas configurables, no por direcciones de correo codificadas.
- Los eventos de aprobación son de solo anexado para preservar la auditoría.
- Las aprobaciones pendientes no expiran por tiempo; permanecen vigentes hasta recibir respuesta o hasta que el flujo sea invalidado.

## Seguridad

- JWT con vencimiento absoluto configurable mediante `TOKEN_EXPIRE_MINUTES`.
- Cierre de sesión tras `SESSION_IDLE_MINUTES` minutos sin actividad humana. El frontend informa actividad mediante `POST /api/auth/activity`; el polling no mantiene viva la sesión.
- Revocación de sesiones mediante una versión de sesión almacenada por usuario.
- Bloqueo temporal por intentos fallidos de inicio de sesión.
- Límites separados para lecturas, escrituras, cargas y acciones sensibles.
- Validación del contenido real de archivos PDF, JPEG, PNG y WEBP.
- CORS restringido, CSP y encabezados de seguridad en producción.
- Secretos y contraseñas fuera del repositorio.

Valores iniciales recomendados:

```env
TOKEN_EXPIRE_MINUTES=480
SESSION_IDLE_MINUTES=30
USER_READ_RATE_LIMIT=120
USER_WRITE_RATE_LIMIT=30
USER_UPLOAD_RATE_LIMIT=6
USER_SENSITIVE_RATE_LIMIT=10
```

Los límites se expresan por usuario y por minuto. Deben ajustarse usando métricas reales antes de aumentarlos.

## Correo con Brevo

En producción se usa la API HTTPS de Brevo, por lo que no es necesario configurar un puerto SMTP en Render.

```env
EMAIL_MODE=brevo
BREVO_API_KEY=< CLAVE API DE BREVO >
BREVO_SENDER_NAME=< NOMBRE VISIBLE DEL REMITENTE >
EMAIL_FROM=< CORREO VERIFICADO EN BREVO >
```

El correo de `EMAIL_FROM` debe estar verificado en Brevo. SMTP puede conservarse como opción local; Brevo ofrece `smtp-relay.brevo.com` y el puerto `587`, pero no es la opción recomendada cuando Render bloquea conexiones SMTP salientes.

## Desarrollo local

### Requisitos

- Python 3.12 o compatible.
- Node.js 20 o compatible.
- PostgreSQL o una cadena de conexión de Neon.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Copia los archivos `.env.example` correspondientes y reemplaza únicamente los marcadores `< LO QUE SE SUPONE QUE DEBERIA IR >`. Nunca uses claves reales en archivos versionados.

## Variables de Render

```env
ENVIRONMENT=production
DATABASE_URL=< URL DE CONEXION DE NEON >
PUBLIC_URL=< URL PUBLICA DEL FRONTEND EN VERCEL >
CORS_ALLOWED_ORIGINS=< URL PUBLICA DEL FRONTEND EN VERCEL >

SECRET_KEY=< SECRETO ALEATORIO LARGO >
TOKEN_EXPIRE_MINUTES=480
SESSION_IDLE_MINUTES=30

USER_READ_RATE_LIMIT=120
USER_WRITE_RATE_LIMIT=30
USER_UPLOAD_RATE_LIMIT=6
USER_SENSITIVE_RATE_LIMIT=10

EMAIL_MODE=brevo
BREVO_API_KEY=< CLAVE API DE BREVO >
BREVO_SENDER_NAME=< NOMBRE VISIBLE DEL REMITENTE >
EMAIL_FROM=< CORREO VERIFICADO EN BREVO >

ADMIN_NAME=Administrador del sistema
ADMIN_EMAIL=< CORREO DEL ADMINISTRADOR DEL SISTEMA >
ADMIN_PASSWORD=< CONTRASENA SEGURA DE AL MENOS 12 CARACTERES >

UPLOAD_DIR=/app/uploads
MAX_UPLOAD_STORAGE_MB=450
```

`MAX_UPLOAD_STORAGE_MB` es el máximo total que la aplicación permite ocupar dentro de `UPLOAD_DIR`; no es el tamaño máximo de un archivo individual.

No configures `TREASURER_EMAIL`, `PRESIDENT_EMAIL` ni variables SMTP si `EMAIL_MODE=brevo`.

## Variable de Vercel

```env
VITE_API_URL=< URL PUBLICA DEL BACKEND EN RENDER >
```

Después de cambiar variables en Render o Vercel, realiza un nuevo despliegue.

## Orden recomendado de despliegue

1. Publica primero el backend actualizado en Render.
2. Confirma que abre el puerto asignado por Render y que el endpoint de salud responde.
3. Ejecuta o deja completar las migraciones.
4. Publica el frontend en Vercel con la URL correcta del backend.
5. Comprueba el inicio de sesión, `POST /api/auth/activity`, la búsqueda de personas y un envío real de correo.

Si Render queda en `Waiting for application startup` o muestra `No open ports detected`, revisa el error anterior en el log. Normalmente la aplicación no abrió el puerto porque falló una migración o una conexión con PostgreSQL. No termines sesiones de Neon sin identificar primero el proceso y su consulta.

## Reiniciar Neon desde cero

El reinicio elimina datos y debe hacerse solamente de forma explícita:

1. Crea una rama de respaldo en Neon.
2. Detén temporalmente el backend o evita nuevos accesos.
3. Confirma que Render ya contiene la versión nueva del código.
4. Vacía el esquema de la rama de producción y ejecuta las migraciones o la inicialización.
5. Verifica que se creó solamente el administrador técnico definido por `ADMIN_*`.
6. Crea desde el portal el administrador de la PH, apartamentos, perfiles y miembros de junta.
7. Comprueba las restricciones de cédula única y asignación de apartamentos.

Vaciar Neon no elimina los archivos del disco persistente de Render. Para reiniciar completamente el entorno también debe vaciarse por separado el contenido de `/app/uploads`, conservando el directorio montado.

## Endpoints destacados

- `POST /api/auth/login`: inicio de sesión.
- `POST /api/auth/activity`: registra actividad humana y renueva la sesión activa.
- `GET /api/users`: listado y búsqueda por cédula, nombre o correo.
- Rutas de organigrama: cargos, junta y unidades.
- Rutas de solicitudes: creación, consulta, adjuntos y seguimiento.
- Rutas de aprobación: decisiones mediante sesión o enlace seguro.

La documentación interactiva está disponible en `/api/docs` cuando la configuración del entorno la habilita.

## Verificación

```bash
cd backend
pytest
```

```bash
cd frontend
npm run build
```

Antes de producción prueba también:

- expiración por 30 minutos de inactividad;
- renovación con actividad humana;
- límites de solicitudes;
- rechazo de una cédula duplicada;
- rechazo de un miembro activo de junta sin apartamento;
- envío mediante Brevo;
- carga y descarga autorizada de adjuntos.
