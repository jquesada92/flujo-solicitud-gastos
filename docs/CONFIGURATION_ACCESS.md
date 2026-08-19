# Acceso a Configuración

## Objetivo

Separar la **administración técnica del sistema** de la **gestión organizacional de Áreas**.

La identidad o acceso no depende de nombres concretos de la organización.

## Fronteras

### Administrador del sistema

Se identifica exclusivamente mediante `system_accounts`.

Puede acceder a:

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

### Gestor de Áreas

Un usuario ordinario puede recibir:

```text
areas:manage
```

por cualquiera de las vías IAM canónicas:

```text
permiso directo
Rol directo
Grupo → Rol
Cargo → Rol
```

Su menú queda:

```text
Configuración
└─ Áreas
```

No recibe Usuarios, Organigrama ni Accesos.

## Configurar colectivos como Administración o Junta Directiva

Estos nombres son datos del cliente y nunca se comparan en runtime.

Alembic `0006` crea un Rol neutral:

```text
Gestor de áreas
└─ areas:manage
```

Después del deploy, el Administrador del sistema puede asociarlo desde **Configuración → Accesos** a cualquier Grupo o Cargo configurado, por ejemplo:

```text
Grupo Administración → Gestor de áreas
Grupo Junta Directiva → Gestor de áreas
```

El ejemplo describe una configuración posible; el producto no presupone esos nombres.

## API

### Áreas

Lectura activa se mantiene disponible para usuarios autenticados cuando es necesaria para solicitudes.

Las operaciones de configuración usan `areas:manage`:

```text
POST   /api/areas
PATCH  /api/areas/{id}
POST   /api/areas/categories
PATCH  /api/areas/categories/{id}
POST   /api/areas/{id}/categories
POST   /api/areas/{id}/categories/{category_id}
DELETE /api/areas/{id}/categories/{category_id}
```

`include_inactive=true` solo revela elementos inactivos a actores con `areas:manage`.

### Administración técnica

IAM, Usuarios, Organigrama, Reglas y Auditoría técnica permanecen bajo `config:manage`.

El resolver IAM elimina `config:manage` de usuarios ordinarios, incluso si una relación legacy todavía lo referencia.

## Sesión / frontend

`/api/auth/login` y `/api/auth/me` exponen:

```json
{
  "is_system_account": true,
  "permission_codes": ["requests:read", "areas:manage", "config:manage"]
}
```

El frontend usa:

```text
is_system_account → UX de administración técnica
permission_codes includes areas:manage → UX de Áreas
```

El backend sigue siendo autoridad final.

`iam-admin.jsx` solo inyecta **Accesos** cuando el menú se marca como perteneciente al System Admin.

## Migración 0006

```text
20260818_0006_area_management_permission.py
```

Responsabilidades:

- crear/upsert `areas:manage`;
- actualizar la descripción de `config:manage` como técnica/system-only;
- crear `area-manager / Gestor de áreas`;
- asociar `areas:manage` al Rol;
- no asignar ese Rol a usuarios/grupos/cargos por nombre.

Cadena:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006
```

## Pruebas de aceptación

Debe demostrarse que:

- System Admin ve Usuarios/Organigrama/Accesos/Áreas;
- usuario con `areas:manage` ve Áreas solamente;
- usuario ordinario sin `areas:manage` no ve Configuración;
- manipular frontend no permite acceder a IAM técnico;
- `config:manage` legacy de usuario ordinario no es efectivo;
- los Grupos/Cargos configurados reciben Áreas solo a través de Roles/Permisos persistidos.