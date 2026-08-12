# Prompt maestro para reconstruir el sistema de gestión de gastos del PH

Puedes copiar desde **INICIO DEL PROMPT** hasta **FIN DEL PROMPT** y usarlo en un agente de desarrollo. Está redactado para reconstruir el sistema completo desde cero, no solamente una maqueta.

---

## INICIO DEL PROMPT

Actúa como arquitecto de software y desarrollador full-stack senior. Construye desde cero una aplicación web funcional, segura, responsive y dockerizada llamada **PH · Gestión de Gastos**, destinada a registrar, aprobar, corregir, cancelar y cerrar solicitudes de gasto de una propiedad horizontal.

No entregues una maqueta ni datos simulados como solución final. Implementa frontend, API, persistencia, autenticación, autorización, carga de archivos, correo y flujo de aprobación real. Todo texto visible para el usuario debe estar en español y todos los importes deben manejar dos decimales sin usar punto flotante para cálculos monetarios.

### 1. Stack y arquitectura

- Frontend: React con Vite, SPA responsive, JavaScript o TypeScript.
- Backend: Python con FastAPI, Pydantic y SQLAlchemy 2.
- Base de datos: PostgreSQL 16.
- Autenticación: JWT Bearer con expiración configurable.
- Contraseñas: hash PBKDF2-SHA256 con salt único y un número alto de iteraciones; nunca almacenar texto plano.
- Archivos: volumen persistente independiente, nombres internos aleatorios y nombre original conservado en la base de datos.
- Correo: SMTP configurable, compatible con SSL y STARTTLS, más modo `console` para desarrollo.
- Infraestructura: Dockerfiles para frontend y backend y un `docker-compose.yml` que levante PostgreSQL, API y frontend.
- Producción local: Nginx sirve la SPA, resuelve rutas del cliente con fallback a `index.html` y actúa como proxy de `/api/` al backend.
- Agrega OpenAPI en `/api/docs` y un endpoint `GET /api/health`.
- Usa variables de entorno y proporciona `.env.example`; no incluyas secretos reales.

### 2. Usuarios, perfiles y permisos

Implementa estos perfiles iniciales:

- `REQUESTER`: solicita gastos y consulta únicamente sus propias solicitudes.
- `APPROVER`: consulta y decide los pasos asignados exactamente a su correo.
- `VIEWER`: consulta solicitudes.
- `ADMIN`: acceso total.

Además del perfil, cada usuario debe tener permisos booleanos independientes:

- `can_request`: crear, corregir y cancelar solicitudes propias.
- `can_approve`: decidir aprobaciones asignadas.
- `can_view`: consultar solicitudes.
- `can_configure`: administrar usuarios y catálogos.

El administrador siempre debe poder ejecutar todas las operaciones. Los usuarios tienen nombre, correo único normalizado a minúsculas, contraseña, perfil, estado activo y fecha de creación. Un usuario inactivo no puede iniciar sesión ni continuar usando un token anterior. Al crear un usuario, no pidas una contraseña al administrador: genera una contraseña temporal criptográficamente segura, envíala por correo y marca la cuenta para cambio obligatorio. En el primer inicio de sesión muestra una pantalla para ingresar la contraseña temporal, crear y confirmar una nueva de al menos diez caracteres. Mientras el cambio esté pendiente, el backend debe bloquear cualquier operación excepto consultar la sesión y cambiar la contraseña. Si el envío de la invitación falla, no dejes creada una cuenta inaccesible.

Al primer arranque, crea un administrador desde `ADMIN_NAME`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`, sin sobrescribir sus credenciales en arranques posteriores. Incluye:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/change-password`
- `GET /api/users`
- `POST /api/users`
- `PATCH /api/users/{id}`

La interfaz de configuración debe permitir registrar usuarios, cambiar perfil, activar/desactivar la cuenta y alternar cada permiso; los cambios se aplican inmediatamente.

### 3. Catálogo de categorías

Las categorías y subcategorías deben persistir en la base de datos, tener código interno único, nombre y estado activo. Genera el código automáticamente desde el nombre: mayúsculas, sin tildes, palabras separadas por guion bajo, admitiendo nombres escritos con tildes y ñ. Si el código ya existe, agrega un sufijo incremental.

Permite listar, crear, activar y desactivar categorías y subcategorías. Los usuarios comunes solo ven opciones activas; usuarios con configuración pueden incluir las inactivas.

Precarga:

- Administración: Equipo, Insumos, Servicios / Proveedor.
- Mantenimiento: Equipo, Insumos, Servicios / Proveedor.
- Extraordinario: Equipo.
- Legal: Consultorías, Trámites, Demandas.
- Piscina: Equipo, Insumos, Servicios / Proveedor.
- Gimnasio: Equipo, Insumos, Servicios / Proveedor.
- Cancha de squash: Equipo, Insumos, Servicios / Proveedor.

Al crear una categoría, crea por defecto un flujo Tesorero → Presidente, usando los correos configurados por entorno. Expón el catálogo bajo `/api/categories`.

### 4. Solicitudes de gasto

Una solicitud debe contener:

- ID interno numérico.
- `request_id` UUID estable y único.
- `flow_id` UUID único para la versión vigente del flujo; debe cambiar al reenviar una corrección.
- ID legible único con formato `PPP-AAAA-###########`, con secuencia anual independiente por categoría y generación atómica para soportar concurrencia. Usa prefijos como `ADM`, `MAN`, `EXT`, `LEG`, `PIS`, `GYM` y `SQU`; para categorías nuevas deriva tres caracteres.
- Título.
- Descripción o justificación.
- Categoría y subcategoría.
- Monto decimal positivo.
- Proveedor.
- URL opcional del producto o servicio.
- Correo del solicitante obtenido del usuario autenticado, nunca aceptado del cliente.
- Estado, fechas de auditoría y relaciones con aprobaciones y adjuntos.

Estados de solicitud:

- `SUBMITTED`
- `PENDING_APPROVAL`
- `APPROVED`
- `REJECTED`
- `NEEDS_REVISION`
- `CANCELLED`
- `CLOSED`

Para crear o reenviar una solicitud exige al menos un soporte: URL válida, cotización adjunta o ambos. Como el archivo se carga después de crear el registro, admite una bandera transitoria `quotation_pending` que no se persista; no inicies la aprobación hasta que el archivo haya sido guardado correctamente.

Acepta adjuntos PDF, JPG, PNG y WEBP, máximo 10 MB por archivo. Impide path traversal, genera un nombre almacenado aleatorio y controla la autorización al descargar. Registra `document_type`, al menos `QUOTATION`, `PURCHASE_ORDER` e `INVOICE`.

Incluye operaciones para:

- Listar solicitudes según permisos.
- Crear una solicitud.
- Adjuntar y descargar soportes.
- Corregir y reenviar la misma solicitud sin crear otra fila: conserva `request_id` e ID legible, invalida enlaces anteriores, genera un nuevo `flow_id`, actualiza los campos y crea un flujo nuevo.
- Cancelar con un motivo obligatorio de 3 a 1000 caracteres. No se puede cancelar una solicitud cerrada, ya cancelada o rechazada. Al cancelar, expiran enlaces abiertos.
- Cerrar una solicitud, solo por administrador y únicamente si está aprobada. El cierre exige una factura con las mismas reglas de archivo y admite notas. La operación debe ser transaccional: si falla, revierte la base de datos y elimina archivos parciales.

Una solicitud cerrada no puede corregirse ni cancelarse. Protege cambios críticos contra carreras mediante bloqueo de fila o mecanismo equivalente.

### 5. Motor de aprobación

Las reglas de aprobación se almacenan en PostgreSQL y contienen categoría, monto mínimo, monto máximo opcional, correo del aprobador, nombre del rol, número de paso y estado activo.

Selecciona todas las reglas activas cuya categoría coincida y cuyo rango incluya el monto, ordenadas por paso ascendente. Si no existe una regla aplicable, no dejes una solicitud inconsistente: informa un error claro y revierte la creación o el inicio del flujo.

Precarga estas reglas:

- Administración de 0 a 500: Tesorero.
- Administración desde 500.01: Tesorero → Presidente.
- Mantenimiento: Tesorero → Presidente.
- Extraordinario: Presidente.
- Legal: Presidente.
- Piscina: Tesorero → Presidente.
- Gimnasio: Tesorero → Presidente.
- Cancha de squash: Tesorero → Presidente.

Los correos provienen de `TREASURER_EMAIL` y `PRESIDENT_EMAIL`. Permite consultar reglas a usuarios autenticados y crear reglas a administradores.

Cada paso de aprobación debe guardar el `flow_id`, aprobador, rol, orden, token aleatorio de alta entropía, estado, comentario y fecha de decisión. Estados:

- `WAITING`: espera su turno.
- `PENDING`: paso activo.
- `APPROVED`.
- `REJECTED`.
- `REVISION_REQUESTED`.
- `EXPIRED`.

El flujo es estrictamente secuencial:

1. Al iniciar, solo el primer paso queda `PENDING`; el resto queda `WAITING`.
2. Al aprobar, activa el siguiente paso y envíale correo.
3. Si ya no hay más pasos, marca la solicitud `APPROVED` y notifica al solicitante.
4. Al rechazar, marca la solicitud `REJECTED`, expira pasos abiertos y notifica al solicitante.
5. Al enviar a revisión, exige comentario mínimo de tres caracteres, marca `NEEDS_REVISION`, expira pasos abiertos y notifica al solicitante indicando la corrección solicitada.
6. Un token usado, expirado o perteneciente a un flujo cancelado, cerrado, rechazado o sustituido jamás se puede reutilizar.
7. Una decisión debe ser idempotentemente segura: ante doble clic o solicitudes concurrentes solo una puede procesarse.

El enlace de aprobación requiere sesión. Solo puede abrirlo y decidirlo un administrador o un usuario activo con `can_approve` cuyo correo normalizado coincida con el aprobador del paso.

### 6. Correos

Envía correos HTML con alternativa en texto plano. El correo de aprobación debe mostrar ID legible, `flow_id`, título, categoría/subcategoría, proveedor, monto, solicitante, descripción y soportes, e incluir botones para Aprobar, Rechazar, Enviar a revisión y Ver detalle. Los botones abren la página de detalle con una indicación de la acción pretendida, pero nunca ejecutan la decisión directamente; el usuario debe autenticarse, revisar y confirmar.

Notifica al solicitante cuando la solicitud sea aprobada, rechazada o enviada a revisión. Si requiere revisión, incluye el comentario y un enlace al sistema. Un fallo de correo no debe revertir una decisión ya guardada: registra el error y conserva el estado consistente.

### 7. Interfaz de usuario

Diseña una interfaz sobria, moderna y responsive, con fondo gris muy claro, tarjetas blancas redondeadas, sombras discretas, tipografía de sistema/Inter, encabezado azul carbón casi negro y estados con colores accesibles. Evita una estética genérica recargada.

Pantallas y componentes:

1. **Inicio de sesión:** marca “PH”, título “Iniciar sesión”, correo, contraseña y errores claros.
2. **Encabezado autenticado:** “PH · Gestión de Gastos”, nombre y perfil del usuario, navegación a Solicitudes, Permisos y Categorías según permisos, y Salir.
3. **Formulario de solicitud:** título, categoría, subcategoría dependiente, monto, proveedor, URL, cotización y descripción. Muestra claramente que se exige al menos un soporte. Sirve también para corregir y reenviar, avisando que conserva la solicitud pero reemplaza el flujo y expira los enlaces anteriores.
4. **Seguimiento:** tabla con ID, solicitud/proveedor, categoría/subcategoría, soportes, solicitante, monto, estado, `flow_id` y pasos de aprobación. Incluye búsqueda por identificadores, título, proveedor, solicitante o flujo; filtros por estado y categoría; contador de resultados y limpiar filtros.
5. **Acciones por fila:** Corregir / reenviar, Cancelar solicitud y, para administradores sobre aprobadas, Cerrar aprobación.
6. **Cierre:** solicita obligatoriamente una factura, más notas opcionales.
7. **Permisos:** alta de usuarios y tabla editable de perfil, permisos y estado.
8. **Categorías:** alta de categoría, tarjetas por categoría, activar/desactivar, ver subcategorías y agregar/activar/desactivar subcategorías.
9. **Aprobación por token:** muestra todo el detalle, monto destacado, soportes, responsable autenticado, comentario y botones Rechazar, Enviar a revisión y Aprobar. Tras decidir, presenta un resultado visual inequívoco y deshabilita nuevas decisiones.
10. **Consulta de facturas:** pantalla independiente con búsqueda por nombre del archivo, ID/UUID de solicitud, flujo, título, proveedor o solicitante; filtro por categoría; cantidad de resultados y descarga autorizada. Muestra archivo, fecha de carga, solicitud, proveedor, categoría, monto, solicitante, fecha/responsable del cierre. Los solicitantes solo pueden encontrar facturas de sus propias solicitudes.

En móvil, apila formularios, filtros, panel de cierre y detalles. Mantén las tablas desplazables horizontalmente cuando sea necesario. Muestra estados con etiquetas visuales y mensajes de carga, vacío, éxito y error.

### 8. Modelo de datos mínimo

Crea tablas equivalentes a:

- `users`
- `expense_categories`
- `expense_subcategories`
- `category_counters`
- `expenses`
- `expense_attachments`
- `approval_rules`
- `approvals`
- `approval_step_events` como historial append-only de todas las transiciones.

La tabla de eventos debe estar preparada para CDC/streaming a un datalake. Incluye
un cursor monotónico `event_sequence`, un `event_id` UUID para deduplicación,
`occurred_at` con zona horaria asignado por PostgreSQL, `request_id`, `display_id`,
`flow_id`, `approval_id`, `step`, aprobador/rol, estado anterior y nuevo, estado de
la solicitud, actor, comentario, tipo de evento y un `payload` JSON versionado con
el snapshot completo. Registra al menos creación, activación, aprobación, rechazo,
solicitud de revisión y expiración. El evento y el cambio de estado deben guardarse
en la misma transacción; nunca actualices ni borres eventos ya emitidos.

Define claves foráneas, índices y restricciones únicas para correos, códigos, UUID, ID legible, tokens y nombres almacenados. Usa borrado en cascada solo donde corresponda. Evita N+1 al listar solicitudes con aprobaciones y adjuntos.

### 9. Variables de entorno

Documenta como mínimo:

`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`, `TOKEN_EXPIRE_MINUTES`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `TREASURER_EMAIL`, `PRESIDENT_EMAIL`, `EMAIL_MODE`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `PUBLIC_URL` y `UPLOAD_DIR`.

### 10. Calidad y criterios de aceptación

- Incluye migraciones reproducibles; no dependas de modificaciones manuales a la base de datos.
- Agrega pruebas automatizadas del motor de aprobación, permisos, rangos de monto, doble decisión, corrección/expiración, archivos, cancelación y cierre.
- Valida tanto en frontend como en backend; el backend es la autoridad final.
- Usa transacciones para operaciones compuestas y respuestas HTTP adecuadas (`401`, `403`, `404`, `409`, `410`, `413`, `415`, `422`).
- No expongas hashes, tokens de otros pasos, rutas internas ni secretos.
- Proporciona README con arquitectura, configuración, arranque, credenciales bootstrap, modo de correo, endpoints y comandos de prueba.
- Verifica al final: compilación del frontend, pruebas del backend, creación limpia de contenedores, persistencia tras reinicio y flujo completo crear → aprobar/revisar/rechazar → reenviar → aprobar → cerrar.
- Entrega código mantenible y modular. No declares el trabajo terminado mientras alguna pantalla use datos falsos o alguna operación crítica carezca de persistencia/autorización.

Si debes tomar decisiones no especificadas, elige la opción más simple que preserve seguridad, trazabilidad y consistencia, documéntala y continúa sin reducir el alcance funcional.

## FIN DEL PROMPT
