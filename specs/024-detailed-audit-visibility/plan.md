# Plan 024 — Auditoría visible con diferencias por campo

1. Crear `audit_change_feed` append-only e indexado sobre el head Alembic vigente.
2. Hacer backfill set-based de las fuentes históricas en PostgreSQL y validar
   conteos e idempotencia por clave de origen.
3. Capturar entidades, relaciones y eventos de dominio en el feed dentro de la
   misma transacción de negocio.
4. Migrar `GET /api/audit/events` y `/api/users/changes` a una sola fuente y
   paginación keyset por `occurred_at,event_sequence`, con páginas de 10 en la
   pantalla y una fila adicional de lectura solo para determinar `has_more`.
5. Retirar sin `CASCADE` las ocho tablas redundantes solo después de verificar
   su copia; mantener los eventos operativos de aprobación y votación.
6. Enmascarar datos personales y excluir secretos antes de serializar.
7. Exponer `change_type` y `changes` manteniendo campos compatibles.
8. Renderizar acción y comparación anterior/actual en la pantalla Auditoría.
9. Incorporar **Desde/Hasta** con siete fechas calendario por defecto en
   `APP_TIME_ZONE`, sin límite histórico fijo; retirar la vista **Todos**, abrir
   en **Flujos** y conservar el rango al navegar las cinco secciones.
10. Convertir las filas y los filtros en controles completos para anchos
    estrechos.
11. Probar backfill, inmutabilidad, una consulta por página, cambio de Rol,
    eliminación, privacidad, límites de fecha, rango ampliado, páginas de hasta
    10 sin acumulación ni duplicados, reinicio de cursor, PostgreSQL local,
    build y navegador.
