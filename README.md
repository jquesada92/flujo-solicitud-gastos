# Flujo de Control de Gastos

> Constitución vigente: **2.26.0**.

Aplicación web para registrar gastos directos y para crear, evaluar, aprobar,
votar, seguir, corregir, cancelar, cerrar y documentar solicitudes de gasto con
trazabilidad. El producto es neutral respecto al tipo de organización: la
estructura se configura como datos y los nombres organizacionales no forman
parte de la lógica de autorización.

> Revisión de soporte al desarrollo: **2026-08-28**. Antes de trabajar con una IA, leer [AGENTS.md](AGENTS.md). Los bloqueos que todavía no deben darse por resueltos están en [docs/KNOWN_RISKS.md](docs/KNOWN_RISKS.md).

## Contrato actual en una página

```text
Usuario activo
├─ requests:read (baseline)
├─ 0..1 Cargo organizacional
├─ 0..N Roles globales
└─ 0..N Roles agrupados (máximo 1 por Grupo)
      ├─ Permisos propios
      └─ Grupo asociado
            └─ Permisos heredables
```

Reglas clave:

- un Grupo puede existir sin Roles;
- cada Rol puede pertenecer a cero o un Grupo;
- un Rol sin Grupo es global;
- el Rol agrupado asignado al Usuario determina su membresía en ese Grupo;
- un Usuario puede tener máximo un Rol por Grupo y varios Roles globales;
- un Rol puede limitar opcionalmente su cantidad de Usuarios activos; los inactivos conservan la asignación sin consumir cupo;
- los Permisos de un Rol agrupado son la unión aditiva de los propios y los del Grupo;
- la ausencia a nivel de Rol hereda y no existe `DENY`;
- no hay permisos directos a Usuario y `GroupMember` aislado no autoriza;
- Cargo no concede permisos;
- un Usuario puede tener como máximo un Cargo;
- FastAPI es la autoridad de autorización;
- los cambios de acceso se guardan explícitamente con **Guardar cambios**;
- el restablecimiento administrativo envía un enlace de un solo uso, no una contraseña;
- Inicio es personal; Seguimiento es una vista de equipo de solo lectura;
- los participantes de aprobación/votación provienen de `requests:approve`
  efectivo, no de nombres de perfiles ni reglas legacy;
- una solicitud nueva sin ronda iniciable no queda persistida;
- una banda `NO_APPROVAL` permite registrar proveedor, ítem, monto y factura en
  `direct_expenses`, sin crear una solicitud o workflow;
- una pantalla privada sin sesión vuelve al Login;
- la aplicación es operable desde 320 px sin overflow horizontal de página;
- toda mutación iniciada por la UI muestra **Procesando…** y vuelve inerte la
  aplicación hasta que termina la última operación pendiente;
- el frontend no debe hacer polling agresivo ni repetir GET idénticos innecesariamente.

Ver [docs/CURRENT_PRODUCT_CONTRACT.md](docs/CURRENT_PRODUCT_CONTRACT.md).

## Terminología

| Término | Significado |
| --- | --- |
| Usuario | Cuenta autenticable |
| Grupo | Ámbito organizacional opcional con Permisos heredables y cero o más Roles |
| Rol | Conjunto de Permisos propios; si está agrupado suma los de su Grupo |
| Rol global | Rol sin Grupo |
| Permiso | Capacidad IAM atómica |
| Cargo / Posición | Metadato organizacional, sin autoridad IAM |
| Área | Contexto organizacional del gasto |
| Categoría | Naturaleza del bien/servicio |
| Inicio | Mis pendientes y mis solicitudes |
| Seguimiento | Carga del equipo por Grupo/miembro/Rol |
| Accesos | Administración de Usuarios, Grupos, Roles y Permisos |
| Gasto directo | Registro final bajo una banda `NO_APPROVAL`; no es una Solicitud |

## IAM

Permisos funcionales vigentes:

| Código | Capacidad |
| --- | --- |
| `requests:read` | Consultar y seguir solicitudes; baseline de usuario activo |
| `requests:create` | Crear una solicitud nueva o un gasto directo elegible |
| `requests:approve` | Aprobar, rechazar, votar y enviar a revisión cuando corresponda |
| `areas:manage` | Administrar Área + Categoría |
| `config:read` | Consultar Configuración sin mutar |
| `config:manage` | Administración técnica protegida |

`requests:close` es un registro inactivo de compatibilidad; el cierre se autoriza por solicitud.

### Resolución de permisos

```text
Usuario ordinario activo
= requests:read
+ Permisos propios de sus Roles globales activos
+ Permisos propios de sus Roles agrupados dentro de Grupos activos
+ Permisos heredados de esos Grupos activos
- config:manage
```

Para cada Rol agrupado se aplica `RolePermission ∪ GroupPermission`; los duplicados se colapsan y un checkbox propio desmarcado no niega la herencia. Un Grupo no entrega todos sus Roles a todos sus miembros: cada Usuario tiene como máximo un Rol concreto dentro de ese Grupo. Los Roles globales no crean membresía y una fila `GroupMember` sin Rol asignado no concede acceso.

La cuenta técnica se identifica con `system_accounts`. En producción su política efectiva es `requests:read + areas:manage + config:manage`. El Rol `Administrador del sistema` es global, técnico y protegido; el bootstrap lo asigna como representación de responsabilidad, pero la autoridad real sigue siendo `SystemAccount`.

Ver [docs/IAM_MODEL.md](docs/IAM_MODEL.md).

## Accesos

La consola muestra:

```text
Usuarios → Acceso por grupo → selector de Rol
         → Roles globales   → selección múltiple
Grupos   → Permisos heredables + Roles opcionales + miembros derivados
Roles    → Permisos propios + herencia visible + cupo opcional de Usuarios activos
Permisos → catálogo
```

Seleccionar opciones no guarda inmediatamente. La persistencia ocurre al pulsar **Guardar cambios**. Al cambiar de usuario/grupo con cambios pendientes se solicita confirmación.

En la lista de Usuarios, cada tarjeta muestra debajo del correo todos los Roles que tiene asignados; la línea se omite cuando no existe ninguna asignación y los Roles inactivos conservados se identifican explícitamente.

Los miembros de un Grupo se derivan de las asignaciones de Roles agrupados y son informativos; `GroupMember` no es una fuente de autorización. Cargo tampoco forma parte de la autorización de esta consola.

Quitar un Rol de un Grupo lo convierte en global sin borrar sus asignaciones de Usuario ni Permisos propios; pierde solo la herencia. Vincular Roles globales a un Grupo se rechaza si eso produciría más de un Rol del mismo Grupo para algún Usuario.

El editor de Rol permite dejarlo sin límite o definir un máximo entero positivo de Usuarios activos. La lista muestra ocupación y máximo; un Rol lleno no puede asignarse a otro Usuario activo. Los Usuarios inactivos conservan el Rol sin consumir cupo y su reactivación se rechaza mientras no exista capacidad. Tampoco se puede reducir el máximo por debajo de la ocupación activa.

Después de crear un Rol correctamente, la lista incorpora el registro y el
editor vuelve a **Crear rol** vacío, sin selección, recuperación ni ID. La
siguiente alta vuelve a usar `POST` y no puede sobrescribir el Rol anterior. Una
edición o reactivación conserva su `PATCH`; si el request falla, el borrador se
mantiene.

La consola debe conservar estados, acciones y contenido legibles desde 320 px, envolver textos largos y apilar paneles cuando no quepan. La validación manual mínima cubre 1180, 1024, 640, 440, 390 y 320 px. El contrato multirol descrito aquí es normativo; la divergencia actual de `UsersPanel` está registrada como bloqueo conocido y no debe convertirse en una regla documental.

La ficha de un Usuario activo no técnico ofrece **Regenerar contraseña**. La
acción envía un enlace de restablecimiento, requiere confirmación y
`config:manage`, se ejecuta de inmediato como acción de seguridad separada de
**Guardar cambios** y no modifica el borrador de Roles. El correo contiene un
enlace válido durante 30 minutos por defecto y nunca una contraseña.

## Inicio y Seguimiento

### Inicio

Vista rápida de la persona conectada:

- acciones que requieren su atención;
- solicitudes propias en proceso;
- métricas personales;
- modal contextual para aprobar, votar, corregir o cerrar cuando exista una tarea vigente.

### Seguimiento

Vista de equipo de solo lectura:

- Grupos activos;
- miembros y sus Roles agrupados;
- pendientes por usuario;
- pendientes agregados por Grupo;
- búsqueda y filtro de usuarios con pendientes.

Los Roles globales no generan membresía en Seguimiento.

La tabla operativa de Solicitudes evita mostrar `0` en rondas `MULTI_QUOTE`: sin
votos usa el monto máximo presentado, con líder único usa el monto de la opción
que va ganando y ante empate usa nuevamente el máximo. Es un valor informativo
separado del monto financiero seleccionado al cerrar.

## Solicitudes y registro directo

El formulario se muestra únicamente a quien tenga `requests:create`. Tener `requests:read` no es suficiente.

Contrato canónico:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M configurable.

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

Las correcciones conservan el tipo original.

**Configuración → Reglas** define bandas `(mínimo,máximo]` por Área, sin overlap
dentro del mismo scope; el Área concreta precede a `ALL`. Cada regla selecciona
Roles/Grupos y una modalidad, pero los targets solo acotan Usuarios que ya tienen
`requests:approve` efectivo. Seleccionar un Grupo expande los Usuarios asignados
a sus Roles activos y deduplica coincidencias. Cargo, `GroupMember`, nombres y
`approver_profile_codes` no conceden acceso.

Las modalidades con ronda son `ANY`, `MAJORITY` y `ALL`. `NO_APPROVAL` no admite
targets ni abre una ronda. La prohibición de overlap también aplica entre reglas
de modalidades distintas dentro del mismo Área/scope.

`SIMPLE` evalúa su monto. `MULTI_QUOTE` evalúa el máximo de todas sus opciones.
La regla aplicada, modalidad, monto y quórum quedan congelados por ronda. Si no
hay regla, `SIMPLE` usa toda la población IAM y `MAJORITY`; la ausencia de
política nunca desactiva IAM. Si no existe otro participante elegible o el flujo
no puede prepararse, la API no conserva la solicitud ni su soporte.

En `MULTI_QUOTE`, `ANY`, `MAJORITY` y `ALL` requieren 1,
`floor(N/2)+1` y `N` votos. Con regla, quórum y líder único habilitan cierre
anticipado solo al Solicitante, pero la ronda continúa abierta para que todos los
invitados voten o cambien hasta que la factura la cierre. Sin regla se requieren
todos los votos y un líder único, pero la ronda también permanece en
`QUOTATION_VOTING`; entonces el cierre ordinario puede hacerlo el Solicitante,
`system_accounts` o un delegado activo. Ante quórum o población incompletos, o
empate, el `POST` de cierre responde `409` sin guardar factura ni fijar ganador.
La factura lleva directamente a `CLOSED`. Ver
[docs/MULTI_QUOTE_VOTING.md](docs/MULTI_QUOTE_VOTING.md).

Cuando una banda `NO_APPROVAL` cubre el Área y monto, **Registro directo → Gasto
sin aprobación** permite guardar Área, proveedor, ítem/descripción, monto y
factura. FastAPI revalida la regla y crea un `DirectExpense` privado; nunca crea
`Expense`, Solicitud, aprobación, voto o acción pendiente. Un Usuario ordinario
consulta sus propios registros y facturas; `system_accounts` puede consultar
todos. Ver [docs/DIRECT_EXPENSES.md](docs/DIRECT_EXPENSES.md).

En **Registro directo**, teléfonos de 320 a 720 px presentan introducción,
campos y bandas en una columna; hasta 440 px cada banda apila también su rango.
En tabletas de 768, 820 y 1024 px se permiten dos columnas cuando siguen
legibles. Área, monto, proveedor, factura, ítem y acción no se ocultan; inputs,
selects y botones miden al menos 44 px. La matriz específica es 320, 360, 390,
412, 440, 600, 640, 768, 820 y 1024 px, sin overflow, recortes o pérdida de foco.

## Revisión, corrección y cierre

`REVISION_REQUESTED` interrumpe la ronda, lleva la solicitud a `NEEDS_REVISION`, expira decisiones pendientes restantes y crea `CORRECT_REQUEST` para el solicitante.

Capacidades por recurso:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

El cierre ordinario depende de ser Solicitante, Administrador del sistema o
delegado activo; no depende de un permiso global. En una votación configurada
con quórum y líder único, el cierre anticipado desde `QUOTATION_VOTING`
pertenece exclusivamente al Solicitante original. En el fallback sin regla,
esas relaciones ordinarias pueden cerrar desde `QUOTATION_VOTING` solo después
de todos los votos y con líder único.

## Sesión y frontend

Login y `GET /api/auth/me` incluyen `role_names` con todos los Roles IAM activos
asignados. La cabecera muestra esos nombres —varios si corresponde— y nunca las
etiquetas de capacidad del perfil técnico legacy como “Puede consultar”. Sin Rol
ordinario muestra **Sin rol asignado**; una cuenta técnica sin Rol visible muestra
**Administrador del sistema**.

### Layout móvil

Desde 320 px, la navegación principal permanece disponible como una banda táctil
desplazable y marca la vista actual. Los formularios, filtros, tableros, Accesos,
Seguimiento y Registro directo se adaptan; la consulta de Solicitudes cambia la
tabla ancha por tarjetas con etiquetas visibles. Menús, modales y visores
permanecen dentro del viewport, usan altura dinámica y respetan las áreas seguras
del dispositivo.

La pantalla global **Procesando…** cubre el viewport completo desde 320 px,
respeta `safe-area` y queda por encima de navegación, Accesos y modales. No tiene
cierre: mientras exista una mutación pendiente, el resto de la aplicación queda
`inert` para mouse, touch y teclado.

La implementación transversal vive en `frontend/src/mobile-layout.css`; los
ajustes propios de Accesos, Inicio, Seguimiento y Registro directo permanecen
junto a sus módulos, incluido `frontend/src/direct-expense-form.css`. La
validación manual global cubre 1180, 1024, 640, 440, 390 y 320 px; Registro
directo amplía su matriz como se indica arriba. En ambos casos se exige ausencia
de overflow horizontal, controles recortados y pérdida de foco visible.

Los hashes privados como `#access-management` y `#user-tracking` requieren sesión. Sin token se limpia la ruta privada y se muestra Login; un `401` invalida la sesión almacenada.

Después de 10 minutos sin actividad humana, el frontend elimina el token,
limpia la ruta privada y muestra **Iniciar sesión**. FastAPI aplica el mismo
límite sobre `last_activity_at` y devuelve `401`; por eso una pestaña suspendida
o un temporizador retrasado no prolongan la sesión. `SESSION_IDLE_MINUTES=10` es
el valor soportado por defecto y solo admite un plazo más estricto entre 5 y 10.

`/reset-password#token=...` es una ruta pública limitada al cambio de
contraseña. El token tiene propósito exclusivo, un solo uso y vigencia
configurable; emitir uno nuevo, cambiar el correo o cambiar `active` invalida los
enlaces anteriores sin cambiar la contraseña ni las sesiones. El fragmento no se
envía en solicitudes HTTP ni a logs HTTP/CDN: la SPA lo captura en memoria y lo
retira de la URL al cargar. Al consumirlo, el backend almacena Argon2, limpia
`must_change_password`, revoca sesiones, invalida todos los enlaces y devuelve al
Login sin iniciar sesión automáticamente. Después del commit intenta una
notificación best-effort de contraseña cambiada, sin token ni contraseña.

El frontend aplica una política transversal de requests:

- carga inicial al montar;
- GET idénticos concurrentes deduplicados;
- caché corta para repeticiones automáticas;
- mutaciones invalidan lecturas;
- `POST`/`PUT`/`PATCH`/`DELETE` muestran un overlay global bloqueante hasta que
  finaliza la última mutación concurrente;
- el sync silencioso de `/api/auth/activity` no muestra ese overlay;
- interacción explícita puede forzar datos frescos;
- sin polling sub-segundo.

Ver [docs/FRONTEND_RUNTIME.md](docs/FRONTEND_RUNTIME.md).

## Persistencia

```text
Database: ph_torre_delta
Schema:   administracion
```

Todas las tablas, `alembic_version` y objetos propios de aplicación viven bajo `administracion`. El runtime es compatible con endpoints pooled porque no envía `search_path` como startup option y califica el schema explícitamente. Sin embargo, el contenedor ejecuta Alembic con la misma `DATABASE_URL`; hasta separar la conexión de migración, los servicios que usan `backend/scripts/start.sh` deben recibir una conexión directa de Neon. Ver [docs/NEON_SETUP.md](docs/NEON_SETUP.md).

Cadena actual:

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
```

Usuarios, Áreas, Roles y Grupos conservan versiones temporales en tablas
separadas. El alta abre una versión desde el mismo `created_at`; cada cambio
cierra la anterior y abre otra con los valores JSON actuales. Un índice único
parcial impide dos versiones abiertas para la misma entidad.
Cada versión registra actor, timestamp del evento, tipo y diferencias
`before/after` por campo; procesos automáticos usan un actor `SYSTEM:*`.

Los catálogos de Usuario, Área, Rol y Grupo muestran solo activos. Al volver a
introducir la cédula, código o nombre de una entidad inactiva, el formulario
ofrece recuperar sus datos y reactivarla con el mismo ID.

`0002` fija que un Rol no puede pertenecer a más de un Grupo y un Usuario no
puede tener dos Roles del mismo Grupo. `0003` fija un Cargo por Usuario. `0004`
permite Roles globales sin relajar la restricción de un Rol por Grupo. `0009`
agrega Permisos heredables de Grupo sin backfill de grants y conserva
`role_permissions`. `0010` agrega `users.password_reset_version`; `0011` agrega
el `max_users` opcional. La rama `20260825_0012` devuelve a votación solicitudes
múltiples antiguas aprobadas sin factura. La otra rama usa `20260827_0012` para
targets e instantáneas de política y `20260828_0013` para `direct_expenses`.
`20260828_0014` une ambas ramas inmutables mediante dos `down_revision` y no
agrega una mutación de dominio.

## Despliegue

El despliegue de producción es una acción explícita y manual. Solo se autoriza desde `main`, mediante **Deploy production**, escribiendo `DEPLOY` y siguiendo [docs/VALIDACION_PRODUCCION.md](docs/VALIDACION_PRODUCCION.md). No ejecutar hooks, migraciones ni pruebas mutantes contra producción desde una sesión de desarrollo.

El `CMD` de la imagen ejecuta `backend/scripts/start.sh`, que aplica este orden:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app --host 0.0.0.0 --port ${PORT:-8000}
```

Frontend Vercel usa `VITE_API_URL=<HTTPS Render API>`.

Variables relevantes:

```text
DATABASE_URL
DATABASE_SCHEMA=administracion
SECRET_KEY
ANALYTICS_HASH_KEY
SESSION_IDLE_MINUTES=10
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS
PUBLIC_URL
EMAIL_MODE
```

Correo de producción: Brevo HTTPS API; `EMAIL_MODE=console` no es válido operacionalmente porque puede escribir contraseñas temporales y tokens en logs. Los restablecimientos usan un template propio con enlace y sin contraseña. Docker local usa console por defecto; cualquier entrega real requiere autorización y configuración explícitas.

## Desarrollo local

Camino soportado: Docker Desktop con Compose v2. Antes de tocar archivos, conservar la rama actual y revisar `git status --short --branch`; no cambiar a `main`, hacer `pull`, limpiar cambios o ejecutar comandos destructivos como parte del arranque.

```powershell
docker compose up -d --build
docker compose ps
```

La aplicación queda en `http://127.0.0.1:3000`; el API y PostgreSQL no se publican directamente al host. Compose fuerza PostgreSQL local y `EMAIL_MODE=console`, aunque exista un archivo backend. No cargar `.env` de producción ni una URL de Neon.

`demo_monitoring` crea cinco escenarios persistentes SIMPLE/MULTI_QUOTE y **muta la base**. Ejecutarlo solo cuando esos datos sean necesarios y exclusivamente dentro de este Compose local:

```powershell
docker compose exec -T backend python -m app.demo_monitoring
```

Ver [docs/VALIDACION_LOCAL.md](docs/VALIDACION_LOCAL.md).

Validación:

```powershell
docker compose exec -T backend alembic heads
# esperado: 20260828_0014 (head)

cd backend
.\.venv\Scripts\python.exe -m scripts.run_tests

cd ..\frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=moderate
```

La suite backend usa principalmente SQLite temporal; el arranque y la prueba funcional del stack Docker ejercitan PostgreSQL 16. Para ejecutar tests fuera de Docker se requiere Python 3.12 y un `.venv` con las dependencias instaladas. Node.js 22 es la referencia del build frontend.

## Arquitectura

```text
frontend/  React + Vite
backend/   FastAPI + SQLAlchemy + Alembic
Neon       PostgreSQL
Render     backend de producción
Vercel     frontend de producción
```

Componentes frontend relevantes:

```text
expense-form.jsx
direct-expense-form.jsx
direct-expense-form.css
home-dashboard.jsx
user-tracking.jsx
iam-admin.jsx
auth-route-guard.js
request-governor.js
classification-admin.js
closure-delegation.jsx
```

## Documentación

Para uso operativo diario consulta la [Guía para Solicitantes y Junta
Directiva](docs/GUIA_USUARIO_FINAL.md).

Empieza por:

1. [AGENTS.md](AGENTS.md), para límites operativos de personas y agentes automatizados.
2. [.specify/memory/constitution.md](.specify/memory/constitution.md), autoridad funcional superior.
3. [`specs/`](specs/), autoridad funcional por feature.
4. [docs/CURRENT_PRODUCT_CONTRACT.md](docs/CURRENT_PRODUCT_CONTRACT.md).
5. [PROMPT_RECONSTRUCCION.md](PROMPT_RECONSTRUCCION.md).
6. [docs/README.md](docs/README.md).
7. [docs/KNOWN_RISKS.md](docs/KNOWN_RISKS.md), para no confundir defectos actuales con el contrato.

La documentación normativa debe reflejar el producto vigente y no mantener diseños sustituidos como opciones activas.
