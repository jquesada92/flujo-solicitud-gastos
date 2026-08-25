# Spec 006 — Acceso por Roles agrupados y globales

**Estado:** Implementada  
**Constitución:** 2.16.0

## Objetivo

Representar responsabilidades de Usuario mediante Roles reutilizables que pueden pertenecer a un Grupo o mantenerse globales, evitando configuraciones ambiguas y preservando la restricción de un Rol por Grupo.

## Modelo

```text
Grupo 1 ─ Permisos heredables
        ├ Rol A ─ Permisos propios
        └ Rol B ─ Permisos propios

Rol Global X ─ Permisos
Rol Global Y ─ Permisos

Usuario X ─ Rol A del Grupo 1
          ├ Rol C del Grupo 2
          └ Rol Global X
```

## Invariantes

1. Un Grupo puede existir sin Roles.
2. Un Rol pertenece a cero o un Grupo; nunca a dos.
3. Un Rol sin Grupo es global.
4. Un Usuario tiene máximo un Rol por Grupo.
5. Un Usuario puede tener varios Roles globales ordinarios.
6. La membresía del Grupo se deriva únicamente de Roles agrupados.
7. Un Rol global no crea membresía.
8. No hay membresía independiente.
9. No hay permiso individual.
10. Cargo/Posición es información organizacional y no concede acceso.
11. Un Usuario tiene máximo un Cargo.
12. El Rol técnico `Administrador del sistema` es global y protegido; `SystemAccount` sigue siendo la autoridad de privilegios técnicos.
13. Un Rol agrupado concede la unión de sus Permisos propios y los Permisos de su Grupo activo.
14. La ausencia de un Permiso propio no lo niega: se hereda si el Grupo lo aporta y no existe `DENY`.
15. `GroupMember` es una proyección derivada y nunca una fuente autónoma de autorización.

## Cambio de scope

Quitar un Rol de un Grupo lo convierte en global sin borrar las asignaciones existentes del Usuario ni sus `RolePermission`; desaparecen únicamente los Permisos heredados del Grupo. Agregar Roles globales a un Grupo debe rechazarse si produciría dos Roles del mismo Grupo para un Usuario ya asignado y, si es válido, suma la herencia del nuevo Grupo sin reemplazar los Permisos propios.

Después de cambiar el catálogo de Roles de un Grupo, `GroupMember` se reconstruye desde las asignaciones de Roles agrupados.

## Enforcement

- validación backend en `iam_users.py` para Roles agrupados y globales;
- `group_roles.role_id` único para impedir que un Rol pertenezca a dos Grupos;
- trigger PostgreSQL sobre `user_role_assignments` para impedir dos Roles del mismo Grupo al asignar/cambiar un Rol de Usuario;
- trigger PostgreSQL sobre `group_roles` para impedir que un cambio Global→Grupo cree retrospectivamente dos Roles del mismo Grupo para un Usuario;
- revisión `20260821_0004_allow_global_roles` permite Roles sin Grupo sin relajar ninguno de esos guards;
- revisión `20260824_0009_group_permission_inheritance` agrega `group_permissions` como grants positivos y deja intactas las filas `role_permissions`;
- `iam_group_assignments.py` valida cambios Global↔Grupo y reconstruye membresía;
- política de compatibilidad bloquea endpoints legacy;
- `user_positions.user_id` único desde revisión 0003.

## UI

La ficha del Usuario tiene:

```text
Acceso por grupo
Grupo A → [Rol A1 | Rol A2 | Sin rol adicional]

Roles globales
[x] Rol global 1
[ ] Rol global 2
```

Los cambios se guardan en una sola operación explícita. La ficha del Grupo permite editar Permisos heredables; la ficha del Rol distingue sus Permisos propios de los heredados y no ofrece una negación. La cuenta técnica muestra su Rol global protegido sin permitir edición ordinaria.
