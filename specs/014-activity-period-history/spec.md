# Spec 014 — Historial de actividad

**Estado:** Sustituida por Spec 024
**Constitución:** 2.30.0

## Objetivo conservado

Conservar cuándo y cómo cambió cada Usuario, Área, Rol y Grupo, incluidos sus
estados activo/inactivo, sin sobrescribir historia. La persistencia temporal por
entidad que implementó originalmente esta Spec fue reemplazada por el change
feed canónico definido en Spec 024.

## Regla vigente

1. `audit_change_feed` guarda una fila inmutable por creación, actualización o
   eliminación auditable.
2. Cada fila conserva `occurred_at`, actor, entidad, tipo de evento, campos,
   diferencias `{before, after}` y una instantánea del estado relevante.
3. Cambiar activa↔inactiva produce una actualización específica y conserva el
   mismo ID de negocio.
4. Las asignaciones Rol→Grupo, Usuario→Rol y los cambios de Permisos actualizan
   la instantánea agregada de la entidad afectada en la misma transacción.
5. Los intervalos históricos se reconstruyen ordenando las instantáneas por
   entidad y usando el siguiente `occurred_at` como fin del estado anterior.
6. Contraseñas, hashes, tokens y secretos quedan fuera del feed.
7. La clave única `(source_type, source_id)` evita duplicar una fuente y el
   backend no persiste actualizaciones sin diferencias.

## Sustitución física

`20260831_0015_audit_change_feed` copió set-based la historia desplegada y
validó conteos. `20260831_0016_retire_legacy_audit_tables` comprobó nuevamente
la copia y retiró sin `CASCADE`:

```text
user_activity_periods
area_activity_periods
role_activity_periods
group_activity_periods
```

Las revisiones `20260821_0005` a `20260821_0008` permanecen inmutables en la
cadena Alembic porque pueden haber sido desplegadas; una instalación nueva las
aplica y posteriormente `0015/0016` consolida y retira sus tablas. El downgrade
de `0016` es irreversible y requiere restaurar el respaldo previo al corte junto
con la imagen anterior.
