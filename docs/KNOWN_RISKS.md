# Riesgos y divergencias conocidas

Última revisión: 2026-09-01.

Este registro evita que una persona o IA convierta una limitación actual en una regla falsa. Los documentos normativos siguen describiendo el comportamiento correcto; una divergencia se corrige en código y pruebas, no rebajando el contrato.

## Bloqueos críticos

### Valor anterior vacío al sustituir Roles de un Usuario

La sustitución de Roles mediante la ruta canónica puede capturar un estado
intermedio sin asignaciones: el `DELETE` por SQL Core elimina el Rol anterior y
el alta ORM del nuevo Rol dispara la instantánea antes de completar la
sustitución. El evento `USER_ROLES_UPDATED` conserva el Rol actual, pero puede
mostrar `assigned_roles.before=[]` aunque existiera un Rol anterior.

La corrección debe preparar la revisión del Usuario antes de cualquier borrado
de asignaciones y conservar el registro final después de aplicar el conjunto
nuevo. No rebajar la Spec 024 ni la comparación anterior/actual para aceptar el
estado vacío. El filtro de fechas de Auditoría no causa ni corrige esta
divergencia.

### Asignación de Roles en la ficha de Usuario

El contrato permite máximo un Rol **por Grupo** y cero o más Roles globales. El backend acepta una lista de `role_ids`, pero la implementación actual de `UsersPanel` en `frontend/src/iam-admin.jsx` reduce la selección a un solo Rol total. Algunas pruebas frontend también fijan por error ese comportamiento.

Hasta corregirlo:

- no cambiar Constitución, Specs o documentos para declarar “un solo Rol por Usuario”;
- no usar la UI como evidencia de que las cardinalidades IAM están completas;
- cubrir la corrección con selección por Grupo, multiselección global, persistencia y regresión de membresía derivada.

### Dumps de base de datos versionados

Existen archivos binarios de respaldo ya rastreados bajo `backups/`. No deben abrirse, imprimirse, copiarse ni incorporarse a nuevos commits. `.gitignore` previene nuevas incorporaciones, pero no elimina archivos ya presentes ni su historial.

La remediación requiere una tarea autorizada por el propietario: evaluar exposición, rotar credenciales si aplica y decidir eliminación del índice/historial. Ninguna IA debe reescribir historia o borrar esos respaldos por iniciativa propia.

## Riesgos operativos abiertos

### Identidad exacta del despliegue

El workflow manual verifica salud y límites anónimos después de activar Render/Vercel, pero hoy no compara un identificador de build o SHA servido por producción. Un resultado verde prueba disponibilidad, no por sí solo que el commit nuevo haya quedado publicado. Confirmar el artefacto en ambos proveedores antes de declarar el despliegue terminado.

### Conexión Neon para runtime y migraciones

La aplicación solo admite `DATABASE_URL`. El contenedor ejecuta Alembic antes de iniciar Uvicorn, así que no existe aún una separación entre URL pooled de runtime y URL directa de migración. Usar conexión directa en todo servicio que ejecute `backend/scripts/start.sh` hasta implementar y probar una variable de migración independiente.

### Correo en producción

La configuración permite técnicamente `EMAIL_MODE=console`; ese modo escribe cuerpos completos en logs y puede incluir contraseñas temporales o enlaces con token. Producción debe usar `brevo`, valores HTTPS y remitente verificado. Falta un guard de runtime que rechace `console` en producción, por lo que la revisión de variables antes del despliegue es obligatoria.

Además, el texto actual de `send_user_access_updated()` todavía afirma que los Permisos pueden provenir de Cargo o asignaciones directas. Eso contradice el IAM vigente: Cargo es informativo y no existen grants directos a Usuario. Corregir ese copy y cubrirlo con una prueba antes de usar esa notificación como explicación del acceso.

### Atomicidad de enlaces de restablecimiento

El proveedor de correo y PostgreSQL no comparten transacción. Un fallo reportado
antes del commit permite rollback, pero si el proveedor acepta el mensaje y el
commit falla después, el Usuario puede recibir un enlace inútil. No cambia su
contraseña ni sesiones; el Administrador debe reemitir. La garantía fuerte
requiere un outbox transaccional, que aún no existe.

### Entrega de notificaciones del flujo

La solicitud y sus aprobaciones se confirman antes de invocar al proveedor de
correo para no enviar enlaces de una transacción fallida. Si el proveedor falla
después del commit, la ronda sigue válida pero el mensaje puede no llegar. Los
logs registran el fallo sin invalidar la solicitud; entrega garantizada y
reintentos durables requieren un outbox transaccional aún no implementado.

### Rate limit público por proceso

El consumo de enlaces se limita por IP dentro de la memoria de cada proceso. La
limpieza TTL evita crecimiento indefinido y el proxy local aporta la IP real,
pero varias réplicas no comparten cuota. Un límite global requiere un almacén
compartido y no debe darse por implementado.

### Polling continuo en Seguimiento

`ExpenseTable` en `frontend/src/main.jsx` vuelve a consultar
`/api/expenses` cada cinco segundos. Esto contradice la política normativa de
cargar al montar, después de mutaciones y mediante **Recargar** explícito, sin
tráfico continuo por temporizadores. No documentar ese polling como
comportamiento deseado; retirarlo y cubrir la regresión en una tarea funcional
con alcance explícito.

### Transformaciones de Vite

`frontend/vite.config.js` transforma fragmentos concretos de `main.jsx` y `iam-admin.jsx` durante el build. Una edición puede funcionar en el archivo fuente y romper la extracción. Todo cambio en esos puntos exige `npm run build`; consultar `FRONTEND_RUNTIME.md` antes de mover componentes o guards.

### Scripts demo

`app.demo_monitoring` y `app.live_demo` crean o modifican datos. Solo están autorizados dentro del stack Docker local aislado descrito en `VALIDACION_LOCAL.md`; no ejecutarlos con una URL externa, Neon o producción.
