# Spec 016 — Herencia aditiva de Permisos por Grupo

**Estado:** Implementada  
**Constitución:** 2.16.0

## Objetivo

Permitir que un Grupo defina Permisos comunes que hereden todos sus Roles, sin perder los Permisos configurados directamente en cada Rol.

## Contrato

Para un Rol activo asignado a un Usuario y vinculado a un Grupo activo:

```text
permisos_del_rol_agrupado = RolePermission(rol) ∪ GroupPermission(grupo)
```

Para un Rol global activo:

```text
permisos_del_rol_global = RolePermission(rol)
```

La operación es una unión de grants positivos: elimina duplicados, conserva los Permisos propios adicionales y hereda todo Permiso del Grupo que no esté configurado en el Rol. La ausencia a nivel de Rol no es una negación; no existe `DENY`, override negativo ni precedencia capaz de retirar un Permiso del Grupo.

## Invariantes

1. Los Permisos de Grupo se persisten en `group_permissions` y los propios del Rol en `role_permissions`.
2. Editar los Permisos del Grupo no crea, reemplaza ni elimina `RolePermission`.
3. Desvincular un Rol del Grupo conserva `UserRoleAssignment` y `RolePermission`; el Rol pierde únicamente la herencia y se vuelve global.
4. Vincular un Rol a un Grupo suma la herencia sin reemplazar sus Permisos propios.
5. Solo una asignación `UserRoleAssignment` a un Rol agrupado activo permite heredar del Grupo activo.
6. `GroupMember` es una proyección de membresía y por sí solo no autoriza.
7. Roles, Grupos y Permisos inactivos no conceden.
8. `config:manage` sigue siendo system-only incluso si se configura en un Grupo o Rol ordinario.
9. Los Roles técnicos `system_managed` y la política `SystemAccount` conservan sus protecciones existentes.

## Accesos

La ficha del Grupo permite editar en una misma operación staged:

```text
Permisos heredables
Roles del Grupo
Miembros derivados (solo lectura)
```

La ficha del Rol sigue editando exclusivamente sus Permisos propios y muestra cuáles también hereda del Grupo. Un Permiso heredado continúa efectivo aunque su checkbox de propiedad directa esté desmarcado.

## Persistencia

Alembic `20260824_0009_group_permission_inheritance` agrega `group_permissions` con unicidad `(group_id, permission_id)` y claves foráneas con borrado en cascada. No hace backfill de grants: todos los Grupos empiezan sin Permisos heredables para no alterar accesos preexistentes. Sí normaliza `permission_codes` en las instantáneas temporales abiertas de Rol y Grupo para que reflejen la forma vigente del historial.

## Fuera de alcance

No se incorpora semántica `ALLOW/DENY`, excepciones negativas por Rol, permisos directos a Usuario ni autoridad derivada de una fila `GroupMember`.
