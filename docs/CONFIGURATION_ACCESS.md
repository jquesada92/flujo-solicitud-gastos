# Acceso a Configuración

## Objetivo

Separar claramente lectura, gestión de Área/Categoría y administración técnica, manteniendo **Accesos** como única superficie de identidades e IAM.

```text
config:read    → consultar Configuración sin modificarla
areas:manage   → administrar Área + Categoría
config:manage  → administración técnica system-only
```

Los nombres de Grupos, Cargos y Roles son datos persistidos en PostgreSQL. Nunca autorizan por sí mismos.

## Navegación canónica

### Administrador del sistema

Se identifica exclusivamente mediante `system_accounts`.

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / configuración técnica
```

**Usuarios/Personas y Organigrama no son entradas independientes.**

Toda creación/configuración de usuarios, estructura IAM y cargos se realiza dentro de **Accesos**.

### Visor de configuración

Un usuario ordinario puede recibir `config:read` por:

```text
permiso directo
Rol directo
Grupo → Rol
Cargo → Rol
```

Su navegación es:

```text
Configuración
├─ Accesos     (solo lectura)
├─ Áreas       (solo lectura, salvo areas:manage)
├─ Reglas      (solo lectura)
└─ Auditoría   (solo lectura)
```

No se reintroducen Usuarios/Personas ni Organigrama para el modo de lectura.

### Gestor de Áreas

Un usuario con `areas:manage` sin `config:read` obtiene:

```text
Configuración
└─ Áreas
```

Puede mutar Área + Categoría, pero no obtiene administración IAM, Reglas ni Auditoría técnica.

## Accesos como fuente única

`Configuración → Accesos` administra:

- Usuarios;
- creación, activación e inactivación;
- datos básicos necesarios para acceso;
- Grupos y miembros;
- Roles;
- Permisos;
- Cargos/Posiciones;
- Cargos asignados a Usuarios;
- Roles heredados por Grupo;
- Roles heredados por Cargo;
- Roles directos;
- Permisos directos;
- permisos efectivos y su origen.

No debe requerirse otra pantalla para completar estas operaciones.

Código legacy de `people` y `organization` puede permanecer internamente mientras se complete la migración, pero:

- no aparece en navegación normal;
- no es autoridad de configuración;
- no duplica lógica nueva;
- debe poder retirarse posteriormente sin pérdida funcional.

## Fronteras de permisos

### `config:manage`

Es **system-only**. Una asignación directa, por Rol, Grupo o Cargo no lo hace efectivo para un usuario que no esté en `system_accounts`.

### `config:read`

Permite lectura de configuración, no mutaciones.

Regla central:

```text
GET / HEAD + config:read   → permitido en recursos de Configuración
POST/PUT/PATCH/DELETE      → requiere permiso de escritura correspondiente
```

`config:read` no implica `config:manage` ni `areas:manage`.

### `areas:manage`

Protege mutaciones de `/api/areas` y de relaciones Área ↔ Categoría.

Puede heredarse por Rol/Grupo/Cargo o asignarse directamente.

## Bootstrap neutral

Alembic `0006` crea:

```text
Gestor de áreas → areas:manage
```

Alembic `0007` crea:

```text
Visor de configuración → config:read
```

El bootstrap de `0007` se basa en relaciones IAM existentes y no compara nombres concretos de Cargos, Grupos, Roles o Usuarios.

Después de la migración, `requests:approve` y `config:read` son capacidades independientes. Crear un nuevo aprobador no concede automáticamente visibilidad de Configuración.

## API

### IAM / Accesos

El backend expone lecturas de Usuarios, Grupos, Roles, Permisos y Cargos para actores autorizados. Las mutaciones requieren `config:manage` y la política de `system_accounts`.

Para `config:read`, la experiencia es solo lectura.

### Área + Categoría

API canónica:

```text
GET    /api/areas
POST   /api/areas
PATCH  /api/areas/{id}
GET    /api/areas/categories
POST   /api/areas/categories
PATCH  /api/areas/categories/{id}
POST   /api/areas/{id}/categories
POST   /api/areas/{id}/categories/{category_id}
DELETE /api/areas/{id}/categories/{category_id}
```

Las lecturas activas necesarias para solicitudes permanecen disponibles a usuarios autenticados. Los elementos inactivos pueden inspeccionarse por actores con visibilidad/configuración adecuada; las mutaciones requieren `areas:manage`.

## Sesión / frontend

`/api/auth/login` y `/api/auth/me` exponen:

```text
permission_codes
is_system_account
```

El bridge de Vite separa:

```text
canReadConfiguration → isSystemAdmin OR config:read
canConfigure         → isSystemAdmin
canManageAreas       → isSystemAdmin OR areas:manage
```

`config-readonly.js` activa la experiencia de solo lectura cuando existe `config:read` sin administración técnica.

`iam-admin.jsx` representa la consola editable de Accesos para System Admin.

## Navegación desde Accesos

Accesos se monta temporalmente mediante:

```text
#access-management
```

La topbar debe permanecer funcional.

Desde Accesos deben funcionar:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

Al seleccionar un destino distinto de Accesos:

1. se elimina `#access-management`;
2. se desmonta la consola IAM;
3. continúa la navegación del shell principal en el mismo clic.

Esto también aplica cuando el destino ya coincide con la pestaña React subyacente.

Abrir/cerrar únicamente el dropdown **Configuración** no abandona Accesos; seleccionar una opción navegable dentro de ese menú sí.

Implementación transitoria:

```text
frontend/src/access-navigation-bridge.js
```

Debe cargarse antes de `main.jsx`.

## Migraciones

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

- `0006`: `areas:manage` + Gestor de áreas.
- `0007`: `config:read` + Visor de configuración.
- `0008`: columnas físicas `expense_area` / `expense_category`.

## Pruebas de aceptación

Debe demostrarse que:

- System Admin ve **Accesos** y no ve Usuarios/Personas ni Organigrama como entradas independientes;
- creación/edición de usuarios sigue disponible dentro de Accesos;
- `config:read` puede consultar Accesos en modo solo lectura;
- `config:read` recibe 403 al intentar mutaciones;
- `areas:manage` administra Área + Categoría sin obtener IAM completo;
- `config:manage` continúa system-only;
- nombres organizacionales no participan en autorización;
- desde Accesos funcionan Inicio, Solicitudes, Facturas, Auditoría, Configuración y Salir;
- el caso de destino igual a la pestaña subyacente también cierra Accesos;
- `npm run build` y suite backend continúan exitosos.
