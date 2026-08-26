# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.21.0
**Vigente desde:** 2026-08-26

## 1. Propósito

El producto digitaliza solicitudes de gasto y sus decisiones con trazabilidad verificable. Debe servir a distintos tipos de organización sin introducir reglas de negocio dependientes del nombre de una organización, grupo, cargo, rol, usuario o área.

FastAPI es la autoridad final para autorización, transiciones, acceso a documentos y capacidades por solicitud. El frontend puede anticipar esas reglas por UX, pero nunca sustituirlas.

## 2. Fuente de verdad y documentación

Orden de autoridad:

1. esta Constitución;
2. `specs/**/spec.md` vigentes;
3. checklists de aceptación;
4. `specs/**/plan.md`;
5. `PROMPT_RECONSTRUCCION.md`;
6. `README.md`;
7. `docs/`;
8. código de compatibilidad explícitamente marcado como deuda.

Un cambio funcional, de seguridad, persistencia, UX o arquitectura no está terminado si deja estas fuentes desalineadas. La documentación normativa describe el estado actual del producto; HISTORY/CHANGELOG pueden resumir evolución, pero no convierten un diseño anterior en alternativa vigente.

## 3. Terminología canónica

- **Usuario**: cuenta autenticable del producto.
- **Grupo**: ámbito organizacional opcional que puede contener cero o más Roles y aportar Permisos heredables a esos Roles.
- **Rol**: conjunto reutilizable de Permisos propios. Puede ser global o pertenecer como máximo a un Grupo; si está agrupado suma los Permisos de su Grupo. Puede limitar opcionalmente cuántos Usuarios activos lo tienen asignado.
- **Rol global**: Rol sin Grupo. No crea membresía de Grupo.
- **Permiso**: capacidad IAM atómica implementada por el producto.
- **Cargo / Posición**: dato organizacional descriptivo. No concede acceso.
- **Área**: unidad, función o contexto organizacional asociado al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.
- **Inicio**: vista personal y operativa del usuario conectado.
- **Seguimiento**: vista de solo lectura de carga del equipo por Grupo, miembro y Rol.
- **Accesos**: consola administrativa de Usuarios, Grupos, Roles y Permisos.
- **Enviar a revisión**: decisión del aprobador que interrumpe la ronda y devuelve la solicitud al solicitante.
- **Corregir / reenviar**: edición por solicitante original o Administrador del sistema cuando el estado lo permite.
- **Delegación de cierre/factura**: autoridad por solicitud, explícita y revocable.

No se crearán sinónimos funcionales para estos conceptos.

## 4. IAM vigente

Modelo normativo:

```text
Permiso propio    → Rol ── 0..1 Grupo ← Permiso heredable
                       ↑
                    Usuario

Usuario activo → requests:read (baseline)
Cargo          → dato organizacional, sin autorización
SystemAccount  → política técnica protegida + Rol global técnico
```

Reglas obligatorias:

1. Un Grupo puede existir con cero Roles y cero miembros.
2. Un Rol puede pertenecer a cero o un Grupo; nunca a más de uno.
3. Un Rol sin Grupo es un Rol global.
4. Un Usuario puede tener como máximo un Rol dentro de cada Grupo.
5. Un Usuario puede tener cero o más Roles globales ordinarios.
6. Asignar un Rol agrupado al Usuario determina automáticamente su membresía en ese Grupo.
7. Quitar o volver global ese Rol elimina la membresía derivada cuando el Usuario ya no conserva otro Rol de ese Grupo.
8. Un Rol global no crea membresía de Grupo.
9. No se asignan Permisos directamente a Usuarios.
10. Un Cargo no hereda Roles ni Permisos y no participa en `effective_permission_codes()`.
11. Cada Usuario puede tener como máximo un Cargo activo asociado.
12. El nombre/código de Grupo, Rol, Cargo, Área o Usuario nunca autoriza por sí mismo.
13. Un Grupo puede tener cero o más Permisos; cada Rol activo vinculado a ese Grupo hereda esos Permisos mientras el Grupo esté activo.
14. Para un Rol agrupado, los Permisos aplicables son la unión aditiva de sus Permisos propios y los de su Grupo. La ausencia de un Permiso propio significa “heredar si el Grupo lo aporta”; no existe `DENY` ni precedencia negativa a nivel de Rol.
15. Editar los Permisos de un Grupo o mover un Rol entre Grupo y scope global no borra ni reemplaza sus filas `RolePermission`. Al desvincularlo solo deja de heredar del Grupo y conserva sus Permisos propios y sus asignaciones de Usuario.
16. `GroupMember` es una proyección organizacional. Una fila de membresía sin `UserRoleAssignment` a un Rol activo de ese Grupo no concede ningún Permiso.
17. Un Rol puede definir `max_users` como entero positivo; `NULL` significa sin límite.
18. El cupo cuenta únicamente Usuarios activos con `UserRoleAssignment` al Rol. Un Usuario inactivo conserva la asignación, pero no consume cupo.
19. Asignar el Rol o reactivar un Usuario que lo conserva se rechaza si alcanzaría un cupo ya lleno.
20. No se permite reducir `max_users` por debajo de la cantidad actual de Usuarios activos asignados.
21. La verificación de cupo es responsabilidad transaccional de FastAPI y debe serializar asignaciones concurrentes sobre el Rol; deshabilitar una opción llena en la UI es solo asistencia de UX.

Permisos vigentes:

```text
requests:read     baseline para usuarios activos
requests:create   crear solicitudes nuevas
requests:approve  aprobar, rechazar, votar y enviar a revisión cuando corresponda
areas:manage      administrar Área + Categoría
config:read       consultar Configuración sin mutarla
config:manage     administración técnica protegida
```

`requests:close` puede existir físicamente como registro inactivo de compatibilidad, pero no autoriza cierre ni factura.

Para un usuario ordinario activo:

```text
effective_permissions =
    {requests:read}
  ∪ permisos propios de sus Roles globales activos
  ∪ permisos propios de sus Roles agrupados activos cuyo Grupo esté activo
  ∪ permisos de cada Grupo activo alcanzado por uno de esos Roles agrupados
  - {config:manage}
```

Para cada Rol agrupado, la operación es `RolePermission ∪ GroupPermission`: los duplicados se colapsan y un Permiso heredado no puede negarse desde el Rol. La mera existencia de `GroupMember` no participa en esta resolución.

`config:manage` solo es efectivo conforme a la política de `system_accounts`, aunque figure en un Grupo o Rol ordinario. `config:read` y `areas:manage` pueden llegar como Permiso propio de un Rol o por herencia de Grupo.

## 5. Accesos

`Configuración → Accesos` es la superficie administrativa de IAM. Su modelo visible es:

```text
Usuarios → Acceso por grupo → máximo un Rol por Grupo
         → Roles globales   → cero o más
Grupos   → Permisos heredables + Roles opcionales + miembros derivados (solo lectura)
Roles    → Permisos propios + herencia visible del Grupo + cupo opcional de Usuarios activos
Permisos → catálogo de capacidades
```

No se muestran permisos individuales. Cargo no forma parte de la matriz de autorización de Accesos.

Toda edición de acceso se prepara localmente y se persiste únicamente mediante un botón explícito **Guardar cambios**. Marcar, desmarcar o seleccionar opciones no debe producir mutaciones por sí solo. Si se abandona una edición con cambios pendientes, la UI debe pedir confirmación.

El envío de un enlace para restablecer contraseña es una acción de seguridad
inmediata e independiente de las ediciones staged de IAM. Requiere confirmación
explícita, `config:manage` efectivo y un Usuario destino activo que no pertenezca
a `system_accounts`; no espera ni queda incluido en **Guardar cambios**.

La edición de un Rol puede actualizar el estado local con la respuesta del `PATCH`; no requiere un GET adicional para reflejar su nombre o estado.

Mover un Rol entre “global” y un Grupo no elimina sus asignaciones de Usuario ni sus `RolePermission`. La aplicación debe recalcular la membresía derivada y rechazar el cambio si produciría dos Roles del mismo Grupo para un mismo Usuario. Al quedar global, el Rol deja de recibir `GroupPermission`; al vincularse a otro Grupo, suma la herencia de ese Grupo a sus Permisos propios.

## 6. Configuración

- `config:read`: lectura de recursos de Configuración. Puede satisfacer guards de `config:manage` únicamente para `GET`/`HEAD`.
- `config:manage`: mutaciones técnicas y de IAM; reservado a la política protegida del Administrador del sistema.
- `areas:manage`: mutaciones de Área, Categoría y relaciones; no concede administración IAM.

Una mutación nunca se autoriza por `config:read`.

## 7. Cargo

Cargo/Posición es metadato organizacional opcional, con cardinalidad `Usuario 0..1 Cargo`. Puede aparecer en comunicaciones y vistas organizacionales, pero cambiar Cargo no cambia los permisos efectivos.

Las notificaciones de creación/cambio pueden incluir el Cargo y siempre deben calcular los permisos desde el IAM vigente: Permisos propios de Roles globales o agrupados, más la herencia aditiva de sus Grupos activos.

## 8. Inicio y Seguimiento

### Inicio

Responde a: **“¿Qué tengo que atender yo?”**

- acciones pendientes asignadas al usuario;
- solicitudes creadas por ese usuario;
- métricas personales;
- acceso contextual a aprobación, votación, corrección o cierre cuando corresponda.

### Seguimiento

Responde a: **“¿Cómo está la carga del equipo?”**

- Grupos activos;
- miembros derivados de Roles agrupados;
- Rol de cada miembro dentro del Grupo;
- cantidad de acciones pendientes por usuario y por Grupo;
- búsqueda por usuario/grupo/rol;
- filtro de usuarios con pendientes.

Los Roles globales no crean filas de membresía en Seguimiento. Es de solo lectura y no modifica accesos.

En la tabla operativa de Solicitudes, el monto visible de una ronda
`MULTI_QUOTE` abierta es informativo y no modifica `Expense.amount`: sin votos
es el máximo presentado; con líder único es el monto de esa opción; con empate
es el máximo de todas las opciones.

## 9. Sesión y rutas privadas

Toda pantalla protegida requiere sesión válida. Abrir directamente una ruta/hash privado sin token debe volver al Login sin montar una vista parcial. Un `401` con token almacenado invalida la sesión local y retorna al Login.

La regla aplica al menos a Accesos y Seguimiento y debe extenderse a cualquier nueva superficie privada.

## 10. Política de requests del frontend

La aplicación no debe producir tráfico continuo por re-render, efectos React o temporizadores accidentales.

Reglas:

- carga inicial al entrar;
- recarga por mutación real, navegación relevante o acción explícita;
- no polling sub-segundo;
- GET idénticos concurrentes comparten una sola llamada;
- repeticiones automáticas pueden reutilizar una respuesta reciente durante una ventana corta;
- POST/PUT/PATCH/DELETE invalidan la caché de lectura;
- una acción humana explícita puede solicitar datos frescos;
- autenticación, archivos y URLs tokenizadas no se cachean con el gobernador general.

Si una feature futura necesita polling, debe documentar propósito y frecuencia y no puede usar un intervalo agresivo por defecto.

## 11. Solicitudes y clasificación

Contrato canónico:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M configurable.

El formulario **Nueva solicitud / Registrar gasto** solo se ofrece a usuarios con `requests:create`. `requests:read` permite consultar, pero no crear.

Tipos de solicitud:

```text
SIMPLE
MULTI_QUOTE
```

Una corrección conserva el tipo:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

Una ronda `MULTI_QUOTE` congela como participantes a usuarios activos con permiso efectivo `requests:approve`, excluye al solicitante y exige soporte válido en cada opción. Cada invitado mantiene un voto activo y todo cambio conserva un evento inmutable. La ronda espera a todos los invitados y permanece en `QUOTATION_VOTING` incluso cuando existe un ganador único provisional, para que los invitados puedan cambiar su voto. Un empate elimina cualquier ganador provisional y bloquea la factura. La carga válida de la factura, con votación completa y ganador único calculado bajo bloqueo transaccional, es el evento que cierra la ronda y lleva la solicitud a `CLOSED`.

Una ronda `SIMPLE` también resuelve sus participantes desde todos los Usuarios
activos con permiso efectivo `requests:approve`, excluyendo al Solicitante. El
Permiso puede provenir de un Rol global, ser propio de un Rol agrupado o heredarse
de su Grupo activo. Una `ApprovalPolicy` aplicable puede determinar la modalidad,
pero su ausencia no desactiva IAM; se usa `MAJORITY`. Reglas legacy por correo y
nombres de perfiles no autorizan ni seleccionan aprobadores.
`ApprovalPolicy.approver_profile_codes` permanece únicamente como metadata de
compatibilidad hasta retirar esa estructura física.

Una solicitud nueva solo se confirma cuando puede iniciar su ronda con soporte
válido y al menos otro participante elegible. Si el flujo no puede prepararse,
FastAPI revierte la creación y no deja una solicitud ni un soporte huérfanos. Las
notificaciones se intentan después del commit y no sustituyen la creación
transaccional de la ronda.

## 12. Acciones pendientes

Tipos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

Son tareas contextuales, no Permisos IAM.

`QUOTATION_VOTE` permanece disponible para cada invitado mientras la ronda siga
en `QUOTATION_VOTING`, aunque ya haya votado, porque representa **votar o cambiar
el voto**. Desaparece al cerrar la solicitud.

## 13. Aprobación, revisión y corrección

Una decisión de aprobación puede ser `APPROVED`, `REJECTED` o `REVISION_REQUESTED`.

Una revisión válida:

```text
approval actual       → REVISION_REQUESTED
solicitud             → NEEDS_REVISION
otras PENDING/WAITING → EXPIRED
solicitante           → CORRECT_REQUEST
```

El aprobador no obtiene capacidad de edición. Corregir corresponde al solicitante original o al Administrador del sistema cuando la solicitud es corregible.

## 14. Cancelación, cierre y factura

Capacidades por recurso:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

Cerrar/facturar requiere estado compatible y una de estas relaciones:

```text
solicitante original
OR system_accounts
OR delegado activo de esa solicitud
```

`requests:close` no participa.

En `MULTI_QUOTE`, `QUOTATION_VOTING` es compatible con cierre solo cuando todos
los invitados votaron y existe un ganador único provisional. La API vuelve a
calcular el resultado bajo bloqueo al recibir la factura; si falta un voto o hay
empate responde 409 y no persiste archivo ni cierre. Una cotización con ganador
provisional no pasa por `APPROVED`: la factura la lleva directamente a `CLOSED`.

## 15. Cuenta técnica

La identidad técnica se persiste en `system_accounts`; no se deriva de nombre, correo, Cargo o `UserRole`.

`Administrador del sistema` es un **Rol global técnico** (`system_managed`) y no pertenece a ningún Grupo. El bootstrap lo asigna a la cuenta técnica para representar su responsabilidad, pero esa asignación no sustituye la política protegida de `system_accounts`.

En producción, la política técnica vigente es:

```text
requests:read
areas:manage
config:manage
```

En producción no participa en aprobación ni votación. En ambientes no productivos la política técnica puede incluir todos los Permisos activos para pruebas end-to-end; esa ampliación de laboratorio no redefine el acceso productivo. Conserva excepciones administrativas por recurso donde el backend las define. El Rol global técnico no puede asignarse, quitarse ni modificarse desde la consola ordinaria.

## 16. Persistencia y Neon

Base de datos de aplicación:

```text
ph_torre_delta
└── administracion
```

`DATABASE_SCHEMA=administracion` es obligatorio. `public` no se usa como schema de aplicación.

Compatibilidad Neon pooled del runtime:

- SQLAlchemy usa `MetaData(schema=DATABASE_SCHEMA)`;
- Alembic usa schema explícito y `version_table_schema`;
- no se envía `options=-csearch_path=...` como parámetro de startup al pooler;
- las migraciones crean el schema si falta.
- los tipos Enum ORM heredan el schema de metadata;
- SQL crudo usa nombres de tabla calificados derivados de metadata.

Alembic y `pg_dump` usan una conexión directa de Neon. Mientras runtime y migraciones compartan una sola `DATABASE_URL` y `start.sh` migre antes de iniciar, el servicio completo debe usar la URL directa; adoptar pooled en runtime requiere implementar y probar una conexión de migración separada.

Cadena Alembic vigente:

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
→ 20260821_0004_allow_global_roles
→ 20260821_0005_activity_periods
→ 20260821_0006_period_snapshot_values
→ 20260821_0007_period_audit_metadata
→ 20260821_0008_normalize_period_timestamps
→ 20260824_0009_group_permission_inheritance
→ 20260824_0010_password_reset_links
→ 20260825_0011_role_user_limit
→ 20260825_0012_keep_quotation_voting_open
```

`20260824_0009_group_permission_inheritance` agrega `group_permissions` vacía para no alterar accesos existentes durante la migración. La tabla relaciona Grupo y Permiso de forma única; no introduce denegaciones ni modifica `role_permissions`.

`20260824_0010_password_reset_links` agrega
`users.password_reset_version` con valor inicial cero. Cada emisión o consumo
válido lo incrementa para invalidar tokens anteriores sin almacenar el token; la
emisión por sí sola no modifica la contraseña, `must_change_password` ni
`session_version`.

`20260825_0011_role_user_limit` agrega `roles.max_users` nullable con un check
positivo y normaliza las instantáneas temporales de Rol. No asigna límites a
Roles existentes: todos migran como ilimitados.

`20260825_0012_keep_quotation_voting_open` devuelve a `QUOTATION_VOTING` las
solicitudes `MULTI_QUOTE` que habían quedado prematuramente en `APPROVED` sin
factura. No altera solicitudes cerradas ni adjuntos existentes.

Usuarios, Áreas, Roles y Grupos mantienen historial temporal versionado. Cada
alta crea una fila cuyo `active_from` coincide con `created_at`; toda modificación
relevante cierra la versión vigente y abre otra con una instantánea JSON. Siempre
existe como máximo una versión abierta, también cuando `active=false`; el valor
JSON permite distinguir períodos activos e inactivos. Usuario conserva cédula,
contacto, nombre y Roles; Rol conserva el Grupo asociado y su `max_users`. Las restricciones
físicas impiden fechas invertidas y más de una versión abierta por entidad.
Cada versión identifica además quién realizó el cambio, cuándo ocurrió, el tipo
de evento, los campos modificados y el valor anterior/nuevo. Las acciones
autenticadas registran ID, correo y cédula del actor; procesos sin sesión usan
un identificador `SYSTEM:*`. La auditoría nunca almacena contraseñas o secretos.

Los listados activos de Usuario, Área, Rol y Grupo no mezclan entidades
inactivas. Las rutas de recuperación y las vistas administrativas de inspección
pueden consultarlas de forma explícita; el catálogo de Permisos puede conservar
registros inactivos para trazabilidad. Intentar crear nuevamente un Usuario por
cédula, o un Área/Rol/Grupo por su clave o nombre normalizado, debe ofrecer
recuperar la entidad inactiva: el backend devuelve su ID y datos, la UI completa
el formulario con confirmación y la reactivación conserva la identidad y el
historial en vez de insertar un duplicado.

La baseline `0001` permanece congelada después de desplegarse; los cambios físicos posteriores se agregan como nuevas revisiones.

## 17. Seguridad operativa

- contraseñas nuevas con Argon2 mediante `pwdlib`;
- sesiones JWT con versión revocable e inactividad;
- CORS explícito en producción;
- documentos privados servidos por backend autorizado;
- respuestas API sensibles con `Cache-Control: no-store`;
- rate limiting por usuario autenticado;
- secretos solo en variables de entorno/plataformas, nunca frontend o repositorio.

El restablecimiento administrativo de contraseña usa un enlace tokenizado de
propósito exclusivo, con vigencia configurable mediante
`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` y valor predeterminado de 30 minutos. Cada
token sirve una sola vez y emitir uno nuevo invalida cualquier enlace anterior
del mismo Usuario. Cambiar su correo o su estado `active` también invalida todos
los enlaces emitidos. La emisión incrementa `password_reset_version`, pero no
cambia la contraseña vigente, no modifica `must_change_password` y no revoca
sesiones. El mensaje incluye el enlace y nunca una contraseña temporal o nueva.

El token viaja en el fragmento
`/reset-password#token=...`: el navegador no envía ese fragmento en la petición
HTTP ni a logs HTTP/CDN. La SPA lo captura en memoria y lo retira de la URL al
cargar, sin persistirlo como sesión ni en almacenamiento del navegador.

Correo y base de datos no forman una transacción atómica. Si el proveedor
reporta el fallo antes del commit, la base hace rollback y conserva el enlace
anterior. Si el proveedor acepta el mensaje y después falla el commit, puede
llegar un enlace inútil, pero no cambia la contraseña, las sesiones ni el acceso;
el Administrador debe reintentar. Una entrega exactamente-una-vez requeriría un
outbox transaccional.

Consumir un enlace válido no requiere una sesión previa: reemplaza la contraseña
con un hash Argon2, establece `must_change_password=false`, incrementa
`session_version` y `password_reset_version`, invalida todos los enlaces de
restablecimiento y revoca las sesiones anteriores. El flujo termina en el Login
y nunca inicia sesión automáticamente. Después del commit se intenta enviar una
notificación best-effort de contraseña cambiada, sin token ni contraseña; su
fallo no revierte el cambio ya confirmado. La emisión usa la cuota sensible por
usuario autenticado. El consumo limita 5 intentos por 15 minutos por IP y por
proceso, con limpieza TTL; no constituye una cuota global entre réplicas y
depende de una dirección cliente confiable. La auditoría registra la acción y
sus actores sin persistir ni exponer el token, la contraseña o su hash.

## 18. Experiencia móvil

La interfaz privada y las rutas públicas deben funcionar desde 320 px de ancho
CSS sin overflow horizontal de la página, controles recortados ni pérdida de
foco visible. En pantallas estrechas:

- la navegación principal sigue disponible mediante una banda táctil desplazable
  y sus menús flotantes permanecen dentro del viewport;
- las consultas operativas prioritarias se representan como tarjetas legibles,
  no como tablas de escritorio comprimidas;
- formularios, filtros, acciones, Accesos y Seguimiento se apilan sin perder
  contenido ni acciones;
- diálogos y visores usan altura dinámica, respetan `safe-area` y mantienen una
  forma visible de cerrar;
- los objetivos táctiles principales miden al menos 44 px.

El escritorio conserva su densidad y estructura. Todo cambio visual transversal
se valida en navegador a 1180, 1024, 640, 440, 390 y 320 px; el build por sí solo
no acredita el contrato responsive.

## 19. Definition of Done

Todo cambio relevante debe revisar y actualizar, según aplique:

```text
.specify/memory/constitution.md
specs/**/spec.md
specs/**/plan.md
specs/**/checklists/acceptance.md
PROMPT_RECONSTRUCCION.md
README.md
docs/
docs/HISTORY.md
CHANGELOG.md
```

Validaciones mínimas:

```text
docker compose up -d --build
docker compose exec -T backend alembic heads
# esperado: 20260825_0012

cd backend
.\.venv\Scripts\python.exe -m scripts.run_tests

cd ..\frontend
npm ci
npm run build
```

Los sembradores `app.demo_monitoring`/`app.live_demo` no son gates universales: mutan datos y solo pueden ejecutarse cuando la validación funcional lo requiera, dentro del PostgreSQL local aislado de Compose.

Para cambios IAM, la aceptación debe cubrir además la unión aditiva Rol ∪ Grupo, ausencia de `DENY`, conservación de `RolePermission` al editar o desvincular, ausencia de autoridad por `GroupMember` aislado, exclusión de `config:manage` para usuarios ordinarios y, cuando aplique, cupo del Rol ante asignación, reactivación y concurrencia.

Para `MULTI_QUOTE`, la aceptación debe cubrir voto inicial y cambio de voto,
evento por cada cambio, ganador provisional sin transición a `APPROVED`, empate
que limpia la selección y bloquea la factura, recálculo transaccional al cerrar,
cierre directo a `CLOSED` con factura, rechazo de votos posteriores y monto
operativo máximo/líder/máximo para los casos sin votos/líder único/empate.

Para restablecimiento de contraseña, la aceptación debe cubrir autorización y
destinos protegidos, expiración y uso único, invalidación del enlace anterior,
rollback ante fallo de correo, ausencia de credenciales en el mensaje y la
auditoría, fragmento retirado por la SPA, invalidación por correo/estado, Argon2,
revocación de sesiones al consumir, notificación post-commit y ausencia de
auto-login. La prueba de entrega debe distinguir rollback antes del commit del
caso aceptado por el proveedor cuyo commit posterior falla.

GitHub Actions puede ser un gate adicional cuando exista cuota disponible; su indisponibilidad no convierte un run sin steps en evidencia de fallo del código.
