# Aceptación 021

- [x] Las bandas activas usan `(min,max]`, permiten adyacencia y rechazan overlap dentro del mismo scope.
- [x] El Área concreta precede a `ALL` y un hueco usa fallback sin regla.
- [x] `SIMPLE` evalúa su monto y `MULTI_QUOTE` el máximo de todas sus opciones.
- [x] Solo Roles/Grupos activos compatibles con `requests:approve` pueden guardarse como targets.
- [x] Seleccionar un Grupo expande sus Roles/Usuarios elegibles y deduplica participantes.
- [x] Cargo, `GroupMember`, nombres y `approver_profile_codes` no conceden autoridad.
- [x] El Solicitante queda excluido y una regla sin participantes no deja datos huérfanos.
- [x] `ANY`, `MAJORITY` y `ALL` calculan 1, `floor(N/2)+1` y `N` respectivamente.
- [x] Regla, modalidad, monto evaluado y umbral quedan congelados por ronda.
- [x] Con regla y líder único, el quórum habilita cierre anticipado solo al Solicitante.
- [x] Después del quórum, invitados restantes pueden votar/cambiar hasta la factura y el cierre.
- [x] Empate no habilita cierre y un voto posterior recalcula el líder vigente.
- [x] Cierre y factura son atómicos; después de `CLOSED`, votar responde 409.
- [x] Sin regla, `MULTI_QUOTE` espera a todos, exige líder único y permanece en `QUOTATION_VOTING` hasta la factura.
- [x] Sin regla, Solicitante, `system_accounts` o delegado activo pueden cerrar directamente a `CLOSED` solo con población completa y líder único.
- [x] Sin regla, votos pendientes o empate responden 409 sin factura ni ganador seleccionado.
- [x] Políticas legacy sin targets quedan inactivas/no aplicables y no habilitan cierre anticipado.
- [x] Suite backend, migración PostgreSQL local, build frontend, navegador y contrato documental pasan.
