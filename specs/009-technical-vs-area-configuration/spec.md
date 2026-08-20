# Especificación funcional — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución vigente:** 2.9.0  
**Evolución:** la navegación original de esta feature fue consolidada posteriormente por Feature 011.

## Objetivo

Separar la administración técnica del sistema de la configuración organizacional de Área + Categoría.

Frontera vigente:

```text
Administrador del sistema (system_accounts)
→ Accesos
→ Áreas
→ Reglas / Auditoría técnica

Usuario con config:read
→ Accesos (solo lectura)
→ Áreas (solo lectura salvo areas:manage)
→ Reglas / Auditoría (solo lectura)

Usuario con areas:manage sin config:read
→ Áreas solamente
```

**Usuarios/Personas y Organigrama ya no son pantallas independientes**; Feature 011 los consolidó funcionalmente dentro de Accesos.

## F-009-01 — `config:manage` es system-only

`config:manage` representa administración técnica de escritura.

Solo una cuenta persistida en `system_accounts` puede tener `config:manage` como permiso efectivo.

Una asignación directa, Rol, Grupo o Cargo que contenga `config:manage` para un usuario ordinario no lo convierte en Administrador del sistema.

## F-009-02 — `areas:manage` es configurable

```text
areas:manage
```

autoriza a administrar:

- Áreas;
- Categorías;
- activación/desactivación;
- relación Área ↔ Categoría;
- configuración de elementos inactivos según contrato vigente.

Puede heredarse mediante:

```text
Usuario → Permiso directo
Usuario → Rol → areas:manage
Usuario → Grupo → Rol → areas:manage
Usuario → Cargo → Rol → areas:manage
```

## F-009-03 — `config:read` separa lectura de escritura

Alembic `0007` incorpora `config:read` para permitir consulta de Configuración sin conceder mutaciones.

```text
config:read    → lectura
config:manage  → escritura técnica system-only
areas:manage   → escritura de Área + Categoría
```

Feature 011 reutiliza **Accesos** como la superficie de lectura de Usuarios/Grupos/Roles/Permisos/Cargos.

## F-009-04 — Sin autorización por nombres

Runtime no debe comprobar nombres como Administración, Junta Directiva, Presidente, Tesorero o Administrador.

La organización otorga capacidades mediante relaciones persistidas.

## F-009-05 — Menú del Administrador del sistema

Estado vigente tras Feature 011:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría
```

La identidad se obtiene de `system_accounts`, no de `UserRole.ADMIN`, email, Cargo o nombre.

## F-009-06 — Menú de un Gestor de Áreas

Un usuario con `areas:manage` pero sin `config:read`:

- ve Configuración;
- ve Áreas;
- no obtiene Accesos, Reglas o Auditoría por esa capacidad;
- no puede mutar IAM aunque manipule el frontend.

## F-009-07 — Backend authoritative

Las mutaciones de `/api/areas` usan `areas:manage`.

Las mutaciones IAM/técnicas continúan detrás de `config:manage` system-only.

Lecturas de configuración admitidas por `config:read` no conceden escritura.

Ocultar un botón no constituye autorización.

## F-009-08 — Identidad técnica explícita

Login y `/api/auth/me` exponen:

```text
is_system_account
permission_codes
```

El frontend puede usar esos datos para UX; backend revalida endpoints sensibles.

## F-009-09 — Migraciones

### `0006`

`20260818_0006_area_management_permission.py`:

- crea/activa `areas:manage`;
- crea Rol neutral `Gestor de áreas`;
- no asigna el Rol por nombre organizacional.

### `0007`

`20260819_0007_configuration_read_access.py`:

- crea/activa `config:read`;
- crea Rol neutral `Visor de configuración`;
- realiza bootstrap estructural sin autorización runtime por nombres.

Cadena vigente del proyecto continúa hasta `0008` por la normalización física de Área/Categoría.

## F-009-10 — Categorías activas en asignación

- Maestro de Categorías muestra activas e inactivas;
- **Categorías por área** muestra solo `active=true`;
- contador usa la misma población visible;
- checkbox modifica borrador local;
- relación cambia solo al pulsar Guardar;
- desactivar Categoría no borra relaciones históricas.

## F-009-11 — Accesos integrado al shell

La consola Accesos:

- conserva visible la topbar;
- usa layout/tarjetas del shell principal;
- evita overflow de nombres/correos;
- presenta **Recargar** como refresco;
- diferencia botones deshabilitados y estado dirty.

La navegación completa desde Accesos se especifica y prueba en **Feature 011**.

## Seguridad

- `config:manage` system-only;
- `config:read` read-only;
- `areas:manage` default deny si no existe asignación;
- `system_accounts` es la fuente de identidad técnica;
- ninguna autorización depende de Cargo/título/nombre;
- Accesos no sustituye validaciones backend.

## Relación con Feature 011

Feature 009 definió la separación de capacidades. Feature 011 evolucionó la superficie de navegación:

```text
Usuarios + Organigrama + Accesos
→ consolidación
→ Accesos
```

Ante cualquier discrepancia de navegación, prevalecen Constitución 2.9.0 y Feature 011.

## Fuera de alcance

- asignar automáticamente Roles a colectivos por nombre;
- retirar físicamente toda deuda legacy;
- rediseñar completamente el shell;
- introducir multi-tenancy;
- cambiar reglas de aprobación/corrección/cierre.
