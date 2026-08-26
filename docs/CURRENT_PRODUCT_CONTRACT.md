# Contrato vigente del producto

Este documento es el mapa rápido entre Constitución, código y Specs. No sustituye la Constitución; resume el estado que una implementación correcta debe observar.

## Producto

Flujo de Control de Gastos digitaliza solicitudes y decisiones con evidencia, auditoría y responsabilidades explícitas. La configuración organizacional vive en PostgreSQL y no se codifican nombres organizacionales en reglas de autorización.

## Identidad y acceso

```text
Usuario
├─ requests:read si está activo
├─ 0..1 Cargo (informativo)
├─ 0..N Roles globales
└─ Roles agrupados
     └─ máximo 1 Rol por Grupo
          ├─ Permisos propios del Rol
          └─ Permisos heredados del Grupo
```

Cardinalidades:

```text
Grupo   0..N Roles
Rol     0..1 Grupo
Usuario 0..1 Rol por Grupo
Usuario 0..N Roles globales
Usuario 0..1 Cargo
Rol     0..1 límite positivo de Usuarios activos (`NULL` = sin límite)
```

Un Rol sin Grupo es global. La membresía del Grupo es una proyección únicamente de Roles agrupados y `GroupMember` aislado no autoriza. Cargo tampoco participa en autorización.

En Configuración > Accesos, la lista de Usuarios activos presenta como máximo 10 coincidencias. La búsqueda acepta cédula, nombres, apellidos, correo, Rol o Grupo asignado y no distingue mayúsculas ni acentos. Cada tarjeta muestra debajo del correo todos los Roles persistidos; si no tiene ninguno, no presenta una línea vacía, y un Rol asignado inactivo se identifica como tal.

La ficha de un Usuario activo no técnico permite enviar un enlace de
restablecimiento. Requiere confirmación y `config:manage`; es una acción inmediata
separada de las ediciones staged de Roles y de **Guardar cambios**.

## Permisos

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

`config:manage` está protegido para `system_accounts`; `config:read` es lectura ordinaria. `requests:close` no es una capacidad operativa vigente.

Los permisos efectivos ordinarios pueden venir de Permisos propios de Roles globales o, en un Rol agrupado dentro de un Grupo activo, de la unión `RolePermission ∪ GroupPermission`. Es herencia aditiva sin `DENY`; los Permisos propios se conservan al editar o desvincular el Grupo. `config:manage` continúa reservado a la política técnica protegida.

## UX principal

```text
Inicio        → mis acciones + mis solicitudes
Solicitudes   → consulta de procesos; crear solo con requests:create
Seguimiento   → carga de equipo, solo lectura
Configuración → Accesos / Áreas / Reglas / Auditoría según permisos
```

Accesos:

```text
Usuario → selector de Rol por Grupo + Roles globales → Guardar cambios
Grupo   → Permisos heredables + Roles opcionales; miembros derivados
Rol     → Permisos propios + herencia visible; global o agrupado
        → ocupación y máximo opcional de Usuarios activos
```

El Rol global técnico `Administrador del sistema` no pertenece a ningún Grupo. El bootstrap lo asigna a la cuenta técnica como representación, pero la autorización privilegiada sigue dependiendo de `system_accounts`.

La respuesta de sesión expone `role_names` con los Roles IAM activos asignados.
La cabecera muestra todos esos nombres y no el perfil técnico legacy ni una frase
de Permiso. Sin asignación ordinaria muestra **Sin rol asignado**; una cuenta
técnica sin Rol visible muestra **Administrador del sistema**.

Un Rol puede limitar opcionalmente su cantidad de Usuarios activos. Los Usuarios inactivos conservan su asignación sin consumir cupo; asignar a otro Usuario activo o reactivar uno que conserva el Rol se rechaza si está lleno. El máximo no puede bajarse de la ocupación activa y FastAPI serializa la comprobación sobre la fila del Rol.

Contrato responsive global:

- funciona desde 320 px de ancho CSS sin overflow horizontal de página;
- la navegación permanece disponible como banda táctil desplazable y los menús
  flotantes no salen del viewport;
- la consulta principal de Solicitudes cambia la tabla ancha por tarjetas con
  etiquetas; formularios, filtros, tableros, Accesos y Seguimiento se apilan;
- el estado de cada Rol, las acciones y los textos largos permanecen visibles;
- modales y visores usan altura dinámica, `safe-area` y un cierre alcanzable;
- los controles táctiles principales miden al menos 44 px;
- la validación visual mínima cubre 1180, 1024, 640, 440, 390 y 320 px.

**Divergencia conocida:** el contrato anterior sigue exigiendo un selector por Grupo y selección múltiple de Roles globales. La ficha actual de `iam-admin.jsx` expone temporalmente un único selector total y reduce el borrador a `role_ids[0]`. Esto no modifica la cardinalidad normativa y no debe copiarse en una reconstrucción; la corrección debe representar y preservar todos los Roles ya asignados antes de guardar.

## Flujo

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

`SIMPLE` crea su ronda con todos los Usuarios activos que tengan permiso efectivo
`requests:approve`, excluyendo al Solicitante. Participan por igual el Permiso
propio de un Rol global, el propio de un Rol agrupado y el heredado de su Grupo
activo. Una regla de monto puede definir la modalidad; si no existe una aplicable,
IAM sigue activo y se usa `MAJORITY`. Cargo, `GroupMember`, nombres de perfiles y
reglas legacy por correo no seleccionan aprobadores.
`ApprovalPolicy.approver_profile_codes` es metadata física legacy y tampoco
participa en la población.

La solicitud nueva, su soporte y su ronda constituyen una unidad de éxito. Si no
puede prepararse el flujo, la API responde con error y no conserva la solicitud
ni archivos huérfanos. Las notificaciones ocurren después del commit.

`MULTI_QUOTE` congela por ronda a los usuarios activos con `requests:approve`,
excluye al solicitante y requiere soporte en cada opción. Cada invitado tiene un
voto activo que puede cambiar mientras la solicitud siga en
`QUOTATION_VOTING`; cada cambio conserva evento. Cuando todos votan, un ganador
único es provisional y no cambia el estado. Un empate limpia esa selección y
bloquea la factura. Solo la factura, tras recalcular bajo bloqueo que la población
está completa y no hay empate, lleva directamente a `CLOSED`.

La tabla operativa expone `tracking_amount` sin alterar `Expense.amount`: máximo
de opciones sin votos, monto del líder único cuando hay votos y máximo de todas
las opciones cuando los líderes están empatados.

Estados relevantes:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
APPROVED
REJECTED
NEEDS_REVISION
CANCELLED
CLOSED
```

Acciones contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Clasificación

```text
expense_area
expense_category
```

Área y Categoría son independientes y su habilitación conjunta usa una relación N:M.

## Responsabilidad por recurso

El backend calcula `can_cancel`, `can_correct`, `can_close`, `can_delegate_close`. Estas capacidades dependen de estado y relación con la solicitud, no de un permiso IAM global.

Para solicitudes múltiples, `can_close` solo es accionable con ganador
provisional. Un 409 por empate o votos pendientes no persiste factura ni cierre.

## Seguridad de sesión

- rutas privadas requieren token;
- token inválido/expirado/inactivo devuelve 401;
- `session_version` permite revocación;
- inactividad expira sesión;
- contraseña temporal bloquea operación normal hasta cambio;
- un 401 en frontend limpia sesión y retorna Login.

## Restablecimiento de contraseña

La emisión administrativa usa
`POST /api/users/{user_id}/regenerate-password`. Solo `config:manage` efectivo
puede solicitarla y el destino debe ser un Usuario activo no técnico. El token
tiene propósito exclusivo, un solo uso y una vigencia predeterminada de 30
minutos configurable mediante `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`.

`users.password_reset_version` identifica la emisión vigente. Emitir un enlace
nuevo incrementa esa versión e invalida los anteriores, pero no cambia la
contraseña, `must_change_password` ni las sesiones; un fallo de correo revierte
el incremento. El mensaje contiene `/reset-password#token=...` y nunca una
contraseña.

`POST /api/auth/reset-password` consume el token sin sesión. Un consumo válido
almacena Argon2, establece `must_change_password=false`, incrementa
`session_version` y `password_reset_version`, revoca sesiones e invalida todos
los enlaces. El frontend vuelve al Login sin auto-login. La emisión usa la cuota
sensible autenticada y el consumo una cuota pública de 5 intentos por 15
minutos por IP y proceso, con limpieza TTL y confianza en `X-Forwarded-For` solo
desde un peer privado/loopback. Respuesta, UI y auditoría no exponen token, contraseña o hash; tampoco
los logs ordinarios, con la excepción explícita de `EMAIL_MODE=console` local,
cuyo cuerpo se trata como sensible.

Cambiar el correo o el estado activo invalida enlaces anteriores. Después del
commit exitoso se intenta enviar una confirmación sin token ni contraseña; su
fallo no revierte el cambio. Correo y base no son atómicos: si el proveedor
acepta el mensaje y luego falla el commit de emisión, el enlace recibido será
inútil y debe reemitirse.

## Red frontend

No polling agresivo. GET iguales se deduplican en vuelo y las repeticiones automáticas usan caché corta. Las mutaciones invalidan lecturas. Las acciones de usuario pueden solicitar datos frescos.

## Persistencia

```text
ph_torre_delta.administracion
```

Alembic:

```text
0001 initial_schema
→ 0002 group_scoped_roles
→ 0003 single_user_position
→ 0004 allow_global_roles
→ 0005 activity_periods
→ 0006 period_snapshot_values
→ 0007 period_audit_metadata
→ 0008 normalize_period_timestamps
→ 0009 group_permission_inheritance
→ 0010 password_reset_links
→ 0011 role_user_limit
→ 0012 keep_quotation_voting_open
```

`0004` permite Roles globales manteniendo la protección de máximo un Rol por Usuario/Grupo.
`0005` agrega períodos para Usuario, Área, Rol y Grupo. `0006` incorpora la
instantánea JSON: cada modificación cierra la versión anterior y abre una fila
nueva con llave propia. Usuario conserva cédula, contacto y Roles; Rol conserva
el Grupo asociado.
`0007` agrega actor, timestamp, tipo de evento, campos modificados y valores
anterior/nuevo. Las operaciones autenticadas usan al usuario de la sesión y los
procesos internos quedan marcados como `SYSTEM:*`.
`0008` normaliza toda vigencia y evento a timestamps con zona horaria UTC.
`0009` agrega `group_permissions` vacía y no altera `role_permissions` ni accesos preexistentes.
`0010` agrega `users.password_reset_version` para invalidar enlaces de restablecimiento sin almacenar tokens ni rotar la contraseña durante la emisión.
`0011` agrega `roles.max_users` nullable, exige valores positivos y añade el campo a las instantáneas temporales de Rol sin limitar Roles existentes.
`0012` devuelve a `QUOTATION_VOTING` las solicitudes `MULTI_QUOTE` que habían
quedado en `APPROVED` sin factura, sin modificar solicitudes cerradas ni sus
adjuntos.

## Recuperación de entidades inactivas

Usuario, Área, Rol y Grupo desaparecen de sus listas al quedar inactivos. Las
rutas `/recovery` permiten localizar únicamente registros inactivos por cédula,
código o nombre normalizado. La UI solicita confirmación, completa el formulario
y usa `PATCH` sobre el ID recuperado; nunca crea otra identidad ni borra auditoría.
El flujo existe tanto en la consola IAM como en la pantalla principal de Personas.

El runtime es compatible con Neon pooled porque tablas, tipos ENUM y SQL crudo se califican explícitamente y no se envía `search_path` mediante startup options. Los contadores de identificadores usan el nombre completo derivado de `AreaCounter.__table__.fullname`; los Enum ORM usan `inherit_schema=True`. Alembic y `pg_dump` requieren conexión directa; como `start.sh` todavía comparte una única `DATABASE_URL`, el servicio completo usa URL directa hasta separar y probar la conexión de migración.

## Archivos de referencia en código

Backend:

```text
app/services/iam_service.py
app/api/iam_users.py
app/api/iam_group_assignments.py
app/api/iam_access_policy.py
app/api/users.py
app/api/auth.py
app/core/security.py
app/services/email_service.py
app/api/organization_overview.py
```

Frontend:

```text
iam-admin.jsx
home-dashboard.jsx
user-tracking.jsx
auth-route-guard.js
request-governor.js
expense-form.jsx
```
