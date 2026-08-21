# Aceptación

- [x] Usuario, Área, Rol y Grupo crean una fila inicial.
- [x] `active_from` coincide con `created_at`.
- [x] Desactivar cierra la versión anterior y abre una versión inactiva.
- [x] Reactivar crea una fila nueva y conserva las anteriores.
- [x] Un cambio relevante distinto de `active` crea una versión JSON.
- [x] Usuario conserva cédula, contacto, nombre, correo y Roles.
- [x] Rol conserva su Grupo y versiona cambios de asociación.
- [x] Cada versión identifica quién, cuándo y qué cambió.
- [x] Los cambios contienen valores anterior y nuevo por campo.
- [x] Procesos automáticos quedan identificados como `SYSTEM:*`.
- [x] No se auditan contraseñas, hashes, tokens ni secretos.
- [x] La base rechaza dos períodos abiertos para la misma entidad.
- [x] La migración rellena registros existentes.
- [x] Migración y transiciones verificadas en PostgreSQL local.
