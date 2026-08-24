# Aceptación 012

- [x] ORM usa schema explícito.
- [x] `alembic_version` usa `administracion`.
- [x] endpoint pooled no recibe startup `search_path`.
- [x] Render declara `DATABASE_SCHEMA`.
- [x] cadena Alembic es lineal `0001 → … → 0009` y tiene un único head.
- [x] 0002 aplica reglas Grupo/Rol.
- [x] 0003 aplica un Cargo por Usuario.
- [x] 0004 permite Roles globales sin relajar el límite de un Rol por Grupo.
- [x] 0009 agrega `group_permissions` sin reescribir revisiones previas.
- [x] tests de schema verifican el contrato.
- [x] SQL crudo del contador usa tabla calificada por metadata.
- [x] Enum ORM hereda el schema de aplicación.
- [x] escenario Docker inserta contador, solicitud y aprobaciones en PostgreSQL.
