# Spec 014 — Historial temporal de actividad

**Estado:** Implementado  
**Constitución:** 2.14.0

## Objetivo

Conservar los intervalos en que cada Usuario, Área, Rol y Grupo estuvo activo,
sin perder historia al alternar el indicador `active`.

## Reglas

1. Cada entidad tiene períodos con llave primaria propia y llave foránea estable.
2. Al crearla se inserta una fila con `active_from = created_at` y una instantánea JSON.
3. La versión vigente mantiene `active_until = NULL`, incluso si su JSON indica `active=false`.
4. Cualquier modificación relevante cierra la versión abierta y crea una nueva en la misma transacción.
5. Cambiar activa↔inactiva sigue la misma regla y nunca sobrescribe versiones anteriores.
6. Una asignación o retiro Rol→Grupo y Usuario→Rol también crea versión del propietario relacionado.
7. `active_until` nunca puede ser anterior a `active_from`.
8. La base de datos impide más de un período abierto para la misma entidad.
9. Los intervalos cuyo JSON contiene `active=false` identifican inactividad.
10. La migración rellena una fila inicial para todos los registros existentes.
11. Cada versión registra `event_at`, actor, tipo de cambio, campos modificados
    y diferencias anterior/nuevo.
12. El actor autenticado conserva ID interno, correo y cédula. Bootstrap,
    migraciones y automatizaciones usan un actor explícito `SYSTEM:*`.
13. Contraseñas, hashes, tokens y secretos quedan fuera de las instantáneas.

## Persistencia

```text
user_activity_periods  → users
area_activity_periods  → expense_categories
role_activity_periods  → roles
group_activity_periods → user_groups
```

Cada tabla contiene `id`, la llave foránea, `active_from`, `active_until` y
`values` JSON. Para Usuario, `identity_document` (cédula) es la llave de negocio
conservada junto con teléfono, nombres, apellidos, correo y Roles. Para Rol se
conserva el Grupo asociado.

Metadatos de auditoría:

```text
event_at
actor_user_id
actor_identifier
actor_identity_document
change_type
changed_fields
changes              # {campo: {before, after}}
```
Las eliminaciones en cascada siguen la vida de la entidad principal; la
aplicación no ofrece eliminación ordinaria de estos catálogos.
