# Prompt maestro para reconstruir la aplicación

## INICIO DEL PROMPT

Construye una aplicación web lista para producción llamada **Flujo de Solicitud de Gastos**, destinada a administrar solicitudes, revisiones y aprobaciones de gastos de una propiedad horizontal.

Debe ser segura, auditable y responsive, con frontend en Vercel, backend en Render y PostgreSQL en Neon.

## 1. Arquitectura

- Frontend: React con Vite.
- Backend: FastAPI con SQLAlchemy y migraciones controladas.
- Base de datos: PostgreSQL compatible con Neon.
- Autenticación: JWT con revocación y control real de inactividad.
- Correo de producción: API HTTPS de Brevo.
- Archivos: almacenamiento privado persistente configurable.

Separa modelos, esquemas, servicios, rutas, seguridad, configuración y pruebas.

## 2. Usuarios, perfiles y permisos

Implementa autorización basada en perfiles y permisos comprobados siempre por el backend.

Distingue:

- **Administrador del sistema:** cuenta técnica inicial creada con `ADMIN_NAME`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`. No representa al administrador operativo de la PH.
- **Administrador de la PH:** usuario operativo creado desde el portal.
- **Miembros de junta directiva:** usuarios asociados a cargos como presidente, vicepresidente, tesorero y vocal.
- **Solicitantes y otros usuarios:** acceso determinado por sus perfiles y permisos.

Los miembros y cargos de junta se administran desde el portal. No uses `TREASURER_EMAIL` ni `PRESIDENT_EMAIL`. Permite inactivar usuarios sin borrar su historial.

## 3. Personas, cédula y apartamentos

Cada usuario puede incluir nombre, apellidos, correo, cédula, estado y unidades asociadas.

Requisitos:

- Buscar por cédula, nombre, apellido o correo electrónico.
- Normalizar la cédula eliminando espacios externos y unificando mayúsculas.
- Impedir duplicados en el servicio y con un índice único normalizado en PostgreSQL.
- Devolver HTTP 409 con un mensaje claro ante una cédula existente.
- Mostrar una sola fila por usuario y agrupar sus apartamentos.
- Exigir al menos un apartamento a cada miembro activo de junta.
- Aplicar esa regla al crear, editar, activar, importar o modificar en lote.

El administrador técnico puede usar la unidad lógica `Administración` y no está sujeto a la regla de apartamento de la junta.

## 4. Organigrama y junta

Permite administrar perfiles, permisos, cargos, miembros activos e inactivos, apartamentos y políticas de aprobación. Explica en la interfaz la diferencia entre el administrador técnico y el administrador operativo de la PH. No incrustes correos personales en el código.

## 5. Solicitudes de gasto

Cada solicitud debe contener solicitante, concepto, descripción, monto, moneda, fecha, estado, adjuntos, historial, pasos de aprobación, comentarios y decisiones.

Usa estados coherentes como borrador, pendiente, aprobado, rechazado y cancelado. Registra quién realizó cada transición y cuándo.

## 6. Aprobaciones

Implementa políticas configurables por perfil, con uno o varios pasos.

- Permite decidir desde una sesión autorizada o un enlace firmado.
- Los enlaces expiran según `APPROVAL_LINK_HOURS`, recomendado en 72 horas.
- Los eventos de aprobación son de solo anexado.
- Protégelos en PostgreSQL contra actualización y eliminación.
- Invalida enlaces consumidos, vencidos o incompatibles con el estado actual.

## 7. Sesiones

Implementa dos límites independientes:

- Vencimiento absoluto: `TOKEN_EXPIRE_MINUTES=480`.
- Inactividad humana: `SESSION_IDLE_MINUTES=30`.

La sesión debe expirar solamente después de 30 minutos sin actividad humana. Clics, navegación, teclado y acciones reales pueden informar actividad mediante `POST /api/auth/activity`. Polling y solicitudes automáticas no deben extenderla.

Al registrar actividad válida, actualiza el último momento activo y renueva la sesión. Usa una versión de sesión por usuario para revocar todos sus JWT tras cambios de contraseña, desactivación u otra acción administrativa.

Limita los intentos fallidos de inicio de sesión, por ejemplo a 5 dentro de 15 minutos, sin revelar si el correo existe.

## 8. Límites de solicitudes

Separa límites por usuario y tipo de operación. Valores iniciales por minuto:

- Lecturas: `USER_READ_RATE_LIMIT=120`.
- Escrituras: `USER_WRITE_RATE_LIMIT=30`.
- Cargas: `USER_UPLOAD_RATE_LIMIT=6`.
- Acciones sensibles: `USER_SENSITIVE_RATE_LIMIT=10`.

Devuelve HTTP 429 al superarlos. No uses una única regla agresiva para toda la aplicación. Diseña los contadores para poder migrarlos a Redis si el backend utiliza varias instancias.

## 9. Adjuntos

Admite PDF, JPEG, PNG y WEBP. Valida extensión, MIME, firma real, tamaño individual y cuota total. Usa nombres internos impredecibles y autorización para descargar.

En Render usa:

```env
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_STORAGE_MB=450
```

El directorio no debe ser público. Reiniciar PostgreSQL no vacía el disco de Render.

## 10. Correo

En producción usa la API HTTPS de Brevo:

```env
EMAIL_MODE=brevo
BREVO_API_KEY=< CLAVE API DE BREVO >
BREVO_SENDER_NAME=< NOMBRE VISIBLE DEL REMITENTE >
EMAIL_FROM=< CORREO VERIFICADO EN BREVO >
```

Centraliza el envío, configura tiempos de espera y registra errores sin secretos. SMTP puede mantenerse como adaptador opcional local, pero no debe ser obligatorio en Render.

## 11. Seguridad

Incluye:

- validación estricta de configuración;
- `SECRET_KEY` aleatoria y larga;
- CORS limitado a orígenes HTTPS;
- CSP, HSTS bajo HTTPS y encabezados de seguridad;
- hashing fuerte de contraseñas;
- ORM y consultas parametrizadas;
- errores sin secretos ni trazas internas;
- auditoría de operaciones sensibles;
- protección contra asignación masiva de permisos;
- validación de archivos por contenido;
- dependencias fijadas y análisis de seguridad en CI.

Nunca incluyas secretos reales. Usa:

```env
VARIABLE=< LO QUE SE SUPONE QUE DEBERIA IR >
```

Si una credencial fue publicada, debe rotarse; eliminarla del archivo no basta.

## 12. Variables de despliegue

Render:

```env
ENVIRONMENT=production
DATABASE_URL=< URL DE CONEXION DE NEON >
PUBLIC_URL=< URL PUBLICA DEL FRONTEND EN VERCEL >
CORS_ALLOWED_ORIGINS=< URL PUBLICA DEL FRONTEND EN VERCEL >
SECRET_KEY=< SECRETO ALEATORIO LARGO >

TOKEN_EXPIRE_MINUTES=480
SESSION_IDLE_MINUTES=30
APPROVAL_LINK_HOURS=72
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

Vercel:

```env
VITE_API_URL=< URL PUBLICA DEL BACKEND EN RENDER >
```

No agregues correos fijos de tesorería o presidencia ni SMTP si Brevo usa API.

## 13. Base de datos

Usa migraciones repetibles y evita bloqueos largos durante el arranque. Incluye restricciones para correo único cuando corresponda, cédula única normalizada, relaciones válidas y eventos de aprobación de solo anexado.

Para reiniciar Neon:

1. Crear una rama de respaldo.
2. Detener o aislar el backend.
3. Desplegar el código actualizado.
4. Confirmar la rama y vaciar el esquema.
5. Ejecutar migraciones y semillas mínimas.
6. Crear solamente el administrador técnico con `ADMIN_*`.
7. Crear desde el portal usuarios operativos, junta, apartamentos y políticas.
8. Ejecutar pruebas de integridad.

No termines conexiones a ciegas: identifica PID, usuario, estado, consulta y antigüedad.

## 14. Interfaz

Crea pantallas responsive para inicio de sesión, tablero, solicitudes, aprobaciones, usuarios, perfiles y permisos, organigrama, apartamentos, auditoría y configuración.

Muestra errores junto al campo correspondiente. Los conflictos de cédula y junta sin apartamento deben ser claros y accionables.

## 15. Criterios de aceptación

Demuestra mediante pruebas que:

- producción rechaza configuración insegura;
- una cédula duplicada devuelve conflicto;
- la búsqueda funciona por cédula, nombre y correo;
- un miembro activo de junta sin apartamento es rechazado;
- el administrador técnico se distingue del administrador de la PH;
- la sesión expira después de 30 minutos sin actividad humana;
- el polling no renueva la sesión y la actividad válida sí;
- los límites devuelven HTTP 429;
- los permisos se validan en backend;
- archivos inválidos se rechazan por contenido;
- los eventos históricos no se pueden alterar;
- Brevo envía desde un remitente verificado;
- `pytest` finaliza correctamente;
- `npm run build` compila el frontend.

Entrega también archivos `.env.example` sin secretos, instrucciones para Render/Vercel/Neon y un procedimiento de recuperación con una rama de respaldo antes de borrar datos.

## FIN DEL PROMPT
