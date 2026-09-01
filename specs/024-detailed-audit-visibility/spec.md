# Spec 024 — Auditoría visible con diferencias por campo

**Estado:** Implementada
**Constitución:** 2.30.0

## Objetivo

Permitir que una persona con lectura de Configuración compruebe qué se creó,
actualizó o eliminó, quién lo hizo y, para cada actualización, cuál era el valor
anterior y cuál es el actual.

## Reglas

1. `GET /api/audit/events` sin fechas consulta por defecto las siete fechas
   calendario inclusivas desde hoy menos seis días hasta hoy, según
   `APP_TIME_ZONE`, y conserva búsqueda, filtros, límite y cursor. El límite
   predeterminado de la API es 10.
2. Cada elemento devuelve `change_type` normalizado como `CREATE`, `UPDATE` o
   `DELETE`, además del `event_type` específico.
3. `changes` usa `{campo: {before, after}}`; `changed_fields` enumera exactamente
   las claves visibles de `changes`.
4. Una creación usa `before=null`; una eliminación usa `after=null`.
5. Los cambios de Rol de un Usuario provienen de `audit_change_feed` y muestran
   `assigned_roles` anterior y actual bajo `USER_ROLES_UPDATED`.
6. `GET /api/audit/events` ejecuta una sola consulta sobre el feed, con orden y
   cursor por `occurred_at,event_sequence`; no consulta, fusiona ni ordena en
   Python múltiples tablas de historia.
7. Una desactivación es una actualización con acción específica
   “desactivado”; no se presenta falsamente como borrado físico.
8. La respuesta excluye contraseña, hash, token y secreto, y enmascara correo,
   teléfono e identificación personal de las instantáneas.
9. `config:read` puede consultar la pantalla; ninguna capacidad de lectura
   autoriza mutaciones.
10. La UI muestra etiquetas textuales de Creación/Actualización/Eliminación y
    no depende solo del color.
11. Cada diferencia incluye las etiquetas “Valor anterior” y “Valor actual”.
    `false`, `0`, `null`, listas y objetos se representan sin perder significado.
12. Desde 720 px hacia abajo, cada fila se convierte en una tarjeta completa;
    actor, elemento, acción y valores siguen visibles desde 320 px.
13. `date_from` y `date_to` se envían juntas como `YYYY-MM-DD`; ambos límites
    son inclusivos y `date_from > date_to` responde `422`.
14. El backend convierte el rango local a un intervalo UTC semiabierto y filtra
    `audit_change_feed` antes de ordenar y paginar, sin aplicar funciones a
    `occurred_at` ni conservar un recorte fijo de 45 días.
15. La UI precarga **Desde** y **Hasta** con los últimos 7 días usando
    `VITE_TIME_ZONE`, alineada con `APP_TIME_ZONE`; permite mover o ampliar el
    período para investigar historia anterior y ofrece restaurar el rango
    predeterminado.
16. La pantalla no ofrece la vista agregada **Todos**. Presenta únicamente
    **Flujos**, **Usuarios**, **Accesos**, **Áreas** y **Reglas**, con **Flujos**
    como sección inicial. La API puede conservar `kind=ALL` solo por
    compatibilidad; `Audit()` siempre envía una categoría concreta.
17. Cada sección muestra hasta 10 registros por página y envía `limit=10`.
    **Anterior** y **Siguiente** navegan con el cursor keyset y reemplazan la
    página visible, sin acumular filas, usar `OFFSET` ni ejecutar un conteo
    total; el backend puede leer una fila adicional únicamente para calcular
    `has_more`.
18. Cambiar sección, búsqueda o fechas descarta el historial de cursores y
    vuelve a la primera página. **Actualizar** conserva las fechas, categoría y
    búsqueda aplicadas, y vuelve también a la primera página.

## Contrato de respuesta

```json
{
  "event_id": "USER_PERIOD:42",
  "occurred_at": "2026-08-31T15:00:00Z",
  "kind": "USER",
  "entity_type": "USER",
  "event_type": "USER_ROLES_UPDATED",
  "change_type": "UPDATE",
  "subject": "Usuario de prueba",
  "actor": "Administrador",
  "changed_fields": ["assigned_roles"],
  "changes": {
    "assigned_roles": {
      "before": [{"id": 1, "code": "requester", "name": "Solicitante"}],
      "after": [{"id": 2, "code": "approver", "name": "Aprobador"}]
    }
  }
}
```

`details` permanece como campo de compatibilidad, pero la comparación visible
se construye exclusivamente desde `changes`.

## Persistencia

`audit_change_feed` es la única fuente de lectura de Auditoría. Cada mutación
auditable calcula una vez su instantánea y sus diferencias dentro de la misma
transacción del backend; el feed conserva actor, entidad, acción, campos,
`changes`, contexto y una clave única de origen. PostgreSQL impide modificar,
borrar o truncar sus filas.

`20260831_0015_audit_change_feed` crea el feed, hace backfill set-based de las
fuentes existentes y valida sus conteos. `20260831_0016_retire_legacy_audit_tables`
comprueba nuevamente la copia y elimina sin `CASCADE` estas ocho tablas:

```text
user_activity_periods
area_activity_periods
role_activity_periods
group_activity_periods
user_change_events
access_profile_change_events
approval_policy_change_events
invoice_change_events
```

`approval_step_events` y `quotation_vote_events` permanecen porque son evidencia
operativa consumida por sus dominios; sus altas se proyectan al feed, pero el
listado de Auditoría no las consulta directamente. El downgrade de `0016` es
irreversible: restaurar el diseño anterior requiere un respaldo previo al corte
y la imagen anterior, nunca tablas de historia vacías.
