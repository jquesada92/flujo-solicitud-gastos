# Plan — historial temporal de actividad

1. Crear cuatro tablas con restricciones de integridad e índices por entidad.
2. Rellenar registros existentes desde `created_at` mediante Alembic `0005`.
3. Registrar altas y transiciones desde eventos ORM dentro de la transacción original.
4. Probar altas activas/inactivas, cierres, reaperturas, no-op y duplicidad abierta.
5. Validar migración y operaciones reales contra PostgreSQL local.
