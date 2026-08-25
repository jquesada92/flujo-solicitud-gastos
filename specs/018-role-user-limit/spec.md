# Spec 018 — Límite de Usuarios activos por Rol

**Estado:** Implementado
**Constitución:** 2.18.0
**Fecha:** 2026-08-25

## Objetivo

Permitir que un Rol ordinario defina opcionalmente la cantidad máxima de
Usuarios activos que pueden tenerlo asignado, sin borrar asignaciones de
Usuarios inactivos ni convertir la UI en autoridad de integridad.

## Contrato

- `roles.max_users = NULL` significa sin límite.
- Un límite configurado es un entero mayor o igual que 1.
- La ocupación es la cantidad de `UserRoleAssignment` cuyo Usuario está activo.
- Un Usuario inactivo conserva el Rol y no consume cupo.
- Asignar un Rol lleno a otro Usuario activo devuelve 409 y no persiste cambios.
- Reactivar un Usuario que conserva un Rol lleno devuelve 409 y mantiene al
  Usuario inactivo.
- Inactivar o desasignar libera cupo.
- El máximo no puede reducirse por debajo de la ocupación activa.
- La comprobación bloquea las filas de Roles objetivo en orden estable antes de
  contar, para serializar asignaciones concurrentes en PostgreSQL.
- El límite no altera permisos propios, herencia de Grupo ni cardinalidades IAM.

## UX

El editor de Rol ofrece **Limitar cantidad de usuarios activos** y, al activarlo,
un input numérico **Máximo de usuarios activos**. Muestra la ocupación actual,
valida contra ella y persiste únicamente con **Guardar cambios**. La lista de
Roles presenta ocupación/máximo y el selector de Usuario identifica como **sin
cupo** un Rol lleno que ese Usuario todavía no tiene.

## Persistencia y compatibilidad

Alembic `20260825_0011_role_user_limit` agrega la columna nullable y el check
`ck_roles_max_users_positive`. Los Roles existentes quedan sin límite. Las
instantáneas `role_activity_periods.values` incorporan `max_users`.

## Fuera de alcance

- límites por Grupo, Cargo o Permiso;
- reservar cupos para Usuarios inactivos;
- borrar automáticamente asignaciones al reducir el máximo;
- usar el frontend como única barrera de concurrencia.
