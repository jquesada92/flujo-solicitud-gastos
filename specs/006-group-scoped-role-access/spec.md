# Spec 006 — Acceso por Rol dentro de Grupo

**Estado:** Implementada  
**Constitución:** 2.11.0

## Objetivo

Eliminar configuraciones ambiguas y representar la responsabilidad del Usuario como un Rol concreto dentro de cada Grupo.

## Modelo

```text
Grupo 1 ─ Rol A ─ Permisos
        └ Rol B ─ Permisos

Usuario X ─ Rol A del Grupo 1
          └ Rol C del Grupo 2
```

## Invariantes

1. Un Rol pertenece a un único Grupo.
2. Un Usuario tiene máximo un Rol por Grupo.
3. La membresía del Grupo se deriva de ese Rol.
4. No hay membresía independiente.
5. No hay Rol operativo de Usuario sin Grupo.
6. No hay permiso individual.
7. Cargo/Posición es información organizacional y no concede acceso.
8. Un Usuario tiene máximo un Cargo.

## Enforcement

- validación backend en `iam_users.py`;
- `group_roles.role_id` único;
- PostgreSQL trigger para impedir dos Roles del mismo Grupo para un Usuario;
- política de compatibilidad bloquea endpoints legacy;
- `user_positions.user_id` único en la revisión 0003.

## UI

En la ficha del Usuario cada Grupo tiene un `<select>` de Rol y una opción “Sin rol / sin acceso”. Los cambios se guardan en una sola operación explícita.
