# Aceptación 013

- [x] MULTI_QUOTE requiere al menos dos opciones.
- [x] cada opción requiere soporte.
- [x] URLs duplicadas se rechazan.
- [x] participantes vienen de `requests:approve` efectivo.
- [x] solicitante queda excluido de la población.
- [x] usuario sin invitación recibe 403.
- [x] opción ajena recibe 422.
- [x] ronda cerrada recibe 409.
- [x] cada usuario mantiene un voto activo.
- [x] cambios de voto conservan evento.
- [x] la ronda espera a todos los invitados.
- [x] ganador único lleva a APPROVED.
- [x] empate conserva QUOTATION_VOTING.
- [x] corrección reinicia población, votos y flow_id activos.
- [x] Inicio muestra QUOTATION_VOTE solo mientras esté pendiente.
- [x] Docker local contiene votación abierta y voto parcial visibles.
