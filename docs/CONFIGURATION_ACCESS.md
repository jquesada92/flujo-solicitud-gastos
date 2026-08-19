# Acceso a Configuración

## Objetivo

Separar tres capacidades distintas:

```text
config:read    → consultar toda la configuración sin modificarla
areas:manage   → administrar únicamente Áreas y Categorías
config:manage  → administración técnica completa del sistema
```

La identidad o el acceso **no depende de nombres concretos de la organización**. Los nombres de Grupos, Cargos y Roles son datos persistidos en PostgreSQL.

## Fronteras

### Administrador del sistema

Se identifica exclusivamente mediante `system_accounts`.

Puede acceder y modificar:

```text
Configuración
├─ Usuarios
├─ Organigrama
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / configuración técnica
```

Su capacidad técnica es `config:manage`. Este permiso es **system-only**: una asignación IAM ordinaria no lo hace efectivo para un usuario que no pertenece a `system_accounts`.

En producción su IAM máximo incluye:

```text
requests:read
areas:manage
config:manage
```

Las excepciones de cancelación/corrección/cierre siguen siendo capacidades por recurso y no amplían el IAM financiero.

### Visor de configuración

Un usuario ordinario puede recibir:

```text
config:read
```

por cualquiera de las vías IAM canónicas:

```text
permiso directo
Rol directo
Grupo → Rol
Cargo → Rol
```

Puede consultar todas las pantallas:

```text
Configuración
├─ Usuarios
├─ Organigrama
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría
```

pero no puede crear, modificar, activar, desactivar, asignar, eliminar ni regenerar credenciales.

La separación se aplica en dos niveles:

1. El frontend muestra las vistas en modo **SOLO LECTURA** y elimina/deshabilita controles de mutación.
2. FastAPI sigue siendo la autoridad final: `config:read` solo puede satisfacer guards de configuración en `GET`/`HEAD`. Cualquier `POST`, `PUT`, `PATCH` o `DELETE` continúa requiriendo el permiso de escritura correspondiente.

### Gestor de Áreas

Un usuario ordinario puede recibir:

```text
areas:manage
```

por cualquiera de las vías IAM canónicas.

Su ámbito editable queda limitado a Áreas/Categorías. Este permiso no concede administración de Usuarios, Organigrama, Accesos, Reglas ni Auditoría técnica.

## Configurar colectivos como Administración o Junta Directiva

Esos nombres son datos del cliente y nunca se comparan en runtime.

Alembic `0007` crea un Rol neutral:

```text
Visor de configuración
└─ config:read
```

La migración realiza un **bootstrap estructural único** para el despliegue PH actual. En vez de copiar acceso a personas concretas:

- los Cargos que actualmente heredan `requests:approve` reciben el Rol `Visor de configuración` mediante `position_roles`;
- los Grupos que actualmente heredan `requests:approve` reciben el mismo Rol mediante `group_roles`;
- únicamente cuando la aprobación fue asignada directamente al usuario se usa una asignación directa del Rol como fallback.

Así, cuando cambia la persona que ocupa un Cargo de la estructura vigente, `config:read` sigue al Cargo y no al nombre de la persona. El bootstrap no compara nombres de Cargo, Grupo, Rol ni usuario.

Después de la migración, `requests:approve` y `config:read` son capacidades independientes. Crear un Cargo/Grupo aprobador nuevo **no** concede automáticamente visibilidad de Configuración; el Administrador decide esa relación desde IAM.

## API

### Lectura de configuración

Un actor con `config:read` puede ejecutar lecturas de IAM, Usuarios, Organigrama, Reglas y Auditoría que históricamente estaban detrás de `config:manage`.

La regla central es:

```text
GET / HEAD + config:read   → permitido
mutación + config:read     → 403
mutación + config:manage   → permitido según el endpoint
```

### Áreas

La lectura activa se mantiene disponible para usuarios autenticados cuando es necesaria para solicitudes.

`include_inactive=true` revela elementos inactivos a actores que puedan inspeccionar configuración (`config:read`, `config:manage` o `areas:manage`).

Las mutaciones siguen exigiendo `areas:manage`:

```text
POST   /api/areas
PATCH  /api/areas/{id}
POST   /api/areas/categories
PATCH  /api/areas/categories/{id}
POST   /api/areas/{id}/categories
POST   /api/areas/{id}/categories/{category_id}
DELETE /api/areas/{id}/categories/{category_id}
```

## Sesión / frontend

`/api/auth/login` y `/api/auth/me` exponen los permisos efectivos en `permission_codes`.

Para compatibilidad temporal con el shell React legacy, `can_configure=true` significa que el usuario puede **ver** Configuración cuando tiene `config:read` o `config:manage`. Este flag no autoriza mutaciones; el backend siempre vuelve a comprobar los permisos canónicos.

El bridge de Vite separa explícitamente:

```text
canReadConfiguration → config:read o System Admin
canConfigure         → System Admin / config:manage
canManageAreas       → areas:manage o System Admin
```

`config-readonly.js` detecta:

```text
config:read presente
config:manage ausente
```

y activa la experiencia de solo lectura. También intercepta el botón **Accesos** para mostrar un visor de Usuarios, Grupos, Roles, Permisos y Cargos sin controles de edición.

## Migraciones

### 0006 — Gestión de Áreas

```text
20260818_0006_area_management_permission.py
```

Crea `areas:manage` y el Rol neutral `Gestor de áreas`.

### 0007 — Lectura de Configuración

```text
20260819_0007_configuration_read_access.py
```

Responsabilidades:

- crear/upsert `config:read`;
- crear `configuration-viewer / Visor de configuración`;
- asociar `config:read` al Rol;
- hacer bootstrap estructural sobre Cargos/Grupos que actualmente heredan `requests:approve`;
- usar asignación directa solamente como fallback para aprobadores directos;
- excluir cuentas técnicas de ese fallback;
- no comparar nombres organizacionales en runtime ni en el bootstrap.

Cadena:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007
```

## Pruebas de aceptación

Debe demostrarse que:

- System Admin puede ver y editar todas las pantallas de Configuración;
- usuario con `config:read` puede ver Usuarios, Organigrama, Accesos, Áreas, Reglas y Auditoría;
- usuario con `config:read` recibe 403 al intentar mutaciones de configuración;
- el frontend de `config:read` no presenta controles efectivos de edición;
- `config:read` no concede `config:manage`;
- `config:manage` continúa siendo system-only;
- usuario con `areas:manage` puede administrar Áreas sin obtener administración técnica completa;
- los nombres de Junta Directiva, Administración u otros colectivos no son autoridad runtime;
- `npm run build` y la suite backend continúan exitosos.
