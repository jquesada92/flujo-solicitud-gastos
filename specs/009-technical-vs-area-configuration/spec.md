# Especificación funcional — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución:** 2.8.0

## Objetivo

Separar la administración técnica del sistema de la configuración organizacional de Áreas.

Modelo objetivo:

```text
Administrador del sistema (system_accounts)
→ Usuarios
→ Organigrama
→ Accesos / IAM
→ Áreas
→ Reglas / Auditoría técnica

Usuario ordinario con areas:manage
→ Áreas solamente

Usuario ordinario sin areas:manage
→ sin menú de Configuración
```

La organización puede otorgar `areas:manage` mediante Rol, Grupo, Cargo/Posición o asignación directa. Nombres como **Administración** o **Junta Directiva** son datos configurados y nunca condiciones de autorización en código.

## F-009-01 — `config:manage` es system-only

`config:manage` representa administración técnica del sistema.

Solo una cuenta persistida en `system_accounts` puede tener `config:manage` como permiso efectivo.

Una asignación directa, Rol, Grupo o Cargo que contenga `config:manage` para un usuario ordinario no debe convertirlo en Administrador del sistema ni habilitar endpoints técnicos.

## F-009-02 — `areas:manage` es configurable

Se incorpora el permiso atómico:

```text
areas:manage
```

Autoriza a administrar:

- Áreas;
- activación/desactivación de Áreas;
- Categorías del catálogo;
- relación Área ↔ Categoría;
- visualización de registros inactivos necesarios para configuración.

Puede heredarse mediante:

```text
Usuario → Permiso directo
Usuario → Rol → areas:manage
Usuario → Grupo → Rol → areas:manage
Usuario → Cargo → Rol → areas:manage
```

## F-009-03 — Sin autorización por nombres

Runtime no debe comprobar nombres como:

```text
Administración
Junta Directiva
Presidente
Tesorero
Administrador
```

Para otorgar acceso a un colectivo concreto, el Administrador del sistema configura una relación persistida, por ejemplo:

```text
Rol Gestor de áreas → areas:manage
Grupo configurado por la organización → Rol Gestor de áreas
```

La migración no asigna el Rol a ningún Grupo/Cargo por nombre.

## F-009-04 — Menú del Administrador del sistema

Cuando `user.is_system_account=true`, Configuración puede mostrar:

- **Usuarios**;
- **Organigrama**;
- **Accesos**;
- **Áreas**;
- otras opciones técnicas autorizadas como Reglas/Auditoría.

La identidad se obtiene del backend; no se infiere por `UserRole.ADMIN`, email, cargo o nombre.

## F-009-05 — Menú de un Gestor de Áreas

Cuando un usuario ordinario tiene `areas:manage` pero no es `system_accounts`:

- aparece **Configuración**;
- dentro aparece **Áreas**;
- no aparecen **Usuarios**, **Organigrama** ni **Accesos**;
- no puede abrir las APIs técnicas aunque manipule el frontend.

## F-009-06 — Usuario sin configuración

Un usuario ordinario sin `areas:manage` ni identidad de sistema no debe ver el menú **Configuración**.

Mantiene únicamente las capacidades que correspondan a sus permisos y reglas por recurso.

## F-009-07 — Backend authoritative

Las mutaciones de `/api/areas` usan `require_permission('areas:manage')`.

Las rutas IAM/Usuarios/Organigrama/Reglas/Auditoría técnica siguen bajo `config:manage`; el resolver IAM hace que dicho permiso sea efectivo únicamente para `system_accounts`.

Ocultar un botón no constituye autorización.

## F-009-08 — Identidad técnica explícita en sesión

`/api/auth/login` y `/api/auth/me` exponen:

```text
is_system_account: boolean
```

El frontend puede usarlo para UX. El backend vuelve a validar cada endpoint sensible mediante la identidad persistida y/o permiso efectivo correspondiente.

## F-009-09 — Migración 0006

Alembic `20260818_0006_area_management_permission.py`:

1. crea/activa `areas:manage`;
2. describe `config:manage` como administración técnica reservada;
3. crea el Rol reutilizable `Gestor de áreas` (`area-manager`) si no existe;
4. asocia `areas:manage` al Rol;
5. no asigna ese Rol a ningún Grupo/Cargo/Usuario por nombres organizacionales.

Cadena:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006
```

## Seguridad

- `config:manage` system-only;
- `areas:manage` default deny para usuarios ordinarios sin asignación;
- `system_accounts` es la única fuente de identidad técnica;
- asignaciones legacy de `config:manage` a usuarios ordinarios se ignoran en permisos efectivos;
- frontend no usa cargo, título, `UserRole.ADMIN` ni `can_configure` como autoridad;
- Accesos no se inyecta en menús de usuarios no técnicos.

## Fuera de alcance

- asignar automáticamente `Gestor de áreas` a grupos por nombre;
- retirar físicamente todos los `BOARD_CODES`/AccessProfile/UserRole legacy en esta feature;
- rediseñar completamente `main.jsx`/`domain-normalization.js`;
- introducir multi-tenancy;
- cambiar reglas de aprobación, corrección o cierre.