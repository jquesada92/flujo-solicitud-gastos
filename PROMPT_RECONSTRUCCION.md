# Prompt maestro de reconstrucción

Construye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar y documentar gastos con evidencia verificable de cada decisión.

Este documento es la única fuente funcional y técnica para reconstruir la aplicación. Implementa tanto la interfaz como el backend, la base de datos, la seguridad, el almacenamiento, el correo, las pruebas y la configuración de despliegue.

## 1. Propósito

El sistema debe convertir cada proceso de gasto en un expediente digital, trazable y auditable. Debe permitir demostrar:

- quién presentó la solicitud y cuándo;
- qué productos, servicios y proveedores fueron considerados;
- qué cotizaciones y documentos estaban disponibles;
- quién votó, aprobó, rechazó o solicitó una corrección;
- la fecha, hora, resultado y comentario de cada decisión;
- cuál fue la opción seleccionada;
- qué factura corresponde al gasto ejecutado;
- cómo evolucionó el expediente sin alterar su historial.

La aplicación debe facilitar auditorías y consultas históricas, reducir la dependencia de documentos físicos y ayudar a resolver diferencias mediante evidencia objetiva.

## 2. Alcance y exclusiones

Incluye:

- usuarios, perfiles, permisos y cargos;
- organigrama de junta directiva;
- solicitudes simples y de múltiples cotizaciones;
- votación de cotizaciones;
- políticas y pasos de aprobación;
- correcciones, reenvíos y cancelaciones;
- facturas y cierre del flujo;
- categorías y subcategorías;
- documentos privados;
- notificaciones por correo;
- auditoría inmutable;
- tablero, consultas y filtros.

No construyas ninguna funcionalidad de apartamentos o propiedad inmobiliaria. Esto implica no crear:

- tablas, modelos o catálogos de apartamentos;
- relaciones entre usuarios y unidades;
- endpoints o pantallas de apartamentos;
- tipos de propietario, copropietario, residente o arrendatario;
- validaciones que exijan una unidad a un usuario o miembro de junta;
- eventos de auditoría relacionados con apartamentos.

La participación en el sistema depende únicamente de perfiles, cargos y permisos.

## 3. Arquitectura

- Frontend: React con Vite, desplegado en Vercel.
- Backend: FastAPI con SQLAlchemy, desplegado como contenedor Docker en Render.
- Base de datos: PostgreSQL compatible con Neon.
- Autenticación: JWT con vencimiento, inactividad y revocación.
- Correo de producción: API HTTPS de Brevo.
- Documentos: disco privado persistente de Render.
- Pruebas: `pytest` para backend y compilación de producción para frontend.

Separa modelos, esquemas, servicios, rutas, seguridad, configuración, migraciones y pruebas. El frontend nunca accede directamente a PostgreSQL ni al disco. Toda lectura o modificación pasa por el backend.

## 4. Usuarios, perfiles y permisos

### Tipos administrativos

- **Administrador del sistema:** cuenta técnica inicial creada mediante `ADMIN_NAME`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`. No representa al administrador operativo de la propiedad horizontal.
- **Administrador de la PH:** usuario operativo creado desde el portal y asociado a un perfil.
- **Miembros de junta:** presidente, vicepresidente, tesorero, vocal u otros cargos configurados.
- **Otros usuarios:** acceso definido por sus perfiles y permisos.

No uses correos fijos como `TREASURER_EMAIL` o `PRESIDENT_EMAIL`. Los cargos se asignan desde el portal.

### Datos de la persona

- cédula;
- primer nombre;
- segundo nombre opcional;
- primer apellido;
- segundo apellido opcional;
- correo;
- teléfono opcional;
- perfil o cargo;
- estado activo o inactivo.

Normaliza la cédula eliminando espacios externos y unificando mayúsculas. El correo y la cédula deben ser únicos mediante validación del servicio y restricciones de PostgreSQL. Devuelve HTTP 409 con mensajes accionables ante duplicados.

Permite buscar por cédula, nombre, apellido o correo. Muestra una sola fila por persona. Permite crear, editar, activar, inactivar y modificar usuarios en lote sin exigir datos inmobiliarios.

### Perfiles

Cada perfil puede definir:

- permiso para solicitar;
- permiso para aprobar;
- permiso para consultar;
- permiso para configurar;
- estado activo;
- límite opcional de usuarios activos.

Impide superar el límite en el servicio y en PostgreSQL. No permitas asignación masiva de permisos mediante campos no autorizados.

### Organigrama

Permite asignar presidente, vicepresidente, tesorero, vocales y cargos adicionales a personas activas. Una persona no puede ocupar dos cargos simultáneos dentro del mismo organigrama.

## 5. Contraseñas y sesiones

Los usuarios creados desde el portal reciben por correo una contraseña temporal y deben cambiarla antes de utilizar el resto de la aplicación. Permite al administrador regenerarla. La regeneración invalida la contraseña anterior y todas las sesiones existentes. La contraseña del administrador técnico no puede regenerarse desde el portal.

Implementa:

- vencimiento absoluto mediante `TOKEN_EXPIRE_MINUTES=480`;
- inactividad humana mediante `SESSION_IDLE_MINUTES=30`;
- versión de sesión por usuario para revocar JWT;
- `POST /api/auth/activity` para registrar actividad humana real;
- límite de cinco intentos fallidos dentro de quince minutos;
- mensajes de acceso fallido que no revelen si el correo existe.

Clics, teclado, navegación y acciones reales pueden renovar la actividad. Polling, refrescos automáticos y solicitudes en segundo plano no deben extender la sesión.

## 6. Solicitudes de gasto

Cada solicitud debe conservar:

- identificador interno inmutable;
- identificador visible;
- identificador del flujo;
- referencia a la versión anterior cuando sea una corrección;
- solicitante;
- título y descripción o justificación;
- categoría y subcategoría opcional;
- urgencia `LOW`, `NORMAL`, `HIGH` o `CRITICAL`;
- tipo `SIMPLE` o `MULTI_QUOTE`;
- estado;
- documentos;
- historial, comentarios y decisiones;
- fechas de creación y última actividad relevante.

Usa los estados:

- `QUOTATION_VOTING`;
- `SUBMITTED`;
- `PENDING_APPROVAL`;
- `APPROVED`;
- `REJECTED`;
- `CANCELLED`;
- `CLOSED`;
- `NEEDS_REVISION`.

### Solicitud simple

Exige proveedor, monto mayor que cero y al menos una cotización mediante URL o archivo.

### Múltiples cotizaciones

Exige entre dos y diez opciones. Cada opción contiene proveedor, monto, URL o archivo propio y notas opcionales. No permitas enlaces duplicados.

## 7. Votación de cotizaciones

Cuando una solicitud tenga múltiples cotizaciones:

- convoca a los perfiles configurados de la junta;
- permite votar desde una sesión autorizada o un enlace firmado enviado por correo;
- permite un voto vigente por persona;
- registra cada cambio de voto como evento de solo anexado;
- muestra opciones, documentos, conteo y participantes según permisos;
- define claramente el comportamiento ante empates;
- selecciona una opción ganadora válida antes de iniciar la aprobación.

Protege los enlaces y archivos de cada opción. Una opción sugerida en una URL nunca debe votarse automáticamente: el usuario debe revisar y confirmar.

## 8. Aprobaciones

Implementa políticas configurables por categoría, rango de monto y perfiles aprobadores, con uno o varios pasos. Cada política contiene nombre, categoría o alcance global, monto mínimo, monto máximo opcional, modo, perfiles y estado.

Las decisiones admitidas son:

- aprobar;
- rechazar;
- solicitar corrección.

Permite decidir desde una sesión autorizada o un enlace firmado. Una acción sugerida en la URL requiere confirmación explícita.

Las aprobaciones pendientes no expiran solamente por el paso del tiempo. Se invalidan al responderse o cuando el flujo es cancelado, rechazado, cerrado o reemplazado. `APPROVAL_LINK_HOURS` no forma parte del comportamiento requerido.

## 9. Corrección, reenvío y cancelación

Una solicitud de corrección debe incluir comentario. El solicitante puede crear una versión nueva precargada y vinculada con la original. No sobrescribas ni elimines el expediente anterior.

Permite cancelar una solicitud vigente únicamente con un motivo. Registra responsable, fecha y hora. Invalida acciones pendientes incompatibles con la cancelación.

## 10. Facturas y cierre

Después de aprobar una solicitud, permite cargar una factura y cerrar el flujo con notas. Incluye una consulta específica de facturas con búsqueda por solicitud, título, proveedor o solicitante y filtro por categoría.

La sustitución de una factura requiere:

- archivo nuevo válido;
- motivo obligatorio;
- autorización suficiente;
- evento inmutable con referencia al archivo anterior y al nuevo;
- responsable, fecha y hora.

Conserva la documentación histórica aunque un archivo deje de ser la versión vigente.

## 11. Actas y documentos relacionados

Permite adjuntar documentos adicionales relacionados con el expediente, incluidas actas que respalden una decisión. Cada documento debe registrar tipo, nombre original, responsable y fecha de carga.

Un acta puede incluir fecha de reunión y descripción opcional. Define autorización para cargar, consultar, reemplazar o descargar. Si se reemplaza, conserva la versión anterior y registra el motivo. Los documentos históricos no se eliminan silenciosamente.

## 12. Archivos privados

Admite PDF, JPEG, PNG y WEBP. Valida:

- extensión permitida;
- MIME declarado;
- firma real del contenido;
- tamaño individual;
- cuota total del almacenamiento.

Usa nombres internos impredecibles. Conserva el nombre original solo como metadato. El directorio no debe ser público y cada descarga requiere autorización del backend.

Configuración inicial:

```env
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_STORAGE_MB=450
```

Reiniciar PostgreSQL no elimina el disco de Render. Borrar archivos requiere un procedimiento separado y explícito.

## 13. Correo

Centraliza el envío en un servicio. En producción usa la API HTTPS de Brevo:

```env
EMAIL_MODE=brevo
BREVO_API_KEY=< CLAVE API DE BREVO >
BREVO_SENDER_NAME=< NOMBRE VISIBLE DEL REMITENTE >
EMAIL_FROM=< CORREO VERIFICADO EN BREVO >
```

Envía:

- invitaciones con contraseña temporal;
- solicitudes de votación;
- solicitudes de aprobación;
- notificaciones de aprobación, rechazo, corrección, cancelación y cierre.

Configura tiempos de espera y registra errores sin secretos. SMTP puede existir para desarrollo, pero no es obligatorio en Render.

## 14. Auditoría

Mantén eventos inmutables para:

- solicitudes y transiciones;
- pasos y decisiones de aprobación;
- votos y cambios de voto;
- facturas y sustituciones;
- actas y otros documentos versionados;
- usuarios y permisos;
- perfiles;
- organigrama;
- políticas de aprobación.

Cada evento incluye secuencia, identificador, tipo, actor, fecha, hora, entidad, campos modificados, estado anterior y posterior cuando corresponda y comentario o motivo.

Los eventos son de solo anexado. Instala protecciones en PostgreSQL que impidan actualizarlos o eliminarlos.

## 15. Límites de solicitudes

Aplica contadores separados por usuario y minuto:

```env
USER_READ_RATE_LIMIT=120
USER_WRITE_RATE_LIMIT=30
USER_UPLOAD_RATE_LIMIT=6
USER_SENSITIVE_RATE_LIMIT=10
```

Devuelve HTTP 429 al superar el límite. Diseña el servicio para poder migrar los contadores a Redis si se ejecutan varias instancias.

## 16. Seguridad y privacidad

Incluye:

- validación estricta de configuración en producción;
- `SECRET_KEY` y `ANALYTICS_HASH_KEY` largas, aleatorias y diferentes;
- hashing fuerte de contraseñas;
- CORS limitado a orígenes HTTPS autorizados;
- CSP, HSTS y encabezados de seguridad;
- ORM y consultas parametrizadas;
- errores sin secretos, trazas ni SQL interno;
- identificadores analíticos seudónimos;
- protección contra asignación masiva;
- dependencias fijadas y análisis de seguridad en CI;
- autorización en el backend para cada operación.

Nunca incluyas secretos reales. Si una credencial fue publicada, debe rotarse.

## 17. Navegación y componentes globales

### `AppShell`

Muestra encabezado, usuario, navegación responsive, cierre de sesión y avisos globales. Incluye Inicio, Solicitudes y, según permisos, Facturas, Auditoría, Personas, Organigrama, Categorías y Reglas.

### Componentes transversales

- `PageHeader`: título, descripción y acciones.
- `PermissionGate`: controla presentación según permisos sin sustituir al backend.
- `Notice`: información, éxito, advertencia y error.
- `ConfirmDialog`: confirmación accesible de acciones sensibles.
- `LoadingState`, `EmptyState` y `ErrorState`.
- `FilterBar`: búsqueda, filtros, contador y limpieza.
- `DataTable`: tabla accesible con adaptación móvil.
- `UnsavedChangesGuard`: evita perder cambios sin confirmar.
- `SessionManager`: registra únicamente actividad humana real.
- `DocumentUploader` y `AttachmentViewer`.
- `StatusBadge` y `UrgencyBadge` con texto además de color.

## 18. Pantallas

### Inicio de sesión

Correo, contraseña, opción de mostrar contraseña, procesamiento y mensajes genéricos de error o bloqueo. Redirige al cambio obligatorio o al tablero.

### Cambio de contraseña

Contraseña actual, nueva, confirmación y requisitos visibles. Impide acceder al resto hasta completarlo.

### Tablero

Tarjetas de pendientes, votaciones, aprobadas, rechazadas, correcciones y cerradas; solicitudes recientes; acciones pendientes del usuario y acceso rápido para crear una solicitud.

### Solicitudes

Incluye búsqueda, filtros por estado, categoría y urgencia, contador y limpieza. La tabla muestra identificador, fechas, título, categoría, proveedor u opciones, monto, urgencia, estado y acciones. En móvil usa tarjetas legibles.

### Formulario de solicitud

Implementa campos comunes y formularios condicionales para solicitud simple o múltiples cotizaciones. Muestra validación junto al campo, progreso de archivos, prevención de doble envío y protección de cambios sin guardar.

### Detalle de solicitud

Reúne resumen, documentos, alternativas, votos, aprobaciones y línea de tiempo. Según estado y permisos permite votar, aprobar, rechazar, solicitar corrección, reenviar, cancelar, registrar factura, sustituir factura o cerrar.

### Votación

Compara opciones mostrando proveedor, monto, notas, URL, archivos, votos y acción de confirmación. Explica el estado de participación y los empates.

### Corrección

Muestra el comentario recibido, datos precargados, documentos anteriores y nuevos, y confirmación de reenvío.

### Facturas

Búsqueda, filtro por categoría, contador, listado, visualización autorizada y corrección auditada.

### Personas

Formulario, búsqueda, listado, edición, activación, inactivación y regeneración de contraseña. No incluye datos inmobiliarios.

### Organigrama y perfiles

Muestra cargos y ocupantes. Permite asignar personas y editar permisos, estado y límites de cada perfil.

### Categorías y subcategorías

Crear, buscar, renombrar, activar e inactivar categorías y subcategorías. Inactivar no altera solicitudes históricas. Protege cambios sin guardar.

### Reglas de aprobación

Crear, editar, activar, inactivar y eliminar políticas cuando sea seguro. Detecta rangos inválidos, perfiles vacíos y configuraciones ambiguas.

### Auditoría

Búsqueda por solicitud, proveedor, usuario, aprobador o monto; filtros por evento, estado y fechas; tabla o línea de tiempo; detalle de estados anterior y posterior. No permite editar ni eliminar eventos.

### Acciones desde correo

Pantallas separadas para aprobación y votación. Contemplan enlace pendiente, autenticación requerida, respuesta registrada, flujo incompatible, confirmación exitosa y error seguro.

## 19. Comportamiento de interfaz

- Responsive para escritorio, tableta y móvil.
- Español claro y consistente.
- Fechas usando `VITE_TIME_ZONE`.
- Errores junto al campo correspondiente.
- Estados de carga, vacío, éxito y error en cada consulta.
- Prevención de doble envío.
- Conservación de datos ante errores recuperables.
- Confirmación de acciones sensibles.
- Navegación por teclado, foco visible, etiquetas y contraste accesible.
- Los permisos determinan la navegación, pero el backend es la autoridad final.

## 20. Variables de despliegue

### Render

```env
DATABASE_URL=< URL PRIVADA DE NEON >
PUBLIC_URL=< URL HTTPS DEL FRONTEND EN VERCEL >
CORS_ALLOWED_ORIGINS=< URL HTTPS DEL FRONTEND EN VERCEL >
SECRET_KEY=< SECRETO ALEATORIO LARGO >
ANALYTICS_HASH_KEY=< OTRO SECRETO ALEATORIO LARGO >

TOKEN_EXPIRE_MINUTES=480
SESSION_IDLE_MINUTES=30
USER_READ_RATE_LIMIT=120
USER_WRITE_RATE_LIMIT=30
USER_UPLOAD_RATE_LIMIT=6
USER_SENSITIVE_RATE_LIMIT=10
APP_TIME_ZONE=America/Panama

EMAIL_MODE=brevo
BREVO_API_KEY=< CLAVE API DE BREVO >
BREVO_SENDER_NAME=< NOMBRE DEL REMITENTE >
EMAIL_FROM=< CORREO VERIFICADO EN BREVO >

ADMIN_NAME=Administrador del sistema
ADMIN_EMAIL=< CORREO DEL ADMINISTRADOR TECNICO >
ADMIN_PASSWORD=< CONTRASENA SEGURA >

UPLOAD_DIR=/app/uploads
MAX_UPLOAD_STORAGE_MB=450
```

Render proporciona `RENDER=true`; `ENVIRONMENT=production` puede añadirse explícitamente. No uses `APPROVAL_LINK_HOURS` porque el flujo no expira aprobaciones por horas.

### Vercel

```env
VITE_API_URL=< URL HTTPS DEL BACKEND EN RENDER >
VITE_TIME_ZONE=America/Panama
```

Las variables `VITE_*` son visibles en el navegador y no pueden contener secretos. Cambiarlas exige recompilar y desplegar nuevamente el frontend.

## 21. Base de datos y despliegue

Usa migraciones versionadas y desplegables por separado. No dependas de cambios estructurales extensos durante el arranque. Las semillas mínimas crean únicamente el administrador técnico y los perfiles indispensables.

Para reiniciar Neon:

1. Crear una rama de respaldo.
2. Detener o aislar el backend.
3. Desplegar el código actualizado.
4. Confirmar la rama y vaciar el esquema correcto.
5. Ejecutar migraciones y semillas mínimas.
6. Verificar el administrador técnico.
7. Configurar usuarios, junta, perfiles, categorías y políticas desde el portal.
8. Ejecutar pruebas de integridad.

No termines conexiones a ciegas. Identifica PID, usuario, estado, consulta y antigüedad.

## 22. Criterios de aceptación

Demuestra mediante pruebas que:

- producción rechaza configuración insegura;
- no existen modelos, rutas, campos ni pantallas de apartamentos o propiedad;
- correo y cédula duplicados devuelven conflicto;
- la búsqueda de personas funciona;
- cargos y límites de perfiles se respetan;
- un usuario nuevo debe cambiar su contraseña temporal;
- regenerar la contraseña revoca la anterior y las sesiones;
- la sesión expira tras 30 minutos sin actividad humana;
- el polling no renueva la sesión y la actividad válida sí;
- los límites devuelven HTTP 429;
- los permisos se validan en backend;
- archivos inválidos se rechazan por contenido;
- documentos privados requieren autorización;
- los eventos históricos no pueden alterarse;
- una solicitud simple exige proveedor, monto y soporte;
- múltiples cotizaciones exige al menos dos opciones con soporte;
- la votación funciona desde sesión y enlace firmado;
- cada cambio de voto queda auditado;
- aprobar, rechazar y solicitar corrección funciona;
- corregir y reenviar conserva el vínculo histórico;
- cancelar exige motivo;
- registrar, consultar y sustituir facturas conserva auditoría;
- actas y documentos relacionados pueden archivarse y consultarse;
- categorías y subcategorías no rompen expedientes históricos;
- Brevo envía desde un remitente verificado;
- todas las pantallas tienen carga, vacío, éxito y error;
- la interfaz funciona en escritorio y móvil;
- `pytest` finaliza correctamente;
- `npm run build` compila el frontend.

Entrega archivos `.env.example` sin secretos, migraciones, pruebas, instrucciones de Render/Vercel/Neon y un procedimiento de recuperación con respaldo antes de borrar datos.
