# Prompt maestro actualizado · Sistema de gestión de gastos

Copiar desde **INICIO DEL PROMPT** hasta **FIN DEL PROMPT**. Este documento describe el MVP funcional completo y su arquitectura actual, sin secretos ni datos reales.

---

## INICIO DEL PROMPT

Actúa como arquitecto y desarrollador full-stack senior. Construye una aplicación web segura, responsive y productiva llamada **PH · Gestión de Gastos**, reutilizable posteriormente en empresas y hoteles. No entregues una maqueta: implementa frontend, API, persistencia, autenticación, autorización, archivos, correos, auditoría y pruebas.

Todo texto visible debe estar en español. Los códigos internos nunca se muestran en la interfaz: presenta descriptores legibles. Maneja importes con `Decimal`, dos decimales y nunca con punto flotante.

### 1. Arquitectura y ambientes

- Monorepo con `frontend/` y `backend/`; no crear un repositorio separado para la base de datos.
- Frontend: React con Vite, SPA responsive, servido por Nginx en contenedor.
- Backend: Python, FastAPI, Pydantic y SQLAlchemy 2.
- Base de datos: PostgreSQL 16.
- Autenticación: JWT Bearer con expiración configurable y secreto distinto por ambiente.
- Contraseñas: hash seguro con salt; nunca almacenar ni registrar texto plano.
- Infraestructura local: Docker Compose con frontend, backend y PostgreSQL.
- Producción: Neon PostgreSQL, backend Docker en Render y frontend en Vercel.
- CI/CD: GitHub y GitHub Actions; los pushes a `main` ejecutan pruebas y despliegue.
- Ambientes:
  - `local`: todo local.
  - `preview`: frontend/backend local accesible mediante Cloudflare Quick Tunnel, capturando su URL dinámica.
  - `prod`: Neon + Render + Vercel.
- Vite usa `VITE_API_URL`; nunca expongas secretos en variables `VITE_*`.
- Incluye `GET /api/health`. Deshabilita OpenAPI público en producción.
- Integra Vercel Web Analytics con `@vercel/analytics/react`; excluye rutas `/approve/...` para no enviar tokens.

### 2. Personas, privacidad y acceso

Una persona contiene:

- ID numérico interno y `analytics_id` hash estable, no reversible y único.
- Cédula o pasaporte único.
- Primer nombre, segundo nombre opcional, primer apellido y segundo apellido opcional.
- Nombre completo concatenado para tablas.
- Teléfono, correo único normalizado, fecha de creación, fecha de actualización y estado activo.
- Tipo: Propietario, Co-propietario, Conserje, Administrador operativo o Administrador del sistema.
- Cargo y permisos derivados del perfil de acceso.

Reglas PII:

- Solo el Administrador operativo y el Administrador del sistema pueden ver cédula/pasaporte, teléfono y correo completos.
- Para otros usuarios, enmascara o elimina PII en el backend, no solo en React.
- Auditoría, solicitudes y facturas muestran nombres completos, nunca correos.
- El hash analítico permite análisis posteriores sin usar identificadores personales.

Permisos: solicitar, aprobar, consultar y configurar. Un usuario inactivo no inicia sesión ni usa tokens anteriores. El Administrador del sistema tiene acceso total. El Administrador operativo puede crear/modificar personas y apartamentos, solicitar y consultar, pero no aprobar ni configurar reglas/perfiles. Conserjes solicitan y consultan. Propietarios consultan por defecto.

La pantalla **Personas** permite crear o modificar en el mismo formulario. Para modificar, realiza una consulta al servidor por nombres, apellidos o cédula/pasaporte, con resultados limitados; no cargues 130 usuarios en pantalla. Valida unicidad de correo e identificación y audita cada cambio.

Al crear una cuenta, genera una contraseña temporal y exige cambiarla al primer ingreso. Incluye regeneración de contraseña administrada. Implementa también recuperación segura para el Administrador del sistema mediante token de un solo uso, hash almacenado, expiración de 15 minutos, respuesta no enumerable, rate limiting e invalidación de sesiones.

### 3. Apartamentos

Crea un maestro de apartamentos del piso 6 al 21, letras A a H. La relación persona–apartamento usa internamente la cédula/pasaporte como clave de negocio y claves foráneas técnicas para integridad. Una persona puede tener varios apartamentos. Cada relación indica Propietario o Co-propietario. Cada apartamento tiene bandera de alquiler.

La pantalla **Apartamentos** permite buscar por unidad o propietario, editar propietario, co-propietario y alquiler, acumular cambios, resaltar filas modificadas y confirmar mediante un botón **Guardar cambios** con contador. No sobrescribas asignaciones sin validación de concurrencia.

### 4. Organigrama y perfiles

Usa el nombre **Organigrama**, no Junta Directiva. En el MVP no implementes jerarquías. Cargos iniciales: Presidente, Vicepresidente, Tesorero, Vocal, Administrador, Conserje, Mantenimiento y Propietario.

- Los cargos se asignan desde Organigrama.
- Los miembros autorizados consultan en modo lectura; solo el Administrador del sistema cambia cargos y perfiles.
- La tabla de asignación muestra usuario, apartamentos, cargo, fechas, estado y seguridad; no muestres checkboxes informativos de permisos.
- **Perfiles de acceso** permite definir permisos predeterminados, estado y límite opcional de personas.
- Nunca muestres códigos como `OWNER`, `ADMINISTRATOR`, `PENDING_APPROVAL` o códigos de categoría; usa descriptores.

### 5. Categorías y subcategorías

Persisten en PostgreSQL y son administrables desde GUI. Precarga Administración, Mantenimiento, Extraordinario, Legal, Piscina, Gimnasio y Cancha de squash con sus subcategorías conocidas. Genera códigos internos automáticos, únicos, normalizados y nunca visibles.

La pantalla muestra una sola categoría a la vez. Un desplegable permite navegar entre categorías; indica cuáles están inactivas. Permite renombrar, activar/desactivar y gestionar subcategorías. Al intentar cambiar con ediciones pendientes, ofrece **Guardar y continuar**, **Desechar y continuar** o **Cancelar**.

### 6. Solicitudes y documentos

Una solicitud contiene ID interno, `request_id` UUID, `flow_id` UUID, ID legible `PPP-AAAA-###########`, título, descripción, categoría, subcategoría, monto, proveedor, URL opcional, solicitante autenticado, `requester_analytics_id`, estado y fechas.

Estados internos: enviada, pendiente de aprobación, aprobada, rechazada, requiere corrección, cancelada y cerrada. Muéstralos siempre traducidos.

- Exige soporte inicial: URL de producto/servicio, cotización o ambos.
- Soportes no incluyen factura.
- La factura es un documento de cierre posterior a la aprobación final.
- Acepta PDF, JPG, PNG y WEBP, máximo 10 MB, nombre interno aleatorio, protección de ruta y autorización de descarga.
- Incluye visor integrado de PDF/imágenes y descarga.
- Corregir/reenvíar conserva la solicitud, genera nuevo flujo e invalida enlaces anteriores.
- Cancelar exige motivo.
- Solo el Administrador del sistema cierra una solicitud aprobada y adjunta factura.
- Lista solicitudes abiertas y cerradas durante los últimos 7 días; no cargues histórico completo.
- Evita desbordes: tablas con ancho controlado, elipsis, tooltips, scroll interno y encabezado fijo.

### 7. Aprobaciones

Las reglas viven en PostgreSQL y son configurables desde GUI por categoría, rango de monto, modalidad y perfiles aprobadores. La regla predeterminada exige aprobación de todos los miembros activos del Organigrama directivo.

- El solicitante nunca puede aprobar su propia solicitud.
- No se crea ni envía su paso de aprobación.
- Si el solicitante pertenece al Organigrama, aprobaciones requeridas = miembros activos menos uno.
- En modalidad `ALL`, todos los demás miembros tienen pasos pendientes; la solicitud se aprueba cuando todos aprueban.
- Rechazo o solicitud de corrección invalida pasos abiertos según la política.
- Tokens son aleatorios, de alta entropía, de un solo uso y requieren sesión.
- Usa bloqueo de fila/idempotencia para doble clic y concurrencia.

Mantén `approval_step_events`: es append-only y prepara el sistema para CDC futuro sin pérdida de datos. Guarda evento y cambio de estado en la misma transacción.

### 8. Auditoría y rendimiento

**Auditoría** está en el menú principal, no dentro de Configuración. Incluye flujos y cambios a personas, apartamentos, permisos, perfiles, categorías y reglas.

- Solo consulta los últimos 45 días.
- Paginación por cursor desde el servidor, 50 eventos por página.
- Búsqueda del lado del servidor por artículo, proveedor, creador, aprobador, modificador y monto.
- Muestra nombres completos en “Realizado por” y sujetos; nunca correos ni PII.
- Tablas con scroll interno y encabezados fijos para mantener la pantalla estable.
- La aplicación debe operar con menos de 0.5 GB de datos activos; aplica ventanas temporales, paginación, índices y políticas de almacenamiento.

### 9. Correo por ambiente

Implementa una interfaz de proveedor de correo con:

- `EMAIL_MODE=console` para local: registra mensajes sin enviarlos.
- `EMAIL_MODE=sendgrid` para producción: usa la API HTTPS de SendGrid por puerto 443, nunca SMTP en Render gratuito.
- `EMAIL_MODE=smtp` opcional para ambientes donde los puertos SMTP estén permitidos.

Variables de producción: `SENDGRID_API_KEY`, `EMAIL_FROM` verificado y `PUBLIC_URL`. La API key solo tiene permiso **Mail Send** y nunca entra al repositorio, frontend, logs ni respuestas. Usa timeout HTTP corto, manejo de errores estructurado y logs sin secretos.

Los correos incluyen versión HTML y texto plano: invitación, regeneración/recuperación, aprobación y estado final. Un fallo de notificación de flujo no revierte una decisión ya confirmada. Para alta de usuarios, registra el estado de entrega y permite reintentar la invitación de forma segura; evita peticiones bloqueadas durante minutos. Idealmente procesa notificaciones mediante cola/outbox.

### 10. Política global de cambios pendientes

Si hay cambios reales sin guardar, advierte antes de cambiar de pantalla, cerrar sesión, recargar o cerrar el navegador. No actives avisos por filtros o búsquedas. Los diálogos específicos pueden ofrecer guardar, desechar o cancelar. Esta política aplica a solicitudes, personas, apartamentos, cargos, perfiles, categorías, subcategorías y reglas.

### 11. Seguridad y datos

- Aplica autorización en backend; React nunca es la autoridad.
- Enmascara PII antes de serializar.
- CORS solo acepta orígenes configurados.
- Protege JWT, tokens, archivos, rate limits y validación de entradas.
- No expongas secretos, hashes, rutas internas ni tokens en Analytics.
- Incluye claves foráneas, restricciones únicas, índices e integridad transaccional.
- Eventos de auditoría son inmutables mediante reglas de base de datos.
- No elimines datos de prueba automáticamente; desactívalos o consérvalos cuando deban monitorearse. Cualquier limpieza destructiva debe ser explícita.

Tablas mínimas: usuarios, perfiles de acceso, apartamentos, relación usuario-apartamento, categorías, subcategorías, contadores, solicitudes, adjuntos, políticas de aprobación, aprobaciones, `approval_step_events` y eventos append-only para personas, apartamentos, perfiles, categorías y reglas.

### 12. Variables

Documenta sin valores reales:

`DATABASE_URL`, `SECRET_KEY`, `ANALYTICS_HASH_KEY`, `TOKEN_EXPIRE_MINUTES`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `PUBLIC_URL`, `CORS_ALLOWED_ORIGINS`, `EMAIL_MODE`, `SENDGRID_API_KEY`, `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD`, `UPLOAD_DIR`, `MAX_UPLOAD_STORAGE_MB` y `VITE_API_URL`.

### 13. Pruebas y aceptación

- Pruebas unitarias e integración para autenticación, permisos, PII, personas, apartamentos múltiples, catálogos, reglas, autoaprobación prohibida, quorum N-1, concurrencia, corrección, cancelación, archivos, cierre, auditoría y paginación.
- Pruebas frontend para componentes, cambios pendientes, descriptores y errores.
- Prueba E2E: crear personas, asignar una a un apartamento y otra a varios, crear Administrador operativo, solicitar con soporte, aprobar por todos menos solicitante, cerrar con factura, visualizar/descargar y consultar auditoría.
- Datos E2E claramente marcados `[PRUEBA]`; nunca uses destinatarios reales sin autorización.
- Valida build de Vite, compilación backend, contenedores, salud, persistencia, CORS y despliegues.
- No declares producción certificada si Vercel/Render ejecutan builds distintos al código probado.

Entrega código modular, migraciones reproducibles, Dockerfiles, Compose, GitHub Actions, `render.yaml`, configuración de Vercel y README con una tabla final que explique cada archivo importante, ambiente, variable y orden de despliegue.

Si falta una decisión, elige la alternativa más simple que preserve seguridad, privacidad, trazabilidad y consistencia; documenta la suposición y continúa.

## FIN DEL PROMPT
