# Aceptación 013

- [x] MULTI_QUOTE requiere al menos dos opciones.
- [x] cada opción requiere soporte.
- [x] URLs duplicadas se rechazan.
- [x] participantes vienen de `requests:approve` efectivo y del scope/fallback de la Spec 021.
- [x] solicitante queda excluido de la población configurada o fallback.
- [x] usuario sin invitación recibe 403.
- [x] opción ajena recibe 422.
- [x] ronda cerrada recibe 409.
- [x] cada usuario mantiene un voto activo.
- [x] cambios de voto conservan evento.
- [x] con regla, quórum y líder único habilitan cierre anticipado sin cerrar la votación.
- [x] sin regla, la ronda espera a todos y un ganador único lleva a APPROVED.
- [x] empate conserva QUOTATION_VOTING y no habilita cierre.
- [x] invitados restantes pueden votar/cambiar hasta la factura y CLOSED.
- [x] corrección reinicia política, quórum, población, votos y flow_id activos.
- [x] Inicio muestra QUOTATION_VOTE solo mientras esté pendiente.
- [x] Docker local contiene votación abierta y voto parcial visibles.
