# Spec 010 — Notificaciones de acceso

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Informar al usuario sobre su contexto organizacional y capacidades cuando se crea su cuenta o cambia su Cargo.

## Invitación

Para usuario activo incluye:

```text
correo
contraseña temporal
Cargo, si existe
permisos efectivos
URL pública
```

## Cambio de Cargo

Un Usuario tiene 0..1 Cargo. Si cambia realmente `position_ids`:

1. se actualiza `UserPosition`;
2. se calculan permisos efectivos vigentes;
3. se envía “Actualización de cargo y permisos”.

Cargo y permisos son datos independientes: el Cargo no concede acceso.

Guardar el mismo Cargo no debe generar correo duplicado.

## Fuente de datos

```text
Cargo    = UserPosition → Position
Permisos = effective_permission_codes()
```

Los permisos efectivos pueden provenir de Permisos propios de Roles globales o, para Roles agrupados cuyo Grupo esté activo, de la unión aditiva de Permisos propios y heredados del Grupo. `GroupMember` aislado no autoriza y la política técnica de `SystemAccount` continúa separada y protegida.
