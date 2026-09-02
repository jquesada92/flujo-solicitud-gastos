# Prompt maestro de reconstrucción

> Constitución vigente: **2.30.0**.

Reconstruye **Flujo de Control de Gastos** como una aplicación web neutral respecto al tipo de organización, lista para desplegar con React/Vite, FastAPI, SQLAlchemy, Alembic y PostgreSQL/Neon.

Antes de ejecutar comandos o modificar el repositorio, aplica `AGENTS.md`. Esa política limita acciones operativas de personas y agentes automatizados; no altera la jerarquía funcional siguiente. Consulta también `docs/KNOWN_RISKS.md` para no reproducir divergencias conocidas como si fueran requisitos.

## Autoridad

Respeta, en orden:

1. `.specify/memory/constitution.md`;
2. `specs/**/spec.md`;
3. checklists de aceptación;
4. `specs/**/plan.md`;
5. este prompt;
6. `README.md`;
7. `docs/`.

No reconstruyas decisiones que contradigan una fuente de mayor prioridad aunque existan estructuras físicas de compatibilidad.

## 1. Modelo organizacional

Usa únicamente conceptos genéricos de organización. Los nombres concretos de Grupos, Roles, Cargos, Áreas o Usuarios son datos configurables en PostgreSQL y nunca condiciones runtime.

Conceptos visibles:

```text
Usuario
Grupo
Rol
Rol global
Permiso
Cargo / Posición
Área
Categoría
Inicio
Seguimiento
Accesos
Gasto directo
```

## 2. IAM

Modelo exacto:

```text
Permiso propio    → Rol ── 0..1 Grupo ← Permiso heredable
                       ↑
                    Usuario

Usuario activo → requests:read
Cargo          → metadato organizacional
SystemAccount  → política técnica + Rol global protegido
```

Invariantes:

- un Grupo puede existir con cero Roles;
- un Rol pertenece a cero o un Grupo, nunca a varios;
- un Rol sin Grupo es global;
- un Usuario puede tener máximo un Rol por Grupo;
- un Usuario puede tener cero o más Roles globales ordinarios;
- un Rol puede tener `max_users` opcional y positivo; `NULL` significa sin límite;
- el cupo cuenta Usuarios activos asignados, no Usuarios inactivos que conservan el Rol;
- asignar o reactivar se rechaza si el Rol está lleno y el máximo no puede bajarse de la ocupación actual;
- la membresía de Grupo se deriva únicamente de Roles agrupados;
- un Rol global no crea membresía de Grupo;
- no se asignan Permisos directamente a Usuarios;
- un Rol agrupado suma sus Permisos propios y los de su Grupo activo;
- la ausencia a nivel de Rol hereda, no niega; no existe `DENY`;
- `GroupMember` aislado no autoriza;
- Cargo no concede Permisos;
- un Usuario tiene 0..1 Cargo;
- nombres/códigos no autorizan.

Permisos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

`requests:read` es baseline para usuarios activos. `config:manage` es system-only. `requests:close` puede persistir inactivo por compatibilidad, pero no autoriza runtime.

Para usuario ordinario:

```text
effective_permissions =
    requests:read
  + own_permissions_of_active_global_roles
  + own_permissions_of_roles_in_active_groups
  + permissions_of_their_active_groups
  - config:manage
```

Para cada Rol agrupado aplica una unión de grants positivos: `RolePermission ∪ GroupPermission`. Conserva los Permisos propios adicionales, colapsa duplicados y no permite que un checkbox propio desmarcado niegue la herencia. `config:manage` continúa excluido para todo Usuario ordinario sin importar su fuente.

## 3. Accesos

Construye una única consola administrativa:

```text
Usuarios
  → Acceso por grupo
     → selector único de Rol por Grupo
  → Roles globales
     → selección de cero o más Roles sin Grupo

Grupos
  → pueden existir sin Roles
  → Permisos heredables editables
  → Roles opcionales del Grupo editables
  → miembros derivados de Roles agrupados, solo lectura

Roles
  → Permisos propios + herencia visible del Grupo
  → pueden ser globales o pertenecer a máximo un Grupo
  → límite opcional y ocupación de Usuarios activos

Permisos
  → catálogo de capacidades
```

No agregues controles de permisos directos a Usuario ni controles `DENY`. Cargo y `GroupMember` no son mecanismos de acceso.

Todas las ediciones de acceso son staged. No hagas requests de mutación al seleccionar una opción. Persiste con **Guardar cambios** y advierte antes de descartar cambios pendientes.

En la lista de Usuarios, muestra debajo de cada correo todos los Roles persistidos, con etiqueta singular/plural. Omite la línea si no hay Roles y conserva visible una asignación inactiva identificándola como tal.

En el editor de Rol permite activar/desactivar el límite y definir un entero positivo. Muestra la ocupación activa, no permite un máximo menor que ella y marca como sin cupo las opciones no asignables. El backend debe volver a validar y serializar asignaciones concurrentes; la UI no es la autoridad.

Después de un `POST` exitoso de Rol, incorpora la respuesta a la lista y vuelve a
**Crear rol** con `selectedId=null`, `recovery=null` y nombre, descripción,
permisos, límite y máximo vacíos. El siguiente alta debe usar otro `POST`, nunca
un `PATCH` al Rol recién creado. Un fallo conserva el borrador; edición y
reactivación siguen usando `PATCH` sobre su ID.

Quitar un Rol de un Grupo lo convierte en global sin borrar `UserRoleAssignment` ni `RolePermission`; elimina solo la herencia del Grupo. Editar Permisos del Grupo tampoco modifica `RolePermission`. Vincular Roles globales a un Grupo debe rechazarse si produciría más de un Rol del mismo Grupo para algún Usuario. Después de cambiar el catálogo de Roles de un Grupo, reconstruye `GroupMember` desde las asignaciones de Roles agrupados.

La consola debe funcionar sin overflow horizontal de página desde 320 px: paneles apilables, textos/códigos con wrap, estados y acciones siempre visibles y controles táctiles utilizables. Valida al menos 1180, 1024, 640, 440, 390 y 320 px. No reduzcas `role_ids` a una selección única total: el contrato es un selector por Grupo más multiselección de Roles globales.

En la ficha de un Usuario activo no técnico agrega **Regenerar contraseña** para
enviar el enlace de restablecimiento. Exige confirmación y `config:manage`; es
una acción de seguridad inmediata, separada del estado staged y de **Guardar
cambios**. Evita doble envío y nunca muestres el token en la respuesta o la UI.

## 4. Configuración

- `config:read`: puede consultar endpoints de Configuración con GET/HEAD.
- `config:manage`: mutaciones de IAM/técnicas; protegido por política de cuenta técnica.
- `areas:manage`: mutaciones de Área + Categoría.

Nunca conviertas `config:read` en autoridad de escritura.

En **Configuración → Auditoría**, consulta exclusivamente `audit_change_feed`.
Precarga **Desde/Hasta** con las siete fechas calendario inclusivas desde hoy
menos seis días hasta hoy en `APP_TIME_ZONE`. El rango es editable y puede
ampliarse para investigar historia anterior, sin un recorte fijo de 45 días. No
ofrezcas la vista agregada **Todos**: muestra únicamente **Flujos**, **Usuarios**,
**Accesos**, **Áreas** y **Reglas**, con **Flujos** como sección inicial. Cada
fila debe decir **Creación**, **Actualización** o **Eliminación**, identificar
elemento y actor y mostrar por campo **Valor anterior** y **Valor actual**. En
particular, un cambio de Roles de Usuario usa `assigned_roles` anterior/actual
del feed bajo `USER_ROLES_UPDATED`.

Captura cada cambio auditable una sola vez y dentro de la misma transacción de
negocio. Filtra el rango en base antes de paginar por
`occurred_at,event_sequence` mediante una consulta indexada; no cargues todos
los Usuarios ni consultes, fusiones y ordenes múltiples tablas en Python.
Cada sección muestra hasta 10 registros por página. **Anterior** y **Siguiente**
navegan mediante cursor y reemplazan la página visible, sin acumular filas,
`OFFSET` ni conteo total. Cambiar sección, búsqueda o fechas vuelve a la primera
página; **Actualizar** conserva los criterios aplicados y también la reinicia.

No expongas contraseñas, hashes, tokens ni secretos. Enmascara correo, teléfono
e identificación que existan en instantáneas históricas. En móvil convierte los
eventos en tarjetas completas sin ocultar sus diferencias.

## 5. Cuenta técnica

Identifica al Administrador del sistema con `system_accounts`.

`system-administrator` es un Rol global `system_managed` sin Grupo. El bootstrap lo asigna a la cuenta técnica para representar su responsabilidad, pero la autoridad de privilegios sigue siendo la política `SystemAccount`; el Rol técnico no puede editarse/asignarse desde la consola ordinaria.

En producción su política efectiva es:

```text
requests:read
areas:manage
config:manage
```

No participa en aprobación/votación. En ambientes no productivos puede recibir los permisos activos necesarios para pruebas.

## 6. Inicio

Inicio es personal. Debe responder rápidamente:

- qué acciones esperan al usuario;
- qué solicitudes propias siguen en proceso;
- métricas de sus propias solicitudes;
- acceso contextual al detalle/acción pendiente.

Acciones actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## 7. Seguimiento

Crea una pantalla privada, de solo lectura, para seguimiento del equipo:

- Grupos activos;
- miembros derivados de Roles agrupados;
- Rol de cada miembro en ese Grupo;
- pendientes por usuario y Grupo;
- KPIs de miembros, usuarios con pendientes y carga total;
- búsqueda por usuario/grupo/rol;
- filtro de usuarios con pendientes.

Los Roles globales no crean membresía ni filas por Grupo en Seguimiento. No permitas editar IAM desde Seguimiento.

En la tabla operativa de Solicitudes, calcula un monto de Seguimiento separado
de `Expense.amount` para `MULTI_QUOTE`: máximo presentado cuando no hay votos,
monto del líder cuando existe uno único y máximo presentado cuando hay empate.
No selecciones proveedor ni ganador solo para completar esta visualización.

## 8. Sesión y rutas privadas

Una ruta privada sin sesión debe redirigir al Login antes de montar su contenido. Un 401 recibido con token almacenado debe limpiar la sesión y retornar al Login.

La sesión debe cerrarse después de 10 minutos sin actividad humana. Usa un
temporizador reiniciable por interacción real de puntero, teclado, touch o
scroll; al vencer elimina `access_token`, limpia cualquier hash privado y
renderiza Login. Antes de aceptar actividad al volver a una pestaña suspendida,
comprueba el tiempo transcurrido para no revivir una sesión vencida. FastAPI es
la autoridad final: `last_activity_at` expira a los 10 minutos y devuelve `401`.
`SESSION_IDLE_MINUTES` puede reducir el plazo entre 5 y 10, nunca ampliarlo.

Incluye en login y `GET /api/auth/me` los nombres ordenados de todos los Roles IAM
activos asignados al Usuario. La cabecera debe mostrar esos nombres, no traducir
el perfil técnico legacy `user.role` a capacidades como “Puede consultar”. Si el
Usuario ordinario no tiene Rol muestra **Sin rol asignado**; para una cuenta
técnica sin Rol visible usa **Administrador del sistema**.

Protege al menos Accesos y Seguimiento y aplica el mismo patrón a cualquier nueva pantalla privada.

Trata `/reset-password#token=...` como ruta pública de propósito limitado y
renderízala antes del Login. Captura el fragmento en memoria y retíralo de la URL
al cargar; el fragmento no debe viajar en la petición HTTP ni aparecer en logs
HTTP/CDN. No aceptes el token como sesión ni hagas auto-login al completar;
muestra confirmación y vuelve al Login.

## 9. Eficiencia de red

No implementes polling agresivo por defecto.

Política:

- carga al montar;
- refresh después de mutación/navegación/acción explícita;
- GET idénticos en vuelo se deduplican;
- repeticiones automáticas pueden usar caché corta;
- una mutación invalida caché;
- `POST`/`PUT`/`PATCH`/`DELETE` iniciados por la UI muestran antes del envío una
  pantalla global **Procesando…** no descartable;
- el resto de la aplicación queda `inert` para mouse, touch y teclado hasta que
  termina la última mutación concurrente;
- un `finally` libera el bloqueo en éxito, error HTTP, aborto o fallo de red;
- `/api/auth/activity` se mantiene silencioso y no activa el overlay;
- clicks/teclas explícitos pueden forzar lectura fresca;
- autenticación, adjuntos y URLs tokenizadas quedan fuera de la caché general.

## 10. Solicitudes

El formulario de nueva solicitud y **Registro directo** solo se muestran con
`requests:create`. El backend también exige ese permiso.

Contrato de clasificación:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M.

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

Una corrección conserva el tipo original.

Implementa `ApprovalPolicy` por Área/scope y bandas `(min_amount,max_amount]` sin
superposición dentro del mismo scope. Permite bandas adyacentes; una regla del
Área concreta precede al fallback `ALL`. `SIMPLE` evalúa su `amount` y
`MULTI_QUOTE` el máximo de todas sus opciones, calculado por FastAPI.

Admite `ANY`, `MAJORITY` y `ALL` para políticas con ronda, y `NO_APPROVAL`
para registro directo. La protección de overlap considera todas las modalidades
activas del scope. `NO_APPROVAL` exige targets de Rol/Grupo vacíos; las otras
modalidades exigen al menos un target válido.

Una política acota la población por `approver_role_ids` y
`approver_group_ids`, pero no concede autoridad. Incluye solo Usuarios activos
con `requests:approve` efectivo y excluye al Solicitante. Un Grupo expande los
Usuarios asignados a cualquiera de sus Roles activos y el resultado se
deduplica. No uses Cargo, `GroupMember`, nombres de perfiles ni reglas legacy por
correo. `approver_profile_codes` es solo metadata física legacy.

Sin política aplicable, `SIMPLE` crea la ronda con todos los Usuarios activos que
tengan permiso efectivo `requests:approve`, excluyendo al Solicitante, y usa
`MAJORITY`. La ausencia de política no desactiva IAM.

La creación de una solicitud nueva y la preparación de su ronda forman una sola
unidad de éxito. Si no existe otro participante elegible o el soporte pendiente
impide iniciar el flujo, revierte la solicitud, adjuntos y aprobaciones; no dejes
un `Expense` en estado intermedio. Envía notificaciones solo después del commit.

Para `MULTI_QUOTE`, exige soporte en cada opción y congela política, modalidad,
monto máximo evaluado, población y quórum. Sobre `N` invitados, `ANY=1`,
`MAJORITY=floor(N/2)+1` y `ALL=N`. Con política, alcanzar quórum y líder único
habilita cierre anticipado solo al Solicitante, pero conserva
`QUOTATION_VOTING`. Todos los invitados conservan **Votar o cambiar voto** hasta
que la factura cierre la solicitud. Un empate no habilita cierre. Sin política,
invita a toda la población IAM y exige todos los votos y un líder único, pero
también permanece en `QUOTATION_VOTING` hasta la factura; entonces el cierre
ordinario puede hacerlo el Solicitante, `system_accounts` o un delegado activo.
Ante quórum o población incompletos, o empate, el `POST` de cierre responde `409`
sin guardar factura ni fijar ganador. El cierre recalcula el resultado bajo
bloqueo y pasa directamente a `CLOSED`; nunca restaura una transición automática
a `APPROVED`.

Para una banda `NO_APPROVAL` aplicable, implementa **Registro directo → Gasto
sin aprobación** con Área, proveedor, ítem/descripción, monto positivo y factura.
El frontend consulta bandas elegibles y puede orientar `(min,max]`, pero el
backend vuelve a resolver Área sobre `ALL` y rechaza si la política dejó de ser
aplicable. Requiere `requests:create`.

Cuando una creación de Solicitud sea rechazada porque el Área y el monto pertenecen
a `NO_APPROVAL`, conserva el borrador y muestra **El área y el monto seleccionados
no requieren un proceso de aprobación. Usa Registro directo para registrar el
gasto y adjuntar la factura.** No expongas la ruta interna ni redirijas de forma
automática; resalta de manera visual y accesible el botón **Registro directo**
hasta que el Usuario elija otra navegación o vuelva a enviar.

Construye esta pantalla para teléfonos y tabletas. Entre 320 y 720 px apila la
introducción, los campos y las bandas en una columna; hasta 440 px apila también
la descripción y el rango dentro de cada banda. En 768, 820 y 1024 px puede usar
dos columnas si el contenido permanece legible. Área, monto, proveedor, factura,
ítem y acción principal siempre permanecen visibles; inputs, selects y botones
miden al menos 44 px, conservan foco visible y ajustan su contenido sin overflow
horizontal. Valida en Chrome a 320, 360, 390, 412, 440, 600, 640, 768, 820 y
1024 px.

Persiste un `DirectExpense` privado en `direct_expenses` con identidad visible,
autor, datos del gasto, metadata de factura y `approval_policy_id` histórico sin
FK destructiva. No crees `Expense`, aprobación, invitación, voto, acción
pendiente, `flow_id` ni estado. Archivo y fila son atómicos. El Usuario ordinario
lista/descarga solo sus registros; `system_accounts` puede consultar todos.

API canónica:

```text
GET  /api/direct-expenses/eligible-policies
POST /api/direct-expenses
GET  /api/direct-expenses
GET  /api/direct-expenses/{record_id}/invoice
```

## 11. Aprobación y revisión

Una aprobación pendiente admite:

```text
APPROVED
REJECTED
REVISION_REQUESTED
```

`REVISION_REQUESTED` requiere comentario útil y produce:

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

No concede edición al aprobador.

## 12. Capacidades por solicitud

Calcula y expón:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

No las conviertas en permisos globales.

Cerrar/facturar requiere estado compatible y requester, `system_accounts` o delegado activo de esa solicitud. Solo el solicitante administra la delegación ordinaria.

## 13. Documentos

Acepta PDF/JPEG/PNG/WEBP conforme a los límites configurados. Valida tipo, firma y tamaño; almacena de forma privada; sirve archivos a través del backend autorizado. Reemplazar factura conserva la versión anterior y su evento de auditoría.

## 14. Backend

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy separados;
- schemas Pydantic;
- servicios para lógica reusable;
- `get_db()` por request;
- Settings centralizados;
- lifespan sin migraciones;
- Alembic antes del servidor ASGI;
- response models explícitos;
- rate limiting de API autenticada;
- rate limiting sensible autenticado para emitir y cuota pública dedicada de 5
  intentos por 15 minutos para consumir el enlace de restablecimiento;
- headers `no-store` y headers de seguridad en respuestas API.

## 15. Persistencia Neon

Contrato:

```text
DATABASE_URL=<Neon PostgreSQL URL>
DATABASE_SCHEMA=administracion
```

Base objetivo: `ph_torre_delta`.

Neon recomienda una conexión directa para migraciones y `pg_dump`. Si el proceso de arranque ejecuta Alembic y solo existe una `DATABASE_URL`, utiliza una URL directa. No declares runtime pooled + migración directa hasta implementar, configurar y probar una URL de migración independiente.

Aislamiento:

- ORM con `MetaData(schema=DATABASE_SCHEMA)`;
- Alembic con schema explícito y `version_table_schema`;
- crear schema si falta;
- no usar startup `options=-csearch_path=...` con endpoint pooled;
- tipos Enum ORM con `inherit_schema=True`;
- SQL crudo con nombres de tabla calificados derivados de metadata;
- SQLite de tests permanece sin schema.

Cadena:

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
  ├→ 20260825_0012_keep_quotation_voting_open ───────────────┐
  └→ 20260827_0012_scoped_approval_policies                  │
     → 20260828_0013_direct_expenses ────────────────────────┤
                                                             └→ 20260828_0014_merge_main_layout_heads
                                                                → 20260831_0015_audit_change_feed
                                                                → 20260831_0016_retire_legacy_audit_tables
```

Toda creación, actualización o eliminación relevante se registra en
`audit_change_feed` con actor, timestamp, entidad, tipo de evento, instantánea y
valores `before/after`. La captura ocurre en la transacción original y omite
actualizaciones sin diferencias. Nunca incluye credenciales, hashes, tokens o
secretos.
Las listas GUI excluyen inactivos. Los formularios consultan recuperación por
cédula o clave/nombre y reactivan el ID existente con confirmación del usuario.

`0001` crea la instalación limpia. `0002` impide múltiples Grupos por Rol y dos
Roles del mismo Grupo por Usuario. `0003` garantiza un Cargo por Usuario. `0004`
permite Roles sin Grupo manteniendo la protección para Roles agrupados. `0009`
agrega `group_permissions` vacía, sin cambiar accesos existentes ni
`role_permissions`. `0010` agrega `users.password_reset_version`; `0011` agrega
el cupo opcional de Rol. La rama `20260825_0012` devuelve a
`QUOTATION_VOTING` solicitudes múltiples en `APPROVED` sin factura. La otra rama
usa `20260827_0012` para targets e instantáneas de política y `20260828_0013`
para `direct_expenses`. `20260828_0014` une ambas ramas mediante dos
`down_revision`, sin reescribirlas ni agregar una mutación de dominio.
`20260831_0015` crea y rellena el feed con SQL set-based; `20260831_0016`
verifica la copia y retira sin `CASCADE` ocho tablas de auditoría redundantes.
El downgrade de `0016` es irreversible y requiere respaldo previo más la imagen
anterior.

## 16. Correo

Producción: Brevo HTTPS API; nunca `console`, porque los cuerpos pueden contener contraseñas temporales o tokens y quedarían en logs. Docker local: `console` por defecto; SMTP únicamente mediante override explícito y autorizado.

Las pruebas unitarias usan fixtures temporales y no dejan solicitudes visibles. Para datos persistentes locales ejecuta `docker compose exec -T backend python -m app.demo_monitoring`; debe crear catálogo, Roles IAM, escenarios SIMPLE y MULTI_QUOTE sin enviar correo real. Ese comando muta datos y queda prohibido fuera del Compose PostgreSQL local aislado.

Invitación de usuario activo:

```text
correo
contraseña temporal
Cargo, si existe
permisos efectivos
URL pública
```

Cuando cambia el Cargo de un usuario activo, envía actualización con Cargo y permisos efectivos actuales. El cambio de Cargo no modifica esos permisos.

Restablecimiento administrativo:

- `POST /api/users/{user_id}/regenerate-password` solo con `config:manage`, para
  Usuario activo no técnico;
- token de propósito exclusivo, un uso y 30 minutos por defecto, configurable
  con `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`;
- emitir uno nuevo invalida los anteriores, pero no cambia contraseña,
  `must_change_password` ni sesiones; cambiar correo o `active` también invalida;
- el email contiene `/reset-password#token=...` y no contiene contraseñas;
- `POST /api/auth/reset-password` consume el token, almacena Argon2, establece
  `must_change_password=false`, revoca sesiones e invalida todos los enlaces;
- tras el commit, intenta notificar best-effort que la contraseña cambió, sin
  token/contraseña y sin revertir el cambio si esa notificación falla;
- no hay auto-login; respuesta, UI y auditoría nunca contienen token, contraseña
  o hash; los logs ordinarios tampoco, salvo el cuerpo local explícito de
  `EMAIL_MODE=console`, que se trata como sensible.

No declares atómica la entrega del correo con la base: un fallo del proveedor
antes del commit revierte la emisión y conserva el enlace anterior; si el
proveedor acepta y el commit falla, el enlace recibido queda inútil sin cambiar
el acceso y se debe reintentar. La garantía exactamente-una-vez requiere outbox.
La cuota pública de consumo es local por IP/proceso, limpia entradas por TTL, no
se coordina entre réplicas y depende de que la IP cliente sea confiable.

## 17. Frontend relevante

```text
frontend/src/expense-form.jsx
frontend/src/direct-expense-form.jsx
frontend/src/direct-expense-form.css
frontend/src/home-dashboard.jsx
frontend/src/user-tracking.jsx
frontend/src/iam-admin.jsx
frontend/src/iam-responsive.css
frontend/src/mobile-layout.css
frontend/src/action-state.css
frontend/src/auth-route-guard.js
frontend/src/request-governor.js
frontend/src/classification-admin.js
frontend/src/closure-delegation.jsx
```

Los bridges o campos de compatibilidad que existan en código no definen el diseño objetivo.

El layout completo funciona desde 320 px sin overflow horizontal de página. En
móvil conserva la navegación como banda táctil desplazable, representa la tabla
operativa de Solicitudes como tarjetas etiquetadas, apila formularios/tableros y
mantiene menús, modales, visores, Accesos y Seguimiento dentro del viewport. Usa
objetivos táctiles de al menos 44 px, alturas dinámicas y `safe-area`. No declares
responsive un cambio validado solo con build: comprueba navegador a 1180, 1024,
640, 440, 390 y 320 px.

El overlay **Procesando…** cubre el viewport completo en esa matriz, queda por
encima de todos los roots/modales, no genera overflow y no ofrece cierre mientras
el documento está inerte.

## 18. Definition of Done

Después de implementar cualquier cambio relevante revisa Constitución, Spec, Plan, Checklist, README, prompt maestro, docs, HISTORY y CHANGELOG.

Gates:

```text
docker compose exec -T backend alembic heads
# esperado: 20260831_0016 (head)

cd backend
.\.venv\Scripts\python.exe -m scripts.run_tests
.\.venv\Scripts\python.exe -m unittest tests.test_documentation_contract -v

cd ../frontend
npm ci
npm run build
```

El resultado debe poder comprenderse y reconstruirse leyendo únicamente la documentación vigente, sin contexto externo. Reporta solamente comandos realmente ejecutados y conserva como fallos abiertos cualquier diferencia entre contrato, código y pruebas.
